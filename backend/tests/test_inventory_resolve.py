"""Phase 20-A: inventory_resolve 노드 단위 테스트."""

from __future__ import annotations

import pytest

from services.agent.nodes.inventory_resolve import _validate_casting, inventory_resolve_node
from services.agent.state import ScriptState


class TestValidateCasting:
    """_validate_casting 유효성 검증 로직."""

    def test_valid_casting_passes(self):
        casting = {"character_id": 1, "character_name": "A", "structure": "monologue"}
        state = ScriptState(valid_character_ids=[1, 2, 3], valid_style_profile_ids=[10])
        result = _validate_casting(casting, state)
        assert result is not None
        assert result["character_id"] == 1

    def test_invalid_character_id_removed(self):
        casting = {"character_id": 99, "character_name": "X", "structure": "monologue"}
        state = ScriptState(valid_character_ids=[1, 2, 3], valid_style_profile_ids=[])
        result = _validate_casting(casting, state)
        assert result is not None
        assert result["character_id"] is None

    def test_invalid_char_b_removed(self):
        casting = {
            "character_id": 1,
            "character_name": "A",
            "character_b_id": 99,
            "character_b_name": "X",
            "structure": "dialogue",
        }
        state = ScriptState(valid_character_ids=[1, 2], valid_style_profile_ids=[])
        result = _validate_casting(casting, state)
        assert result is not None
        # dialogue → monologue로 변경됨 (char_b 없으므로)
        assert result["structure"] == "monologue"

    def test_duplicate_ids_fixed(self):
        casting = {
            "character_id": 1,
            "character_name": "A",
            "character_b_id": 1,
            "character_b_name": "A",
            "structure": "dialogue",
        }
        state = ScriptState(valid_character_ids=[1, 2], valid_style_profile_ids=[])
        result = _validate_casting(casting, state)
        assert result is not None
        assert result["character_b_id"] is None

    def test_two_char_structure_without_b_fallback(self):
        casting = {"character_id": 1, "character_name": "A", "structure": "narrated_dialogue"}
        state = ScriptState(valid_character_ids=[1], valid_style_profile_ids=[])
        result = _validate_casting(casting, state)
        assert result is not None
        assert result["structure"] == "monologue"

    def test_invalid_style_removed(self):
        casting = {"character_id": 1, "character_name": "A", "structure": "monologue", "style_profile_id": 99}
        state = ScriptState(valid_character_ids=[1], valid_style_profile_ids=[10, 20])
        result = _validate_casting(casting, state)
        assert result is not None
        assert result["style_profile_id"] is None

    def test_all_invalid_returns_none(self):
        casting = {"character_id": 99, "character_name": "X"}
        state = ScriptState(valid_character_ids=[1], valid_style_profile_ids=[])
        result = _validate_casting(casting, state)
        assert result is None

    def test_empty_valid_ids(self):
        casting = {"character_id": 1, "character_name": "A", "structure": "monologue"}
        state = ScriptState(valid_character_ids=[], valid_style_profile_ids=[])
        result = _validate_casting(casting, state)
        assert result is not None
        assert result["character_id"] is None

    def test_valid_style_kept(self):
        casting = {"character_id": 1, "character_name": "A", "structure": "monologue", "style_profile_id": 10}
        state = ScriptState(valid_character_ids=[1], valid_style_profile_ids=[10, 20])
        result = _validate_casting(casting, state)
        assert result is not None
        assert result["style_profile_id"] == 10


class TestInventoryResolveNode:
    """inventory_resolve_node 통합 동작."""

    @pytest.mark.asyncio
    async def test_skip_when_research_skipped(self):
        state = ScriptState(skip_stages=["research"])
        result = await inventory_resolve_node(state)
        assert result["casting_recommendation"] is None

    @pytest.mark.asyncio
    async def test_no_casting_passthrough(self):
        state = ScriptState(casting_recommendation=None)
        result = await inventory_resolve_node(state)
        assert result["casting_recommendation"] is None

    @pytest.mark.asyncio
    async def test_user_override_character(self):
        """user가 이미 character_id를 선택한 경우 → Director 추천 무시."""
        state = ScriptState(
            character_id=42,
            casting_recommendation={"character_id": 1, "character_name": "A", "structure": "monologue"},
            valid_character_ids=[1, 2],
            valid_style_profile_ids=[],
        )
        result = await inventory_resolve_node(state)
        # user 선택 유지 → character_id는 result에 포함되지 않음
        assert "character_id" not in result

    @pytest.mark.asyncio
    async def test_director_recommendation_applied(self):
        """user가 선택하지 않은 경우 → Director 추천 적용."""
        state = ScriptState(
            casting_recommendation={
                "character_id": 1,
                "character_name": "A",
                "structure": "monologue",
            },
            valid_character_ids=[1, 2],
            valid_style_profile_ids=[],
        )
        result = await inventory_resolve_node(state)
        assert result["character_id"] == 1
        assert result["structure"] == "monologue"

    @pytest.mark.asyncio
    async def test_user_structure_override(self):
        """user가 구조를 선택한 경우 → Director 추천 무시."""
        state = ScriptState(
            structure="dialogue",
            casting_recommendation={"character_id": 1, "character_name": "A", "structure": "monologue"},
            valid_character_ids=[1],
            valid_style_profile_ids=[],
        )
        result = await inventory_resolve_node(state)
        assert "structure" not in result

    @pytest.mark.asyncio
    async def test_graceful_degradation_invalid_casting(self):
        """잘못된 casting dict → None 반환."""
        state = ScriptState(
            casting_recommendation="not a dict",
        )
        result = await inventory_resolve_node(state)
        assert result["casting_recommendation"] is None
