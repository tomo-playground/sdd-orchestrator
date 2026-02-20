"""Phase 11-P3: 연속 gaze 반복 검출 + validate_visuals 통합 테스트."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.creative_qc import _check_consecutive_gaze, _extract_tags_from_prompt, validate_visuals
from services.keywords.patterns import CATEGORY_PATTERNS

_GAZE_TAGS: frozenset[str] = frozenset(CATEGORY_PATTERNS.get("gaze", []))


# ── _extract_tags_from_prompt ─────────────────────────────────


class TestExtractTagsFromPrompt:
    def test_extracts_matching_tags(self):
        prompt = "looking_at_viewer, brown_hair, smile"
        result = _extract_tags_from_prompt(prompt, _GAZE_TAGS)
        assert result == ["looking_at_viewer"]

    def test_multiple_gaze_tags(self):
        prompt = "looking_at_viewer, looking_away, brown_hair"
        result = _extract_tags_from_prompt(prompt, _GAZE_TAGS)
        assert result == ["looking_at_viewer", "looking_away"]

    def test_no_matching_tags(self):
        prompt = "brown_hair, smile, school_uniform"
        result = _extract_tags_from_prompt(prompt, _GAZE_TAGS)
        assert result == []

    def test_empty_prompt(self):
        result = _extract_tags_from_prompt("", _GAZE_TAGS)
        assert result == []


# ── _check_consecutive_gaze ──────────────────────────────────


class TestCheckConsecutiveGaze:
    def test_no_consecutive_repetition(self):
        """인접 씬에 다른 gaze → 빈 리스트."""
        gaze = [["looking_at_viewer"], ["looking_away"], ["looking_up"]]
        assert _check_consecutive_gaze(gaze) == []

    def test_adjacent_same_gaze_warns(self):
        """인접 씬 동일 gaze → WARN."""
        gaze = [["looking_at_viewer"], ["looking_at_viewer"], ["looking_away"]]
        issues = _check_consecutive_gaze(gaze)
        assert len(issues) == 1
        assert "Scene 0→1" in issues[0]
        assert "looking_at_viewer" in issues[0]

    def test_three_consecutive_same_gaze(self):
        """3연속 동일 gaze → 2개 WARN."""
        gaze = [["looking_away"], ["looking_away"], ["looking_away"]]
        issues = _check_consecutive_gaze(gaze)
        assert len(issues) == 2
        assert "Scene 0→1" in issues[0]
        assert "Scene 1→2" in issues[1]

    def test_no_gaze_tags_skip(self):
        """gaze 태그 없는 씬 → skip (교집합 없음)."""
        gaze = [[], ["looking_at_viewer"], []]
        assert _check_consecutive_gaze(gaze) == []

    def test_non_adjacent_repetition_pass(self):
        """비인접 반복 (0, 2) → PASS."""
        gaze = [["looking_at_viewer"], ["looking_away"], ["looking_at_viewer"]]
        assert _check_consecutive_gaze(gaze) == []

    def test_single_scene(self):
        """단일 씬 → 빈 리스트."""
        gaze = [["looking_at_viewer"]]
        assert _check_consecutive_gaze(gaze) == []

    def test_empty_list(self):
        """빈 리스트 → 빈 리스트."""
        assert _check_consecutive_gaze([]) == []


# ── validate_visuals 연속 gaze 통합 ──────────────────────────


class TestValidateVisualsConsecutiveGaze:
    def test_consecutive_gaze_warn_in_validate_visuals(self):
        """validate_visuals에서 연속 gaze 반복 WARN 검출."""
        scenes = [
            {"image_prompt": "looking_at_viewer, brown_hair", "camera": "close-up", "environment": "indoor"},
            {"image_prompt": "looking_at_viewer, smile", "camera": "medium_shot", "environment": "outdoor"},
            {"image_prompt": "looking_away, sad", "camera": "wide_shot", "environment": "park"},
        ]
        result = validate_visuals(scenes)
        assert result["checks"].get("gaze_consecutive") == "WARN"
        assert any("Scene 0→1" in i for i in result["issues"])

    def test_no_consecutive_pass_in_validate_visuals(self):
        """연속 반복 없으면 gaze_consecutive PASS."""
        scenes = [
            {"image_prompt": "looking_at_viewer, brown_hair", "camera": "close-up", "environment": "indoor"},
            {"image_prompt": "looking_away, smile", "camera": "medium_shot", "environment": "outdoor"},
            {"image_prompt": "looking_up, sad", "camera": "wide_shot", "environment": "park"},
        ]
        result = validate_visuals(scenes)
        assert result["checks"].get("gaze_consecutive") == "PASS"
