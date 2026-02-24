"""Tests for critical failure detection (gender swap, no subject, count mismatch)."""

from __future__ import annotations

from services.critical_failure import (
    CriticalFailureResult,
    detect_critical_failure,
    extract_detected_subjects,
    extract_expected_subjects,
)

# ═══════════════════════════════════════════════════
# extract_expected_subjects
# ═══════════════════════════════════════════════════


class TestExtractExpectedSubjects:
    def test_single_female(self):
        result = extract_expected_subjects("1girl, school_uniform, classroom")
        assert result["gender"] == "female"
        assert result["count"] == 1
        assert "1girl" in result["subject_tags"]

    def test_single_male(self):
        result = extract_expected_subjects("1boy, black_hair, standing")
        assert result["gender"] == "male"
        assert result["count"] == 1
        assert "1boy" in result["subject_tags"]

    def test_multiple_female(self):
        result = extract_expected_subjects("2girls, holding_hands")
        assert result["gender"] == "female"
        assert result["count"] == 2

    def test_mixed_gender(self):
        result = extract_expected_subjects("1girl, 1boy, couple, park")
        assert result["gender"] == "mixed"
        assert result["count"] == 2  # couple → 2

    def test_no_subject_prompt(self):
        result = extract_expected_subjects("landscape, sunset, mountains")
        assert result["gender"] is None
        assert result["count"] is None
        assert len(result["subject_tags"]) == 0

    def test_weighted_tags(self):
        result = extract_expected_subjects("(1girl:1.3), blue_eyes, (smile:0.9)")
        assert result["gender"] == "female"
        assert result["count"] == 1
        assert "1girl" in result["subject_tags"]

    def test_empty_prompt(self):
        result = extract_expected_subjects("")
        assert result["gender"] is None
        assert result["count"] is None


# ═══════════════════════════════════════════════════
# extract_detected_subjects
# ═══════════════════════════════════════════════════


class TestExtractDetectedSubjects:
    def test_high_confidence_detection(self):
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "solo", "score": 0.92, "category": "0"},
            {"tag": "blue_eyes", "score": 0.80, "category": "0"},
        ]
        result = extract_detected_subjects(tags, threshold=0.7)
        assert result["gender"] == "female"
        assert result["count"] == 1
        assert "1girl" in result["subject_tags"]
        assert result["confidence"] == 0.95

    def test_low_confidence_ignored(self):
        tags = [
            {"tag": "1girl", "score": 0.50, "category": "0"},
            {"tag": "blue_eyes", "score": 0.80, "category": "0"},
        ]
        result = extract_detected_subjects(tags, threshold=0.7)
        assert result["gender"] is None
        assert len(result["subject_tags"]) == 0

    def test_no_tags(self):
        result = extract_detected_subjects([], threshold=0.7)
        assert result["gender"] is None
        assert result["count"] is None


# ═══════════════════════════════════════════════════
# detect_critical_failure
# ═══════════════════════════════════════════════════


class TestDetectCriticalFailure:
    def test_gender_swap(self):
        tags = [{"tag": "1boy", "score": 0.95, "category": "0"}]
        result = detect_critical_failure("1girl, school_uniform", tags)
        assert result.has_failure is True
        assert len(result.failures) == 1
        assert result.failures[0].failure_type == "gender_swap"
        assert result.failures[0].expected == "female"
        assert result.failures[0].detected == "male"

    def test_no_subject_detected(self):
        tags = [
            {"tag": "landscape", "score": 0.90, "category": "0"},
            {"tag": "sunset", "score": 0.85, "category": "0"},
        ]
        result = detect_critical_failure("1girl, standing", tags)
        assert result.has_failure is True
        assert result.failures[0].failure_type == "no_subject"
        assert result.failures[0].detected == "none"

    def test_count_mismatch(self):
        tags = [{"tag": "2girls", "score": 0.90, "category": "0"}]
        result = detect_critical_failure("1girl, standing", tags)
        assert result.has_failure is True
        types = {f.failure_type for f in result.failures}
        assert "count_mismatch" in types

    def test_correct_generation(self):
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "solo", "score": 0.92, "category": "0"},
        ]
        result = detect_critical_failure("1girl, blue_eyes, smile", tags)
        assert result.has_failure is False
        assert len(result.failures) == 0

    def test_narrator_scene_no_failure(self):
        tags = [
            {"tag": "scenery", "score": 0.90, "category": "0"},
            {"tag": "sunset", "score": 0.85, "category": "0"},
        ]
        result = detect_critical_failure("landscape, sunset, mountains", tags)
        assert result.has_failure is False

    def test_mixed_gender_no_false_positive(self):
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "1boy", "score": 0.90, "category": "0"},
        ]
        result = detect_critical_failure("1girl, 1boy, couple, park", tags)
        assert result.has_failure is False

    def test_combined_failures(self):
        """prompt=1girl but detected=2boys → gender_swap + count_mismatch."""
        tags = [{"tag": "2boys", "score": 0.90, "category": "0"}]
        result = detect_critical_failure("1girl, standing", tags)
        assert result.has_failure is True
        types = {f.failure_type for f in result.failures}
        assert "gender_swap" in types
        assert "count_mismatch" in types

    def test_to_dict(self):
        tags = [{"tag": "1boy", "score": 0.95, "category": "0"}]
        result = detect_critical_failure("1girl, school_uniform", tags)
        d = result.to_dict()
        assert d["has_failure"] is True
        assert len(d["failures"]) == 1
        assert d["failures"][0]["failure_type"] == "gender_swap"
        assert isinstance(d["failures"][0]["confidence"], float)

    def test_no_failure_to_dict(self):
        result = CriticalFailureResult()
        d = result.to_dict()
        assert d["has_failure"] is False
        assert d["failures"] == []

    def test_solo_prompt_correct(self):
        """solo in prompt, solo detected → no failure."""
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "solo", "score": 0.92, "category": "0"},
        ]
        result = detect_critical_failure("solo, 1girl, standing", tags)
        assert result.has_failure is False

    def test_empty_prompt_no_failure(self):
        tags = [{"tag": "1girl", "score": 0.95, "category": "0"}]
        result = detect_critical_failure("", tags)
        assert result.has_failure is False
