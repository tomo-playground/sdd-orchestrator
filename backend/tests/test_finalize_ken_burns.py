"""Finalize 노드 — ken_burns_preset 검증 테스트."""

from __future__ import annotations

import pytest

from services.agent.nodes.finalize import _validate_ken_burns_presets


class TestValidateKenBurnsPresets:
    """Tests for _validate_ken_burns_presets."""

    def test_valid_preset_preserved(self):
        """유효한 ken_burns_preset은 그대로 유지."""
        scenes = [{"ken_burns_preset": "zoom_in_center", "context_tags": {"emotion": "happy"}}]
        _validate_ken_burns_presets(scenes)
        assert scenes[0]["ken_burns_preset"] == "zoom_in_center"

    def test_invalid_preset_removed(self):
        """무효한 ken_burns_preset은 제거 후 fallback."""
        scenes = [{"ken_burns_preset": "invalid_motion", "context_tags": {"emotion": "happy"}}]
        _validate_ken_burns_presets(scenes)
        # invalid → removed, then emotion fallback
        assert scenes[0]["ken_burns_preset"] != "invalid_motion"
        assert scenes[0].get("ken_burns_preset") is not None

    def test_missing_preset_with_emotion_auto_assigned(self):
        """프리셋 없고 emotion 있으면 자동 배정."""
        scenes = [{"context_tags": {"emotion": "sad"}}]
        _validate_ken_burns_presets(scenes)
        assert scenes[0].get("ken_burns_preset") is not None

    def test_missing_preset_no_emotion_stays_none(self):
        """프리셋 없고 emotion 없으면 None 유지."""
        scenes = [{"context_tags": {"pose": "standing"}}]
        _validate_ken_burns_presets(scenes)
        assert scenes[0].get("ken_burns_preset") is None

    def test_missing_context_tags_stays_none(self):
        """context_tags 자체가 없으면 None 유지."""
        scenes = [{"script": "test"}]
        _validate_ken_burns_presets(scenes)
        assert scenes[0].get("ken_burns_preset") is None

    def test_random_is_invalid(self):
        """'random'은 유효한 씬별 프리셋이 아니다 (전역 전용)."""
        scenes = [{"ken_burns_preset": "random", "context_tags": {"emotion": "calm"}}]
        _validate_ken_burns_presets(scenes)
        # random → removed, then emotion fallback
        assert scenes[0]["ken_burns_preset"] != "random"

    def test_none_preset_is_valid(self):
        """'none'은 유효한 프리셋 (효과 없음)."""
        scenes = [{"ken_burns_preset": "none"}]
        _validate_ken_burns_presets(scenes)
        assert scenes[0]["ken_burns_preset"] == "none"


@pytest.mark.asyncio
async def test_finalize_node_validates_ken_burns():
    """finalize_node가 ken_burns_preset 검증을 실행하는지 확인."""
    from services.agent.nodes.finalize import finalize_node

    state = {
        "skip_stages": [],
        "cinematographer_result": {
            "scenes": [
                {
                    "order": 0,
                    "script": "씬1",
                    "image_prompt": "1girl",
                    "ken_burns_preset": "invalid_preset",
                    "context_tags": {"emotion": "happy"},
                },
                {
                    "order": 1,
                    "script": "씬2",
                    "image_prompt": "1girl",
                    "ken_burns_preset": "zoom_out_center",
                },
            ],
        },
        "tts_designer_result": {"tts_designs": []},
        "sound_designer_result": None,
        "copyright_reviewer_result": None,
    }
    result = await finalize_node(state, {})
    scenes = result["final_scenes"]
    # Scene 0: invalid → auto-assigned from emotion
    assert scenes[0]["ken_burns_preset"] != "invalid_preset"
    # Scene 1: valid → preserved
    assert scenes[1]["ken_burns_preset"] == "zoom_out_center"
