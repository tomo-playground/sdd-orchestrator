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

    def test_character_scene_without_pose_disables_controlnet(self):
        """캐릭터 씬 + pose 없음 → use_controlnet=False."""
        scenes = [{"speaker": "A"}]
        _auto_populate_scene_flags(scenes, character_id=1)
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

    def test_multiple_scenes_mixed(self):
        """여러 씬 혼합 — 캐릭터/Narrator 분리 처리."""
        scenes = [
            {"speaker": "A", "controlnet_pose": "sitting"},
            {"speaker": "Narrator"},
            {"speaker": "B", "controlnet_pose": "standing"},
        ]
        _auto_populate_scene_flags(scenes, character_id=1)
        # Scene 0: character with pose
        assert scenes[0]["use_controlnet"] is True
        assert scenes[0]["use_ip_adapter"] is True
        # Scene 1: narrator
        assert scenes[1]["use_controlnet"] is False
        assert scenes[1]["use_ip_adapter"] is False
        # Scene 2: character with pose
        assert scenes[2]["use_controlnet"] is True
        assert scenes[2]["use_ip_adapter"] is True


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

    with patch("services.agent.nodes.finalize.get_db_session"):
        result = await finalize_node(state, config={})

    final = result["final_scenes"]
    assert final[0]["use_controlnet"] is True
    assert final[0]["use_ip_adapter"] is True
    assert final[1]["use_controlnet"] is False
    assert final[1]["use_ip_adapter"] is False
