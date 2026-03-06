"""Phase 20-A: inventory_resolve 노드 단위 테스트."""

from __future__ import annotations

import pytest

from services.agent.nodes.inventory_resolve import _validate_casting, inventory_resolve_node
from services.agent.state import ScriptState


class TestValidateCasting:
    """_validate_casting 유효성 검증 로직."""

    def test_valid_casting_passes(self):
        casting = {"character_a_id": 1, "character_a_name": "A", "structure": "monologue"}
        state = ScriptState(valid_character_ids=[1, 2, 3])
        result = _validate_casting(casting, state)
        assert result is not None
        assert result["character_a_id"] == 1

    def test_invalid_character_a_id_removed(self):
        casting = {"character_a_id": 99, "character_a_name": "X", "structure": "monologue"}
        state = ScriptState(valid_character_ids=[1, 2, 3])
        result = _validate_casting(casting, state)
        assert result is not None
        assert result["character_a_id"] is None

    def test_invalid_char_b_auto_assigned(self):
        """유효하지 않은 character_b_id → 다른 유효 캐릭터로 자동 할당."""
        casting = {
            "character_a_id": 1,
            "character_a_name": "A",
            "character_b_id": 99,
            "character_b_name": "X",
            "structure": "dialogue",
        }
        state = ScriptState(valid_character_ids=[1, 2])
        result = _validate_casting(casting, state)
        assert result is not None
        # 다른 유효 캐릭터(2)가 자동 할당되어 dialogue 유지
        assert result["structure"] == "dialogue"
        assert result["character_b_id"] == 2

    def test_invalid_char_b_no_alternative_fallback(self):
        """유효하지 않은 character_b_id + 대안 없음 → monologue 강등."""
        casting = {
            "character_a_id": 1,
            "character_a_name": "A",
            "character_b_id": 99,
            "character_b_name": "X",
            "structure": "dialogue",
        }
        state = ScriptState(valid_character_ids=[1])
        result = _validate_casting(casting, state)
        assert result is not None
        assert result["structure"] == "monologue"

    def test_duplicate_ids_auto_assigned(self):
        """중복 ID → character_b를 다른 캐릭터로 자동 할당."""
        casting = {
            "character_a_id": 1,
            "character_a_name": "A",
            "character_b_id": 1,
            "character_b_name": "A",
            "structure": "dialogue",
        }
        state = ScriptState(valid_character_ids=[1, 2])
        result = _validate_casting(casting, state)
        assert result is not None
        assert result["character_b_id"] == 2
        assert result["structure"] == "dialogue"

    def test_duplicate_ids_no_alternative(self):
        """중복 ID + 대안 없음 → monologue 강등."""
        casting = {
            "character_a_id": 1,
            "character_a_name": "A",
            "character_b_id": 1,
            "character_b_name": "A",
            "structure": "dialogue",
        }
        state = ScriptState(valid_character_ids=[1])
        result = _validate_casting(casting, state)
        assert result is not None
        assert result["character_b_id"] is None
        assert result["structure"] == "monologue"

    def test_two_char_structure_without_b_auto_assigned(self):
        """2인 구조 + character_b 없음 + 대안 있음 → 자동 할당."""
        casting = {"character_a_id": 1, "character_a_name": "A", "structure": "narrated_dialogue"}
        state = ScriptState(valid_character_ids=[1, 3])
        result = _validate_casting(casting, state)
        assert result is not None
        assert result["structure"] == "narrated_dialogue"
        assert result["character_b_id"] == 3

    def test_two_char_structure_without_b_no_alternative(self):
        """2인 구조 + character_b 없음 + 대안 없음 → monologue 강등."""
        casting = {"character_a_id": 1, "character_a_name": "A", "structure": "narrated_dialogue"}
        state = ScriptState(valid_character_ids=[1])
        result = _validate_casting(casting, state)
        assert result is not None
        assert result["structure"] == "monologue"

    def test_all_invalid_returns_none(self):
        casting = {"character_a_id": 99, "character_a_name": "X"}
        state = ScriptState(valid_character_ids=[1])
        result = _validate_casting(casting, state)
        assert result is None

    def test_empty_valid_ids(self):
        casting = {"character_a_id": 1, "character_a_name": "A", "structure": "monologue"}
        state = ScriptState(valid_character_ids=[])
        result = _validate_casting(casting, state)
        assert result is not None
        assert result["character_a_id"] is None

    def test_style_profile_id_passthrough(self):
        """style_profile_id는 검증 없이 그대로 통과 (Group 소유권 체제)."""
        casting = {"character_a_id": 1, "character_a_name": "A", "structure": "monologue", "style_profile_id": 99}
        state = ScriptState(valid_character_ids=[1])
        result = _validate_casting(casting, state)
        assert result is not None
        assert result["style_profile_id"] == 99


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
            casting_recommendation={"character_a_id": 1, "character_a_name": "A", "structure": "monologue"},
            valid_character_ids=[1, 2],
        )
        result = await inventory_resolve_node(state)
        # user 선택 유지 → character_id는 result에 포함되지 않음
        assert "character_id" not in result

    @pytest.mark.asyncio
    async def test_director_recommendation_applied(self):
        """user가 선택하지 않은 경우 → Director 추천 적용."""
        state = ScriptState(
            casting_recommendation={
                "character_a_id": 1,
                "character_a_name": "A",
                "structure": "monologue",
            },
            valid_character_ids=[1, 2],
        )
        result = await inventory_resolve_node(state)
        # casting의 character_a_id가 ScriptState의 character_id로 merge됨
        assert result["character_id"] == 1
        assert result["structure"] == "monologue"

    @pytest.mark.asyncio
    async def test_user_structure_override(self):
        """user가 구조를 선택한 경우 → Director 추천 무시."""
        state = ScriptState(
            structure="dialogue",
            casting_recommendation={"character_a_id": 1, "character_a_name": "A", "structure": "monologue"},
            valid_character_ids=[1],
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
