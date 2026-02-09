"""Unit tests for validate_music, validate_scripts, validate_visuals, and resolve_characters_from_context."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.creative_qc import validate_music, validate_scripts, validate_visuals
from services.creative_utils import resolve_characters_from_context

# ── validate_music ────────────────────────────────────────────


class TestValidateMusic:
    def test_valid_recommendation_dict(self):
        rec = {"prompt": "Gentle piano", "mood": "calm", "duration": 30}
        result = validate_music(rec)
        assert result["ok"] is True
        assert result["issues"] == []

    def test_valid_recommendation_list(self):
        rec = [{"prompt": "Upbeat guitar", "mood": "happy", "duration": 45}]
        result = validate_music(rec)
        assert result["ok"] is True

    def test_missing_prompt(self):
        rec = {"mood": "calm", "duration": 30}
        result = validate_music(rec)
        assert result["ok"] is False
        assert any("prompt" in i.lower() for i in result["issues"])

    def test_missing_mood(self):
        rec = {"prompt": "Piano", "duration": 30}
        result = validate_music(rec)
        assert result["ok"] is False
        assert any("mood" in i.lower() for i in result["issues"])

    def test_short_duration(self):
        rec = {"prompt": "Piano", "mood": "calm", "duration": 5}
        result = validate_music(rec)
        assert result["ok"] is False
        assert any("duration" in i.lower() for i in result["issues"])

    def test_string_duration_valid(self):
        rec = {"prompt": "Piano", "mood": "calm", "duration": "30"}
        result = validate_music(rec)
        assert result["ok"] is True

    def test_string_duration_invalid(self):
        rec = {"prompt": "Piano", "mood": "calm", "duration": "abc"}
        result = validate_music(rec)
        assert result["ok"] is False

    def test_empty_list(self):
        result = validate_music([])
        assert result["ok"] is False

    def test_empty_dict(self):
        result = validate_music({})
        assert result["ok"] is False


# ── WARN does not trigger retry (W-7 fix) ─────────────────────


def _make_scripts(count: int, language: str = "Korean") -> list[dict]:
    """Helper to create valid script scenes."""
    text = "테스트 스크립트입니다" if language == "Korean" else "This is a test script"
    return [{"order": i, "script": text, "speaker": "A", "duration": 2.5} for i in range(count)]


class TestWarnDoesNotFailScripts:
    """WARN checks should keep ok=True (only FAIL triggers retry)."""

    def test_duration_warn_ok_true(self):
        # 6 scenes × 2.5s = 15s vs target 30s → duration_sum WARN, but no FAIL
        scripts = _make_scripts(6)
        result = validate_scripts(scripts, "Monologue", 30, "Korean")
        assert result["checks"]["duration_sum"] == "WARN"
        assert result["ok"] is True

    def test_script_length_fail_triggers_retry(self):
        # Short script → script_length FAIL (triggers retry)
        scripts = _make_scripts(6)
        scripts[0]["script"] = "짧"  # too short (1 char < 5 min)
        result = validate_scripts(scripts, "Monologue", 30, "Korean")
        assert result["checks"]["script_length"] == "FAIL"
        assert result["ok"] is False

    def test_scene_duration_range_fail(self):
        # Scene with 1.5s duration → scene_duration_range FAIL
        scripts = _make_scripts(6)
        scripts[0]["duration"] = 1.5  # below 2.0s min
        result = validate_scripts(scripts, "Monologue", 30, "Korean")
        assert result["checks"]["scene_duration_range"] == "FAIL"
        assert result["ok"] is False

    def test_scene_duration_range_pass(self):
        # All scenes within 2.0-3.5s → PASS
        scripts = _make_scripts(6)
        result = validate_scripts(scripts, "Monologue", 30, "Korean")
        assert result["checks"]["scene_duration_range"] == "PASS"

    def test_fail_still_fails(self):
        # Wrong speaker → FAIL
        scripts = _make_scripts(6)
        scripts[0]["speaker"] = "X"
        result = validate_scripts(scripts, "Monologue", 30, "Korean")
        assert result["checks"]["speaker_rule"] == "FAIL"
        assert result["ok"] is False


class TestWarnDoesNotFailVisuals:
    def test_camera_warn_ok_true(self):
        scenes = [
            {"image_prompt": "tag1", "camera": "close_up", "environment": "indoor"},
            {"image_prompt": "tag2", "camera": "close_up", "environment": "outdoor"},
        ]
        result = validate_visuals(scenes)
        assert result["checks"]["camera_diversity"] == "WARN"
        assert result["ok"] is True

    def test_env_warn_ok_true(self):
        scenes = [
            {"image_prompt": "tag1", "camera": "close_up", "environment": ""},
            {"image_prompt": "tag2", "camera": "medium_shot", "environment": "park"},
            {"image_prompt": "tag3", "camera": "wide_shot", "environment": "city"},
        ]
        result = validate_visuals(scenes)
        assert result["checks"]["environment_present"] == "WARN"
        assert result["ok"] is True

    def test_missing_prompt_fails(self):
        scenes = [{"camera": "close_up", "environment": "indoor"}]
        result = validate_visuals(scenes)
        assert result["checks"]["image_prompt_present"] == "FAIL"
        assert result["ok"] is False


# ── resolve_characters_from_context ────────────────────────────


class TestResolveCharactersFromContext:
    def test_multi_character(self):
        ctx = {
            "characters": {
                "A": {"id": 1, "name": "Haru", "tags": ["brown_hair"]},
                "B": {"id": 2, "name": "Mina", "tags": ["blonde_hair"]},
            }
        }
        result = resolve_characters_from_context(ctx)
        assert "A" in result
        assert result["A"]["name"] == "Haru"
        assert "B" in result

    def test_legacy_single_character(self):
        ctx = {"character_name": "Haru", "character_id": 1}
        result = resolve_characters_from_context(ctx)
        assert "A" in result
        assert result["A"]["name"] == "Haru"
        assert result["A"]["id"] == 1

    def test_no_characters(self):
        result = resolve_characters_from_context({})
        assert result == {}

    def test_characters_takes_priority(self):
        ctx = {
            "characters": {"A": {"id": 1, "name": "Haru", "tags": []}},
            "character_name": "Old Name",
        }
        result = resolve_characters_from_context(ctx)
        assert result["A"]["name"] == "Haru"

    def test_narrated_dialogue_three_speakers(self):
        ctx = {
            "characters": {
                "Narrator": {"id": 3, "name": "Guide", "tags": []},
                "A": {"id": 1, "name": "Haru", "tags": []},
                "B": {"id": 2, "name": "Mina", "tags": []},
            }
        }
        result = resolve_characters_from_context(ctx)
        assert len(result) == 3
        assert "Narrator" in result
