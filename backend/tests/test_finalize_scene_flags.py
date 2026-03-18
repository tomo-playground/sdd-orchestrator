"""Finalize 노드 — _auto_populate_scene_flags 테스트."""

from __future__ import annotations

import pytest

from services.agent.nodes.finalize import _auto_populate_scene_flags


class TestAutoPopulateSceneFlags:
    """Tests for _auto_populate_scene_flags."""

    def test_character_scene_controlnet_default_off(self):
        """캐릭터 씬 — ControlNet 기본 OFF (프롬프트 충성도 충분)."""
        scenes = [{"speaker": "A", "controlnet_pose": "standing"}]
        _auto_populate_scene_flags(scenes, character_id=1)
        assert scenes[0]["is_controlnet_enabled"] is False

    def test_character_scene_ip_adapter_on(self):
        """캐릭터 씬 + character_id → use_ip_adapter=True."""
        scenes = [{"speaker": "A"}]
        _auto_populate_scene_flags(scenes, character_id=42)
        assert scenes[0]["use_ip_adapter"] is True

    def test_no_character_id_disables_ip_adapter(self):
        """character_id 없음 → use_ip_adapter=False."""
        scenes = [{"speaker": "A"}]
        _auto_populate_scene_flags(scenes, character_id=None)
        assert scenes[0]["use_ip_adapter"] is False

    def test_narrator_scene_disables_both(self):
        """Narrator 씬 → ControlNet OFF, IP-Adapter OFF."""
        scenes = [{"speaker": "Narrator", "controlnet_pose": "standing"}]
        _auto_populate_scene_flags(scenes, character_id=1)
        assert scenes[0]["is_controlnet_enabled"] is False
        assert scenes[0]["use_ip_adapter"] is False

    def test_existing_values_preserved(self):
        """이미 값이 있는 필드는 덮어쓰지 않는다."""
        scenes = [
            {
                "speaker": "A",
                "controlnet_pose": "standing",
                "is_controlnet_enabled": True,  # 명시적 ON → 보존
                "use_ip_adapter": False,
                "controlnet_weight": 0.5,
                "multi_gen_enabled": True,
            }
        ]
        _auto_populate_scene_flags(scenes, character_id=1)
        assert scenes[0]["is_controlnet_enabled"] is True  # 명시값 보존
        assert scenes[0]["use_ip_adapter"] is False
        assert scenes[0]["controlnet_weight"] == 0.5
        assert scenes[0]["multi_gen_enabled"] is True

    def test_multi_gen_default(self):
        """multi_gen_enabled → config 기본값."""
        from config import DEFAULT_MULTI_GEN_ENABLED

        scenes = [{"speaker": "A"}]
        _auto_populate_scene_flags(scenes, character_id=None)
        assert scenes[0]["multi_gen_enabled"] is DEFAULT_MULTI_GEN_ENABLED

    def test_context_tags_pose_recorded_but_controlnet_off(self):
        """context_tags.pose → controlnet_pose에 기록은 하되 ControlNet OFF."""
        scenes = [{"speaker": "A", "context_tags": {"pose": "sitting"}}]
        _auto_populate_scene_flags(scenes, character_id=1)
        assert scenes[0]["controlnet_pose"] == "sitting"
        assert scenes[0]["is_controlnet_enabled"] is False

    def test_multiple_scenes_mixed(self):
        """여러 씬 혼합 — 모두 ControlNet OFF, IP-Adapter는 캐릭터만 ON."""
        scenes = [
            {"speaker": "A", "controlnet_pose": "sitting"},
            {"speaker": "Narrator"},
            {"speaker": "B", "controlnet_pose": "standing"},
        ]
        _auto_populate_scene_flags(scenes, character_id=1, character_b_id=2)
        assert scenes[0]["is_controlnet_enabled"] is False
        assert scenes[0]["use_ip_adapter"] is True
        assert scenes[1]["is_controlnet_enabled"] is False
        assert scenes[1]["use_ip_adapter"] is False
        assert scenes[2]["is_controlnet_enabled"] is False
        assert scenes[2]["use_ip_adapter"] is True


class TestFlattenTtsDesigns:
    """Tests for _flatten_tts_designs — tts_design dict 분해 로직."""

    def test_extracts_voice_design_prompt(self):
        from services.agent.nodes.finalize import _flatten_tts_designs

        scenes = [{"tts_design": {"voice_design_prompt": "warm tone", "pacing": {}}}]
        _flatten_tts_designs(scenes)
        assert scenes[0]["voice_design_prompt"] == "warm tone"
        assert "tts_design" not in scenes[0]

    def test_extracts_scene_emotion(self):
        from services.agent.nodes.finalize import _flatten_tts_designs

        scenes = [{"tts_design": {"emotion": "frustrated", "pacing": {}}}]
        _flatten_tts_designs(scenes)
        assert scenes[0]["scene_emotion"] == "frustrated"

    def test_preset_scene_emotion_without_voice_design_prompt(self):
        from services.agent.nodes.finalize import _flatten_tts_designs

        scenes = [{"tts_design": {"emotion": "happy", "pacing": {"head_padding": 0.2, "tail_padding": 0.8}}}]
        _flatten_tts_designs(scenes)
        assert scenes[0].get("voice_design_prompt") is None
        assert scenes[0]["scene_emotion"] == "happy"
        assert scenes[0]["head_padding"] == 0.2
        assert scenes[0]["tail_padding"] == 0.8

    def test_skip_scene_not_extracted(self):
        from services.agent.nodes.finalize import _flatten_tts_designs

        scenes = [{"tts_design": {"skip": True, "emotion": "sad"}}]
        _flatten_tts_designs(scenes)
        assert "scene_emotion" not in scenes[0]

    def test_no_tts_design_unchanged(self):
        from services.agent.nodes.finalize import _flatten_tts_designs

        scenes = [{"speaker": "A", "script": "hello"}]
        _flatten_tts_designs(scenes)
        assert scenes[0] == {"speaker": "A", "script": "hello"}


