"""Finalize 노드 — _auto_populate_scene_flags 테스트."""

from __future__ import annotations

import pytest

from services.agent.nodes.finalize import _auto_populate_scene_flags


class TestAutoPopulateSceneFlags:
    """Tests for _auto_populate_scene_flags."""

    def test_character_scene_with_pose_enables_controlnet(self):
        """캐릭터 씬 + controlnet_pose → use_controlnet=True."""
        scenes = [{"speaker": "A", "controlnet_pose": "standing"}]
        _auto_populate_scene_flags(scenes, character_id=1)
        assert scenes[0]["use_controlnet"] is True
        assert scenes[0]["controlnet_weight"] == 0.8

    def test_character_scene_without_pose_auto_assigns_default(self):
        """캐릭터 씬 + pose 없음 + character_id → 기본 포즈 자동 할당, ControlNet ON."""
        scenes = [{"speaker": "A"}]
        _auto_populate_scene_flags(scenes, character_id=1)
        assert scenes[0]["controlnet_pose"] == "standing"
        assert scenes[0]["use_controlnet"] is True

    def test_character_scene_without_pose_no_character_disables_controlnet(self):
        """캐릭터 씬 + pose 없음 + character_id=None → use_controlnet=False."""
        scenes = [{"speaker": "A"}]
        _auto_populate_scene_flags(scenes, character_id=None)
        assert scenes[0]["use_controlnet"] is False

    def test_narrator_scene_disables_both(self):
        """Narrator 씬 → use_controlnet=False, use_ip_adapter=False."""
        scenes = [{"speaker": "Narrator", "controlnet_pose": "standing"}]
        _auto_populate_scene_flags(scenes, character_id=1)
        assert scenes[0]["use_controlnet"] is False
        assert scenes[0]["use_ip_adapter"] is False

    def test_character_id_enables_ip_adapter(self):
        """character_id 존재 + 캐릭터 씬 → use_ip_adapter=True."""
        scenes = [{"speaker": "A"}]
        _auto_populate_scene_flags(scenes, character_id=42)
        assert scenes[0]["use_ip_adapter"] is True
        assert scenes[0]["ip_adapter_weight"] == 0.7

    def test_no_character_id_disables_ip_adapter(self):
        """character_id 없음 → use_ip_adapter=False."""
        scenes = [{"speaker": "A"}]
        _auto_populate_scene_flags(scenes, character_id=None)
        assert scenes[0]["use_ip_adapter"] is False

    def test_existing_values_preserved(self):
        """이미 값이 있는 필드는 덮어쓰지 않는다."""
        scenes = [
            {
                "speaker": "A",
                "controlnet_pose": "standing",
                "use_controlnet": False,
                "use_ip_adapter": False,
                "controlnet_weight": 0.5,
                "multi_gen_enabled": True,
            }
        ]
        _auto_populate_scene_flags(scenes, character_id=1)
        assert scenes[0]["use_controlnet"] is False
        assert scenes[0]["use_ip_adapter"] is False
        assert scenes[0]["controlnet_weight"] == 0.5
        assert scenes[0]["multi_gen_enabled"] is True

    def test_multi_gen_default(self):
        """multi_gen_enabled → config 기본값 (False)."""
        scenes = [{"speaker": "A"}]
        _auto_populate_scene_flags(scenes, character_id=None)
        assert scenes[0]["multi_gen_enabled"] is False

    def test_context_tags_pose_used_for_controlnet(self):
        """context_tags.pose가 있으면 controlnet_pose로 자동 할당.
        sitting 계열은 pose 기록은 하되 use_controlnet=False (하체 왜곡 방지).
        """
        scenes = [{"speaker": "A", "context_tags": {"pose": "sitting"}}]
        _auto_populate_scene_flags(scenes, character_id=1)
        assert scenes[0]["controlnet_pose"] == "sitting"
        assert scenes[0]["use_controlnet"] is False

    def test_context_tags_pose_underscore_normalized(self):
        """context_tags.pose 언더바 형식 → POSE_MAPPING 키 매칭."""
        scenes = [{"speaker": "A", "context_tags": {"pose": "arms_crossed"}}]
        _auto_populate_scene_flags(scenes, character_id=1)
        assert scenes[0]["controlnet_pose"] == "arms_crossed"
        assert scenes[0]["use_controlnet"] is True

    def test_invalid_context_pose_falls_back_to_default(self):
        """유효하지 않은 context_tags.pose → DEFAULT_POSE_TAG fallback."""
        scenes = [{"speaker": "A", "context_tags": {"pose": "flying_kick"}}]
        _auto_populate_scene_flags(scenes, character_id=1)
        assert scenes[0]["controlnet_pose"] == "standing"
        assert scenes[0]["use_controlnet"] is True

    def test_context_tags_none_falls_back_to_default(self):
        """context_tags가 None인 경우 DEFAULT_POSE_TAG 할당."""
        scenes = [{"speaker": "A", "context_tags": None}]
        _auto_populate_scene_flags(scenes, character_id=1)
        assert scenes[0]["controlnet_pose"] == "standing"
        assert scenes[0]["use_controlnet"] is True

    def test_multiple_scenes_mixed(self):
        """여러 씬 혼합 — 캐릭터/Narrator 분리 처리."""
        scenes = [
            {"speaker": "A", "controlnet_pose": "sitting"},
            {"speaker": "Narrator"},
            {"speaker": "B", "controlnet_pose": "standing"},
        ]
        _auto_populate_scene_flags(scenes, character_id=1, character_b_id=2)
        # Scene 0: sitting 포즈 → use_controlnet=False (하체 왜곡 방지)
        assert scenes[0]["use_controlnet"] is False
        assert scenes[0]["use_ip_adapter"] is True
        # Scene 1: narrator
        assert scenes[1]["use_controlnet"] is False
        assert scenes[1]["use_ip_adapter"] is False
        # Scene 2: character B with pose
        assert scenes[2]["use_controlnet"] is True
        assert scenes[2]["use_ip_adapter"] is True


