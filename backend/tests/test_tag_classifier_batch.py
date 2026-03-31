"""Tests for TagClassifier batch methods — N+1 regression prevention."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from services.tag_classifier import ClassificationResult, TagClassifier


def _make_tag_row(
    name: str,
    group_name: str | None = "expression",
    classification_source: str | None = "rule",
    classification_confidence: float | None = 0.95,
) -> MagicMock:
    """Create a mock Tag row."""
    row = MagicMock()
    row.name = name
    row.group_name = group_name
    row.classification_source = classification_source
    row.classification_confidence = classification_confidence
    return row


class TestLookupDbBatch:
    """Tests for _lookup_db_batch()."""

    def test_single_query(self):
        """N tags → db.execute exactly 1 time."""
        db = MagicMock()
        tags = ["smile", "angry", "blush"]
        rows = [_make_tag_row(t) for t in tags]
        db.execute.return_value.scalars.return_value.all.return_value = rows

        classifier = TagClassifier(db)
        result = classifier._lookup_db_batch(tags)

        assert db.execute.call_count == 1
        assert len(result) == 3

    def test_empty_list(self):
        """Empty input → no DB call, empty dict."""
        db = MagicMock()
        classifier = TagClassifier(db)
        result = classifier._lookup_db_batch([])

        assert result == {}
        assert db.execute.call_count == 0

    def test_legacy_subject_low_confidence(self):
        """group_name='subject' + source=None → confidence 0.3."""
        db = MagicMock()
        row = _make_tag_row("some_tag", group_name="subject", classification_source=None)
        db.execute.return_value.scalars.return_value.all.return_value = [row]

        classifier = TagClassifier(db)
        result = classifier._lookup_db_batch(["some_tag"])

        assert result["some_tag"]["confidence"] == 0.3
        assert result["some_tag"]["source"] == "db"

    def test_legacy_subject_default_source(self):
        """group_name='subject' + source='default' → confidence 0.3."""
        db = MagicMock()
        row = _make_tag_row("some_tag", group_name="subject", classification_source="default")
        db.execute.return_value.scalars.return_value.all.return_value = [row]

        classifier = TagClassifier(db)
        result = classifier._lookup_db_batch(["some_tag"])

        assert result["some_tag"]["confidence"] == 0.3

    def test_classified_high_confidence(self):
        """Explicitly classified tag → confidence >= 0.9."""
        db = MagicMock()
        row = _make_tag_row("smile", classification_confidence=0.95)
        db.execute.return_value.scalars.return_value.all.return_value = [row]

        classifier = TagClassifier(db)
        result = classifier._lookup_db_batch(["smile"])

        assert result["smile"]["confidence"] >= 0.9
        assert result["smile"]["group"] == "expression"

    def test_no_group_name_excluded(self):
        """Tags with group_name=None are excluded from results."""
        db = MagicMock()
        row = _make_tag_row("mystery_tag", group_name=None)
        db.execute.return_value.scalars.return_value.all.return_value = [row]

        classifier = TagClassifier(db)
        result = classifier._lookup_db_batch(["mystery_tag"])

        assert "mystery_tag" not in result

    def test_confidence_floor_at_0_9(self):
        """DB confidence below 0.9 is floored to 0.9 for classified tags."""
        db = MagicMock()
        row = _make_tag_row("tag_a", classification_confidence=0.5)
        db.execute.return_value.scalars.return_value.all.return_value = [row]

        classifier = TagClassifier(db)
        result = classifier._lookup_db_batch(["tag_a"])

        assert result["tag_a"]["confidence"] == 0.9

    def test_none_confidence_defaults_to_1_0(self):
        """None confidence → treated as 1.0, then max(1.0, 0.9) = 1.0."""
        db = MagicMock()
        row = _make_tag_row("tag_b", classification_confidence=None)
        db.execute.return_value.scalars.return_value.all.return_value = [row]

        classifier = TagClassifier(db)
        result = classifier._lookup_db_batch(["tag_b"])

        assert result["tag_b"]["confidence"] == 1.0


class TestSaveClassificationBatch:
    """Tests for _save_classification_batch()."""

    @patch("services.tag_classifier.normalize_prompt_token", side_effect=lambda x: x)
    @patch("services.tag_classifier.TagClassifier._group_to_category", return_value="scene")
    def test_single_query(self, mock_cat, mock_norm):
        """N items → db.execute exactly 1 time."""
        db = MagicMock()
        classifier = TagClassifier(db)
        items: list[tuple[str, ClassificationResult]] = [
            ("smile", {"group": "expression", "confidence": 0.95, "source": "rule"}),
            ("angry", {"group": "expression", "confidence": 0.95, "source": "rule"}),
            ("sunset", {"group": "background", "confidence": 0.95, "source": "rule"}),
        ]

        classifier._save_classification_batch(items)

        assert db.execute.call_count == 1
        assert db.commit.call_count == 1

    @patch("services.tag_classifier.normalize_prompt_token", side_effect=lambda x: x)
    def test_empty_list(self, mock_norm):
        """Empty input → no DB call."""
        db = MagicMock()
        classifier = TagClassifier(db)
        classifier._save_classification_batch([])

        assert db.execute.call_count == 0
        assert db.commit.call_count == 0

    @patch("services.tag_classifier.normalize_prompt_token", side_effect=lambda x: x)
    @patch("services.tag_classifier.TagClassifier._group_to_category", return_value="scene")
    def test_rollback_on_error(self, mock_cat, mock_norm):
        """DB error → rollback called."""
        db = MagicMock()
        db.execute.side_effect = Exception("DB error")
        classifier = TagClassifier(db)
        items: list[tuple[str, ClassificationResult]] = [
            ("tag_x", {"group": "expression", "confidence": 0.95, "source": "rule"}),
        ]

        classifier._save_classification_batch(items)

        assert db.rollback.call_count == 1
        assert db.commit.call_count == 0

    @patch("services.tag_classifier.normalize_prompt_token", side_effect=lambda x: x)
    @patch("services.tag_classifier.TagClassifier._group_to_category", return_value="scene")
    def test_defer_commit(self, mock_cat, mock_norm):
        """defer_commit=True → no commit call."""
        db = MagicMock()
        classifier = TagClassifier(db)
        items: list[tuple[str, ClassificationResult]] = [
            ("tag_y", {"group": "hair_color", "confidence": 0.95, "source": "rule"}),
        ]

        classifier._save_classification_batch(items, defer_commit=True)

        assert db.execute.call_count == 1
        assert db.commit.call_count == 0

    @patch("services.tag_classifier.normalize_prompt_token", side_effect=lambda x: "")
    def test_empty_normalized_tags_skipped(self, mock_norm):
        """Tags that normalize to empty string are skipped entirely."""
        db = MagicMock()
        classifier = TagClassifier(db)
        items: list[tuple[str, ClassificationResult]] = [
            ("", {"group": "expression", "confidence": 0.95, "source": "rule"}),
        ]

        classifier._save_classification_batch(items)

        assert db.execute.call_count == 0


class TestClassifyBatchUsesBatchMethods:
    """Verify classify_batch() delegates to batch methods."""

    @patch.object(TagClassifier, "_save_classification_batch")
    @patch.object(TagClassifier, "_lookup_db_batch", return_value={})
    @patch.object(TagClassifier, "_apply_rules")
    def test_uses_batch_lookup(self, mock_rules, mock_lookup_batch, mock_save_batch):
        """classify_batch uses _lookup_db_batch instead of per-tag _lookup_db."""
        db = MagicMock()
        mock_rules.return_value = None  # no rule match → goes to DB lookup
        classifier = TagClassifier(db)

        classifier.classify_batch(["tag_a", "tag_b", "tag_c"])

        mock_lookup_batch.assert_called_once()
        assert len(mock_lookup_batch.call_args[0][0]) == 3

    @patch.object(TagClassifier, "_save_classification_batch")
    @patch.object(TagClassifier, "_lookup_db_batch", return_value={})
    @patch.object(TagClassifier, "_apply_rules")
    def test_uses_batch_save(self, mock_rules, mock_lookup_batch, mock_save_batch):
        """classify_batch uses _save_classification_batch for rule-matched tags."""
        db = MagicMock()
        mock_rules.return_value = {"group": "expression", "confidence": 0.95, "source": "rule"}
        classifier = TagClassifier(db)

        classifier.classify_batch(["tag_a", "tag_b"])

        mock_save_batch.assert_called_once()
        assert len(mock_save_batch.call_args[0][0]) == 2

    @patch.object(TagClassifier, "_save_classification_batch")
    @patch.object(TagClassifier, "_lookup_db_batch", return_value={})
    @patch.object(TagClassifier, "_apply_rules", return_value=None)
    def test_no_save_when_no_rule_match(self, mock_rules, mock_lookup_batch, mock_save_batch):
        """No rule match → _save_classification_batch not called."""
        db = MagicMock()
        classifier = TagClassifier(db)

        classifier.classify_batch(["unknown_tag"])

        mock_save_batch.assert_not_called()


class TestSaveClassificationBatchDedup:
    """Duplicate normalized name deduplication — cardinality violation prevention."""

    @patch("services.tag_classifier.TagClassifier._group_to_category", return_value="scene")
    def test_duplicate_normalized_names_deduplicated(self, mock_cat):
        """Different inputs normalizing to same name → single row (no cardinality violation)."""
        db = MagicMock()
        classifier = TagClassifier(db)
        items: list[tuple[str, ClassificationResult]] = [
            ("smile", {"group": "expression", "confidence": 0.95, "source": "rule"}),
            ("smile", {"group": "expression", "confidence": 0.95, "source": "rule"}),
        ]

        classifier._save_classification_batch(items)

        assert db.execute.call_count == 1
        call_args = db.execute.call_args
        # INSERT statement should have only 1 row, not 2
        stmt = call_args[0][0]
        compiled = stmt.compile(compile_kwargs={"literal_binds": False})
        # Verify commit was called (no cardinality error)
        assert db.commit.call_count == 1