class TestDialogueCharacterBFlags:
    """Dialogue 구조: character_b_id 기반 speaker B 테스트."""

    def test_speaker_b_controlnet_off_ip_adapter_on(self):
        """speaker B + character_b_id → ControlNet OFF, IP-Adapter ON."""
        scenes = [{"speaker": "B", "context_tags": {"pose": "sitting"}}]
        _auto_populate_scene_flags(scenes, character_id=1, character_b_id=2)
        assert scenes[0]["controlnet_pose"] == "sitting"
        assert scenes[0]["is_controlnet_enabled"] is False
        assert scenes[0]["use_ip_adapter"] is True

    def test_speaker_b_no_character_b_id_disables(self):
        """speaker B + character_b_id=None → 모두 OFF."""
        scenes = [{"speaker": "B"}]
        _auto_populate_scene_flags(scenes, character_id=1, character_b_id=None)
        assert scenes[0]["is_controlnet_enabled"] is False
        assert scenes[0]["use_ip_adapter"] is False

    def test_dialogue_mixed_speakers(self):
        """Dialogue: A/B/Narrator — 모두 ControlNet OFF."""
        scenes = [
            {"speaker": "A", "context_tags": {"pose": "standing"}},
            {"speaker": "B", "context_tags": {"pose": "sitting"}},
            {"speaker": "Narrator"},
        ]
        _auto_populate_scene_flags(scenes, character_id=1, character_b_id=2)
        assert scenes[0]["is_controlnet_enabled"] is False
        assert scenes[0]["use_ip_adapter"] is True
        assert scenes[1]["is_controlnet_enabled"] is False
        assert scenes[1]["use_ip_adapter"] is True
        assert scenes[2]["is_controlnet_enabled"] is False
        assert scenes[2]["use_ip_adapter"] is False


@pytest.mark.asyncio
async def test_finalize_node_populates_scene_flags():
    """finalize_node 통합 — 일반 씬 ControlNet OFF."""
    from unittest.mock import patch

    from services.agent.nodes.finalize import finalize_node

    state = {
        "draft_scenes": [
            {"script": "test", "speaker": "A", "controlnet_pose": "standing", "duration": 3},
            {"script": "bg", "speaker": "Narrator", "duration": 3},
        ],
        "skip_stages": ["production"],
        "character_id": 1,
        "duration": 30,
        "language": "Korean",
    }

    with (
        patch("services.agent.nodes.finalize.get_db_session"),
        patch(
            "services.agent.nodes._finalize_validators._get_character_info",
            return_value=(None, False),
        ),
    ):
        result = await finalize_node(state, config={})

    final = result["final_scenes"]
    assert final[0]["is_controlnet_enabled"] is False  # 일반 씬 OFF
    assert final[0]["use_ip_adapter"] is True
    assert final[1]["is_controlnet_enabled"] is False
    assert final[1]["use_ip_adapter"] is False


@pytest.mark.asyncio
async def test_finalize_express_mode_controlnet_off():
    """Express 모드 — 일반 씬 ControlNet OFF."""
    from unittest.mock import patch

    from services.agent.nodes.finalize import finalize_node

    state = {
        "draft_scenes": [
            {"script": "씬1", "speaker": "A", "duration": 3},
            {"script": "배경", "speaker": "Narrator", "duration": 3},
            {"script": "씬2", "speaker": "B", "duration": 3},
        ],
        "skip_stages": ["research", "concept", "production", "explain"],
        "character_id": 1,
        "character_b_id": 2,
        "duration": 30,
        "language": "Korean",
    }

    with (
        patch("services.agent.nodes.finalize.get_db_session"),
        patch(
            "services.agent.nodes._finalize_validators._get_character_info",
            return_value=(None, False),
        ),
    ):
        result = await finalize_node(state, config={})

    final = result["final_scenes"]
    # 캐릭터 씬: ControlNet OFF, IP-Adapter ON
    assert final[0]["is_controlnet_enabled"] is False
    assert final[0]["use_ip_adapter"] is True
    # Narrator: 모두 OFF
    assert final[1]["is_controlnet_enabled"] is False
    # 캐릭터 B: ControlNet OFF, IP-Adapter ON
    assert final[2]["is_controlnet_enabled"] is False
    assert final[2]["use_ip_adapter"] is True
