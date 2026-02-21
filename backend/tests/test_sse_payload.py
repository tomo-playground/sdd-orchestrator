"""SSE payload 구성 함수 단위 테스트.

검증 항목:
1. _build_node_payload: finalize 노드에서 sound_recommendation 포함
2. _state_to_response: 동기 응답에서 sound_recommendation 포함
3. 경계 케이스: sound_recommendation 없음, None, Quick 모드
"""

from __future__ import annotations

from routers.scripts import _build_node_payload, _state_to_response


# ── _build_node_payload ──────────────────────────────────────


class TestBuildNodePayloadSoundRecommendation:
    """finalize 노드 payload에 sound_recommendation이 포함되는지 검증."""

    def test_finalize_includes_sound_recommendation(self):
        """Full 모드 finalize에서 sound_recommendation이 result에 포함된다."""
        node_output = {
            "final_scenes": [{"scene_id": 1, "script": "테스트"}],
            "sound_recommendation": {"prompt": "calm piano", "mood": "peaceful"},
        }
        char_ids: list[int | None] = [10, None]

        payload = _build_node_payload("finalize", "thread-1", node_output, char_ids)

        assert payload["status"] == "completed"
        assert payload["result"]["sound_recommendation"] == {
            "prompt": "calm piano",
            "mood": "peaceful",
        }

    def test_finalize_sound_recommendation_none(self):
        """Quick 모드에서 sound_recommendation이 None이면 None으로 포함된다."""
        node_output = {
            "final_scenes": [{"scene_id": 1}],
            "sound_recommendation": None,
        }
        char_ids: list[int | None] = [None, None]

        payload = _build_node_payload("finalize", "thread-1", node_output, char_ids)

        assert payload["status"] == "completed"
        assert payload["result"]["sound_recommendation"] is None

    def test_finalize_missing_sound_recommendation(self):
        """sound_recommendation 키 자체가 없으면 None으로 반환된다."""
        node_output = {
            "final_scenes": [{"scene_id": 1}],
        }
        char_ids: list[int | None] = [None, None]

        payload = _build_node_payload("finalize", "thread-1", node_output, char_ids)

        assert payload["status"] == "completed"
        assert payload["result"]["sound_recommendation"] is None

    def test_finalize_preserves_character_ids(self):
        """sound_recommendation 추가가 기존 character_id를 손상시키지 않는다."""
        node_output = {
            "final_scenes": [{"scene_id": 1}],
            "sound_recommendation": {"mood": "epic"},
        }
        char_ids: list[int | None] = [42, 99]

        payload = _build_node_payload("finalize", "thread-1", node_output, char_ids)

        assert payload["result"]["character_id"] == 42
        assert payload["result"]["character_b_id"] == 99
        assert payload["result"]["scenes"] == [{"scene_id": 1}]

    def test_non_finalize_node_no_sound_recommendation(self):
        """finalize 외 노드에서는 result 자체가 없다."""
        node_output = {"draft_scenes": [{"scene_id": 1}]}
        char_ids: list[int | None] = [None, None]

        payload = _build_node_payload("writer", "thread-1", node_output, char_ids)

        assert "result" not in payload
        assert payload["status"] == "running"

    def test_finalize_no_scenes_no_result(self):
        """final_scenes가 None이면 completed가 아니고 result도 없다."""
        node_output = {"final_scenes": None, "sound_recommendation": {"mood": "calm"}}
        char_ids: list[int | None] = [None, None]

        payload = _build_node_payload("finalize", "thread-1", node_output, char_ids)

        assert payload["status"] == "running"
        assert "result" not in payload


# ── _state_to_response ───────────────────────────────────────


class TestStateToResponseSoundRecommendation:
    """동기 응답에 sound_recommendation이 포함되는지 검증."""

    def test_includes_sound_recommendation(self):
        """sound_recommendation이 응답에 포함된다."""
        result = {
            "final_scenes": [{"scene_id": 1}],
            "draft_character_id": 10,
            "draft_character_b_id": None,
            "sound_recommendation": {"prompt": "epic orchestra", "mood": "heroic"},
        }

        resp = _state_to_response(result)

        assert resp["sound_recommendation"] == {
            "prompt": "epic orchestra",
            "mood": "heroic",
        }

    def test_sound_recommendation_none(self):
        """sound_recommendation이 없으면 None."""
        result = {
            "final_scenes": [{"scene_id": 1}],
            "draft_character_id": None,
            "draft_character_b_id": None,
        }

        resp = _state_to_response(result)

        assert resp["sound_recommendation"] is None

    def test_preserves_other_fields(self):
        """sound_recommendation 추가가 기존 필드를 손상시키지 않는다."""
        result = {
            "final_scenes": [{"scene_id": 1}, {"scene_id": 2}],
            "draft_character_id": 5,
            "draft_character_b_id": 7,
            "sound_recommendation": {"mood": "calm"},
            "explanation_result": {"summary": "설명"},
        }

        resp = _state_to_response(result)

        assert len(resp["scenes"]) == 2
        assert resp["character_id"] == 5
        assert resp["character_b_id"] == 7
        assert resp["explanation"] == {"summary": "설명"}