class TestFlattenTtsDesigns:
    """Tests for _flatten_tts_designs — tts_design dict 분해 로직."""

    def test_extracts_voice_design_prompt(self):
        """voice_design_prompt가 scene에 복사된다."""
        from services.agent.nodes.finalize import _flatten_tts_designs

        scenes = [{"tts_design": {"voice_design_prompt": "warm tone", "pacing": {}}}]
        _flatten_tts_designs(scenes)
        assert scenes[0]["voice_design_prompt"] == "warm tone"
        assert "tts_design" not in scenes[0]

    def test_extracts_scene_emotion(self):
        """emotion 필드가 scene_emotion으로 복사된다."""
        from services.agent.nodes.finalize import _flatten_tts_designs

        scenes = [{"tts_design": {"emotion": "frustrated", "pacing": {}}}]
        _flatten_tts_designs(scenes)
        assert scenes[0]["scene_emotion"] == "frustrated"

    def test_preset_scene_emotion_without_voice_design_prompt(self):
        """preset 캐릭터: voice_design_prompt 없어도 emotion은 추출된다."""
        from services.agent.nodes.finalize import _flatten_tts_designs

        scenes = [{"tts_design": {"emotion": "happy", "pacing": {"head_padding": 0.2, "tail_padding": 0.8}}}]
        _flatten_tts_designs(scenes)
        assert scenes[0].get("voice_design_prompt") is None
        assert scenes[0]["scene_emotion"] == "happy"
        assert scenes[0]["head_padding"] == 0.2
        assert scenes[0]["tail_padding"] == 0.8

    def test_skip_scene_not_extracted(self):
        """skip=True 씬은 아무것도 추출하지 않는다."""
        from services.agent.nodes.finalize import _flatten_tts_designs

        scenes = [{"tts_design": {"skip": True, "emotion": "sad"}}]
        _flatten_tts_designs(scenes)
        assert "scene_emotion" not in scenes[0]
        assert "voice_design_prompt" not in scenes[0]

    def test_no_tts_design_unchanged(self):
        """tts_design 없는 씬은 그대로 유지된다."""
        from services.agent.nodes.finalize import _flatten_tts_designs

        scenes = [{"speaker": "A", "script": "hello"}]
        _flatten_tts_designs(scenes)
        assert scenes[0] == {"speaker": "A", "script": "hello"}


