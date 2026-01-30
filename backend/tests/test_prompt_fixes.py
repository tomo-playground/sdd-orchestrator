
from unittest.mock import MagicMock

from models.tag import Tag

# Import functions to test
from services.prompt.prompt import normalize_tag_spaces
from services.prompt.prompt_composition import filter_conflicting_tokens
from services.tag_classifier import TagClassifier


class TestPromptFixes:
    """Test recent fixes for prompt generation bugs."""

    # Fix 1: Malformed tags like _day, _bright
    def test_normalize_leading_underscores(self):
        """Should strip leading/trailing underscores from tags."""
        inputs = [
            "_day",
            " _bright ",
            "__sun",
            "moon__",
            "flower_field" # Should preserve middle underscore
        ]

        # We expect normalize_tag_spaces to handle lists and return lists
        # It strips spaces THEN replaces spaces with _, THEN strips _

        # Test individual behavior
        assert normalize_tag_spaces(["_day"]) == ["day"]
        assert normalize_tag_spaces([" _bright "]) == ["bright"]
        assert normalize_tag_spaces(["__sun"]) == ["sun"]
        assert normalize_tag_spaces(["moon__"]) == ["moon"]
        assert normalize_tag_spaces(["flower_field"]) == ["flower_field"]

        # Batch test
        result = normalize_tag_spaces(inputs)
        assert result == ["day", "bright", "sun", "moon", "flower_field"]

    # Fix 2: Duplicate tags with weights (e.g. (happy:1.2) vs happy)
    def test_filter_weighted_duplicates(self):
        """filter_conflicting_tokens should deduplicate (tag:1.2) and tag."""

        # Case 1: Weighted comes first (should be kept)
        tokens = ["(happy:1.2)", "happy", "smile"]
        filtered = filter_conflicting_tokens(tokens)
        assert "(happy:1.2)" in filtered
        assert "happy" not in filtered
        assert "smile" in filtered
        assert len(filtered) == 2

        # Case 2: Plain comes first (should be kept)
        # Note: In our implementation, the FIRST occurrence wins
        tokens_2 = ["happy", "(happy:1.2)", "smile"]
        filtered_2 = filter_conflicting_tokens(tokens_2)
        assert "happy" in filtered_2
        assert "(happy:1.2)" not in filtered_2
        assert len(filtered_2) == 2

    # Fix 3: TagClassifier looking up underscores correctly
    def test_tag_classifier_lookup_underscore(self):
        """TagClassifier should find tags in DB even if input has spaces/underscores."""

        # Mock DB
        mock_db = MagicMock()

        # Mock DB query result
        mock_tag = MagicMock(spec=Tag)
        mock_tag.group_name = "quality"
        mock_tag.classification_confidence = 1.0

        # Setup execute().scalar_one_or_none() chain
        mock_execute = mock_db.execute
        mock_execute.return_value.scalar_one_or_none.return_value = mock_tag

        classifier = TagClassifier(db=mock_db)

        # Test input with spaces (should be converted to underscore for DB lookup)
        # because DB stores 'best_quality'
        classifier._lookup_db("best quality")

        # Verify call args - it should have queried for "best_quality"
        # Since _lookup_db constructs a select(Tag).where(Tag.name == tag)
        # We need to inspect how 'tag' argument was passed to the query.
        # This is hard to inspect on the SQLAlchemy object directly without complex mocking.
        # Instead, we rely on the classifier logic we fixed:
        # classify() calls replace(" ", "_") BEFORE calling lookup_db

        # Use white-box testing of the private method normalize logic via public method
        # We can mock _lookup_db to verify it receives underscore version

        classifier._lookup_db = MagicMock(return_value={"group": "quality", "confidence": 1.0, "source": "db"})

        # Case 1: Input "best quality" -> _lookup_db("best_quality")
        classifier.classify("best quality")
        classifier._lookup_db.assert_called_with("best_quality")

        # Case 2: Input "best_quality" -> _lookup_db("best_quality")
        classifier.classify("best_quality")
        classifier._lookup_db.assert_called_with("best_quality")