class TestDialogueCharacterBFlags:
    """Dialogue 구조: character_b_id 기반 speaker B ControlNet/IP-Adapter 테스트."""

    def test_speaker_b_gets_controlnet_with_character_b_id(self):
        """speaker B + character_b_id → sitting 포즈는 use_controlnet=False, IP-Adapter는 ON."""
        scenes = [{"speaker": "B", "context_tags": {"pose": "sitting"}}]
        _auto_populate_scene_flags(scenes, character_id=1, character_b_id=2)
        assert scenes[0]["controlnet_pose"] == "sitting"
        assert scenes[0]["use_controlnet"] is False
        assert scenes[0]["use_ip_adapter"] is True

    def test_speaker_b_no_character_b_id_disables(self):
        """speaker B + character_b_id=None → ControlNet OFF."""
        scenes = [{"speaker": "B"}]
        _auto_populate_scene_flags(scenes, character_id=1, character_b_id=None)
        assert scenes[0]["use_controlnet"] is False
        assert scenes[0]["use_ip_adapter"] is False

    def test_dialogue_mixed_speakers(self):
        """Dialogue: A/B/Narrator 혼합 — 각 speaker에 맞는 character_id 적용."""
        scenes = [
            {"speaker": "A", "context_tags": {"pose": "standing"}},
            {"speaker": "B", "context_tags": {"pose": "sitting"}},
            {"speaker": "Narrator"},
        ]
        _auto_populate_scene_flags(scenes, character_id=1, character_b_id=2)
        # A: uses character_id=1
        assert scenes[0]["use_controlnet"] is True
        assert scenes[0]["use_ip_adapter"] is True
        # B: sitting 포즈 → use_controlnet=False, IP-Adapter ON
        assert scenes[1]["use_controlnet"] is False
        assert scenes[1]["use_ip_adapter"] is True
        # Narrator: always OFF
        assert scenes[2]["use_controlnet"] is False
        assert scenes[2]["use_ip_adapter"] is False

    def test_speaker_a_unaffected_by_character_b_id(self):
        """speaker A는 character_id만 사용, character_b_id 무관."""
        scenes = [{"speaker": "A"}]
        _auto_populate_scene_flags(scenes, character_id=None, character_b_id=2)
        assert scenes[0]["use_controlnet"] is False
        assert scenes[0]["use_ip_adapter"] is False


@pytest.mark.asyncio
async def test_finalize_node_populates_scene_flags():
    """finalize_node 통합 테스트 — 씬 플래그 자동 할당 확인."""
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
    assert final[0]["use_controlnet"] is True
    assert final[0]["use_ip_adapter"] is True
    assert final[1]["use_controlnet"] is False
    assert final[1]["use_ip_adapter"] is False


@pytest.mark.asyncio
async def test_finalize_express_mode_auto_assigns_controlnet():
    """Express 모드 통합 — controlnet_pose 없이도 자동 할당되어 ControlNet ON."""
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
    # 캐릭터 씬: 기본 포즈 자동 할당 → ControlNet ON
    assert final[0]["controlnet_pose"] == "standing"
    assert final[0]["use_controlnet"] is True
    # Narrator 씬: ControlNet OFF 유지
    assert final[1]["use_controlnet"] is False
    # 캐릭터 씬 B: 기본 포즈 자동 할당
    assert final[2]["controlnet_pose"] == "standing"
    assert final[2]["use_controlnet"] is True
