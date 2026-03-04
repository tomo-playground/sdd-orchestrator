"""파이프라인 플로우 검수에서 발견된 이슈별 테스트 시나리오.

각 이슈를 재현·방어하는 시나리오:
1. [MEDIUM] state["topic"] 직접 접근 KeyError (writer, revise)
2. [MEDIUM] interrupt() 반환값 비-dict 방어 (director_plan_gate, concept_gate)
3. [LOW] human_gate revision_count 리셋 후 무한 수정 가능성
4. [LOW] learn 노드 draft_character_id vs character_id 불일치
5. [INFO] routing 엣지 케이스 (review_result=None, 중첩 루프 카운터)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langgraph.store.memory import InMemoryStore

# ═══════════════════════════════════════════════════════
# 1. state["topic"] 직접 접근 KeyError
# ═══════════════════════════════════════════════════════


class TestWriterTopicKeyError:
    """writer_node에서 topic 누락 시 안전 처리 검증.

    state.get("topic", "") 방어 코드로 KeyError 대신 빈 문자열 처리.
    """

    @pytest.mark.asyncio
    @patch("services.agent.nodes.writer.gemini_client")
    @patch("services.agent.nodes.writer.template_env")
    async def test_writer_missing_topic_no_crash(self, _mock_tenv, _mock_gemini):
        """topic 누락 시 KeyError 없이 error 또는 draft_scenes 반환."""
        from services.agent.nodes.writer import writer_node

        _mock_tenv.get_template.return_value.render.return_value = "prompt"
        mock_resp = MagicMock()
        mock_resp.text = '{"scenes": [{"order": 1, "text": "test", "duration": 3}]}'
        _mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_resp)

        state = {
            "description": "설명",
            "duration": 30,
            "language": "Korean",
            "structure": "Monologue",
        }
        result = await writer_node(state)
        assert "error" in result or "draft_scenes" in result

    @pytest.mark.asyncio
    @patch("services.agent.nodes.writer.gemini_client")
    @patch("services.agent.nodes.writer.template_env")
    async def test_writer_empty_topic_no_crash(self, _mock_tenv, _mock_gemini):
        """topic이 빈 문자열이면 crash 없이 진행."""
        from services.agent.nodes.writer import writer_node

        _mock_tenv.get_template.return_value.render.return_value = "prompt"
        mock_resp = MagicMock()
        mock_resp.text = '{"scenes": [{"order": 1, "text": "test", "duration": 3}]}'
        _mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_resp)

        state = {
            "topic": "",
            "description": "",
            "duration": 30,
            "language": "Korean",
            "structure": "Monologue",
        }
        result = await writer_node(state)
        # 빈 topic은 KeyError가 아님 — error 또는 draft_scenes 중 하나
        assert "error" in result or "draft_scenes" in result


class TestReviseTopicKeyError:
    """revise_node의 _make_request에서 topic 누락 시 안전 처리 검증.

    state.get("topic", "") 방어 코드로 KeyError 대신 빈 문자열로 진행.
    """

    @pytest.mark.asyncio
    async def test_revise_missing_topic_no_crash(self):
        """topic 누락 시 revise는 빈 문자열로 진행, crash 없음."""
        from services.agent.nodes.revise import revise_node

        state = {
            "draft_scenes": [{"order": 1, "text": "test", "duration": 3}],
            "review_result": {
                "passed": False,
                "errors": ["total_duration 초과 (expected 30, got 45)"],
            },
            "revision_count": 0,
            # topic 의도적 누락 — state.get("topic", "")로 방어됨
        }
        result = await revise_node(state)
        # crash 없이 draft_scenes 또는 error 반환
        assert "draft_scenes" in result or "error" in result


# ═══════════════════════════════════════════════════════
# 2. interrupt() 반환값 비-dict 방어
# ═══════════════════════════════════════════════════════


class TestDirectorPlanGateInterruptDefense:
    """director_plan_gate의 interrupt 응답 방어."""

    def test_handle_revise_max_count_forces_proceed(self):
        """plan_revision_count > 2 → 강제 proceed."""
        from services.agent.nodes.director_plan_gate import _handle_revise

        state = {"plan_revision_count": 2, "description": "기존 설명"}
        result = _handle_revise(state, {"feedback": "수정해주세요"})
        # count=2+1=3 > 2 → 강제 proceed
        assert result["plan_action"] == "proceed"
        assert result["plan_revision_count"] == 3

    def test_handle_revise_appends_feedback(self):
        """피드백이 description에 추가된다."""
        from services.agent.nodes.director_plan_gate import _handle_revise

        state = {"plan_revision_count": 0, "description": "원본"}
        result = _handle_revise(state, {"feedback": "더 감성적으로"})
        assert result["plan_action"] == "revise"
        assert "더 감성적으로" in result["description"]
        assert result["plan_revision_count"] == 1

    def test_handle_revise_empty_feedback(self):
        """피드백이 비어있으면 description 유지."""
        from services.agent.nodes.director_plan_gate import _handle_revise

        state = {"plan_revision_count": 0, "description": "원본"}
        result = _handle_revise(state, {})
        assert result["description"] == "원본"

    @pytest.mark.asyncio
    async def test_auto_mode_skips_interrupt(self):
        """auto 모드 → interrupt 없이 즉시 proceed."""
        from services.agent.nodes.director_plan_gate import director_plan_gate_node

        state = {"interaction_mode": "auto", "director_plan": {"goal": "test"}}
        result = await director_plan_gate_node(state)
        assert result["plan_action"] == "proceed"

    @pytest.mark.asyncio
    async def test_auto_approve_skips_interrupt(self):
        """auto_approve=True → interrupt 없이 즉시 proceed."""
        from services.agent.nodes.director_plan_gate import director_plan_gate_node

        state = {"interaction_mode": "guided", "auto_approve": True}
        result = await director_plan_gate_node(state)
        assert result["plan_action"] == "proceed"


class TestConceptGateInterruptDefense:
    """concept_gate의 interrupt 응답 방어."""

    def test_handle_regenerate_max_count_forces_select(self):
        """concept_regen_count > MAX → 강제 select."""
        from services.agent.nodes.concept_gate import _handle_regenerate

        state = {"concept_regen_count": 2}  # MAX_CONCEPT_REGEN=2 기본
        result = _handle_regenerate(state)
        # count=2+1=3 > 2 → 강제 select
        assert result["concept_action"] == "select"

    def test_handle_regenerate_within_limit(self):
        """재생성 한도 내 → regenerate 반환."""
        from services.agent.nodes.concept_gate import _handle_regenerate

        state = {"concept_regen_count": 0}
        result = _handle_regenerate(state)
        assert result["concept_action"] == "regenerate"
        assert result["concept_regen_count"] == 1

    def test_handle_select_valid_index(self):
        """유효한 concept_id → 해당 candidate 선택."""
        from services.agent.nodes.concept_gate import _handle_select

        critic_result = {"candidates": [{"title": "A"}, {"title": "B"}]}
        result = _handle_select({"concept_id": 1}, critic_result)
        assert result["critic_result"]["selected_concept"]["title"] == "B"

    def test_handle_select_out_of_range(self):
        """concept_id 범위 초과 → 첫 번째 candidate로 폴백."""
        from services.agent.nodes.concept_gate import _handle_select

        critic_result = {"candidates": [{"title": "A"}, {"title": "B"}]}
        result = _handle_select({"concept_id": 99}, critic_result)
        assert result["critic_result"]["selected_concept"]["title"] == "A"

    def test_handle_select_empty_candidates(self):
        """candidates 비어있을 때 → 빈 dict 반환."""
        from services.agent.nodes.concept_gate import _handle_select

        result = _handle_select({"concept_id": 0}, {"candidates": []})
        assert result["critic_result"]["selected_concept"] == {}

    def test_handle_custom_concept(self):
        """사용자 직접 입력 컨셉 주입."""
        from services.agent.nodes.concept_gate import _handle_custom_concept

        critic_result = {"candidates": [{"title": "A"}], "selected_concept": {"title": "A"}}
        custom = {"title": "내 아이디어", "hook": "직접 작성"}
        result = _handle_custom_concept({"custom_concept": custom}, critic_result)
        assert result["critic_result"]["selected_concept"] == custom
        assert result["concept_action"] == "select"

    @pytest.mark.asyncio
    async def test_auto_mode_skips_interrupt(self):
        """auto 모드 → interrupt 없이 즉시 select."""
        from services.agent.nodes.concept_gate import concept_gate_node

        state = {"interaction_mode": "auto", "critic_result": {"selected_concept": {"title": "A"}}}
        result = await concept_gate_node(state)
        assert result["concept_action"] == "select"


# ═══════════════════════════════════════════════════════
# 3. human_gate revision_count 리셋
# ═══════════════════════════════════════════════════════


class TestHumanGateRevisionReset:
    """human_gate에서 revision_count 리셋 시나리오."""

    @pytest.mark.asyncio
    async def test_non_hands_on_auto_approves(self):
        """hands_on 아닌 모드 → 즉시 approve."""
        from services.agent.nodes.human_gate import human_gate_node

        for mode in ["auto", "guided"]:
            state = {"interaction_mode": mode}
            result = await human_gate_node(state)
            assert result["human_action"] == "approve"
            assert "revision_count" not in result

    @pytest.mark.asyncio
    @patch("services.agent.nodes.human_gate.interrupt")
    async def test_revise_resets_revision_count(self, mock_interrupt):
        """revise 선택 시 revision_count가 0으로 리셋된다."""
        from services.agent.nodes.human_gate import human_gate_node

        mock_interrupt.return_value = {"action": "revise", "feedback": "더 재미있게"}
        state = {"interaction_mode": "hands_on", "revision_count": 3}
        result = await human_gate_node(state)
        assert result["human_action"] == "revise"
        assert result["revision_count"] == 0
        assert result["human_feedback"] == "더 재미있게"

    @pytest.mark.asyncio
    @patch("services.agent.nodes.human_gate.interrupt")
    async def test_approve_does_not_reset_count(self, mock_interrupt):
        """approve 선택 시 revision_count 미변경."""
        from services.agent.nodes.human_gate import human_gate_node

        mock_interrupt.return_value = {"action": "approve"}
        state = {"interaction_mode": "hands_on", "revision_count": 2}
        result = await human_gate_node(state)
        assert result["human_action"] == "approve"
        assert "revision_count" not in result


# ═══════════════════════════════════════════════════════
# 4. learn 노드: draft_character_id vs character_id
# ═══════════════════════════════════════════════════════


class TestLearnCharacterIdMismatch:
    """learn 노드가 character_id (원본)을 사용하는지 검증."""

    @pytest.fixture
    def store(self):
        return InMemoryStore()

    @pytest.fixture
    def config(self):
        return {"configurable": {"thread_id": "test-thread"}}

    @pytest.fixture
    def scenes(self):
        return [{"scene_id": 1, "script": "테스트", "speaker": "A", "duration": 3}]

    @pytest.mark.asyncio
    async def test_uses_character_id_not_draft(self, store, config, scenes):
        """learn은 character_id(원본)을 사용하고 draft_character_id는 무시한다."""
        from services.agent.nodes.learn import learn_node

        state = {
            "topic": "테스트",
            "final_scenes": scenes,
            "structure": "Monologue",
            "character_id": 42,  # 원본 (inventory_resolve가 확정)
            "draft_character_id": 99,  # writer가 반환한 임시 ID
        }
        await learn_node(state, config, store=store)

        # character 42가 기록되어야 함
        items_42 = await store.asearch(("character", "42"))
        assert len(items_42) == 1
        assert items_42[0].value["generation_count"] == 1

        # draft_character_id(99)는 기록되지 않아야 함
        items_99 = await store.asearch(("character", "99"))
        assert len(items_99) == 0

    @pytest.mark.asyncio
    async def test_both_characters_tracked(self, store, config, scenes):
        """character_id와 character_b_id 모두 추적된다."""
        from services.agent.nodes.learn import learn_node

        state = {
            "topic": "대화 테스트",
            "final_scenes": scenes,
            "structure": "Dialogue",
            "character_id": 10,
            "character_b_id": 20,
        }
        await learn_node(state, config, store=store)

        items_a = await store.asearch(("character", "10"))
        items_b = await store.asearch(("character", "20"))
        assert len(items_a) == 1
        assert len(items_b) == 1

    @pytest.mark.asyncio
    async def test_none_character_id_skipped(self, store, config, scenes):
        """character_id=None이면 캐릭터 추적을 스킵한다."""
        from services.agent.nodes.learn import learn_node

        state = {
            "topic": "테스트",
            "final_scenes": scenes,
            "structure": "Monologue",
            "character_id": None,
        }
        result = await learn_node(state, config, store=store)
        assert result["learn_result"]["stored"] is True

    @pytest.mark.asyncio
    async def test_error_state_skips_learn(self, store, config):
        """error 상태 → 학습 스킵."""
        from services.agent.nodes.learn import learn_node

        state = {"error": "이전 노드 에러", "final_scenes": [{"scene_id": 1}]}
        result = await learn_node(state, config, store=store)
        assert result["learn_result"]["stored"] is False
        assert result["learn_result"]["reason"] == "error"


# ═══════════════════════════════════════════════════════
# 5. routing 엣지 케이스
# ═══════════════════════════════════════════════════════


class TestRoutingEdgeCases:
    """routing 함수의 경계값·None 처리 시나리오."""

    def test_review_result_none_treated_as_failed(self):
        """review_result=None → passed=False → revise 경로."""
        from services.agent.routing import route_after_review

        state = {"review_result": None, "revision_count": 0, "skip_stages": []}
        assert route_after_review(state) == "revise"

    def test_review_result_missing_treated_as_failed(self):
        """review_result 키 자체 없음 → revise 경로."""
        from services.agent.routing import route_after_review

        state = {"revision_count": 0, "skip_stages": []}
        assert route_after_review(state) == "revise"

    def test_review_max_revisions_forces_through(self):
        """revision 한도 도달 + review 실패 → 강제 통과."""
        from services.agent.routing import route_after_review

        state = {
            "review_result": {"passed": False},
            "revision_count": 3,  # LANGGRAPH_MAX_REVISIONS=3
            "skip_stages": [],
        }
        assert route_after_review(state) == "director_checkpoint"

    def test_review_max_revisions_with_production_skip(self):
        """revision 한도 + production skip → finalize."""
        from services.agent.routing import route_after_review

        state = {
            "review_result": {"passed": False},
            "revision_count": 3,
            "skip_stages": ["production"],
        }
        assert route_after_review(state) == "finalize"

    def test_director_checkpoint_error_decision(self):
        """checkpoint decision=error → cinematographer (graceful proceed)."""
        from services.agent.routing import route_after_director_checkpoint

        state = {"director_checkpoint_decision": "error"}
        assert route_after_director_checkpoint(state) == "cinematographer"

    def test_director_checkpoint_max_revisions_forces_through(self):
        """checkpoint revision 한도 → cinematographer 강제 진행."""
        from services.agent.routing import route_after_director_checkpoint

        state = {
            "director_checkpoint_decision": "revise",
            "director_checkpoint_revision_count": 3,  # MAX=3
        }
        assert route_after_director_checkpoint(state) == "cinematographer"

    def test_director_unknown_decision_fallback(self):
        """director 미지정 decision → finalize 폴백."""
        from services.agent.routing import route_after_director

        state = {"director_decision": "unknown_action", "director_revision_count": 0}
        assert route_after_director(state) == "finalize"

    def test_director_hands_on_approve_goes_human_gate(self):
        """hands_on 모드 + approve → human_gate."""
        from services.agent.routing import route_after_director

        state = {
            "director_decision": "approve",
            "interaction_mode": "hands_on",
        }
        assert route_after_director(state) == "human_gate"

    def test_director_hands_on_error_goes_human_gate(self):
        """hands_on 모드 + error decision → human_gate."""
        from services.agent.routing import route_after_director

        state = {
            "director_decision": "error",
            "interaction_mode": "hands_on",
        }
        assert route_after_director(state) == "human_gate"

    def test_human_gate_default_approve(self):
        """human_action 미지정 → approve → finalize."""
        from services.agent.routing import route_after_human_gate

        assert route_after_human_gate({}) == "finalize"
        assert route_after_human_gate({"human_action": "approve"}) == "finalize"

    def test_human_gate_revise(self):
        """human_action=revise → revise."""
        from services.agent.routing import route_after_human_gate

        assert route_after_human_gate({"human_action": "revise"}) == "revise"

    def test_plan_gate_revise_routing(self):
        """plan_action=revise → director_plan."""
        from services.agent.routing import route_after_director_plan_gate

        assert route_after_director_plan_gate({"plan_action": "revise"}) == "director_plan"
        assert route_after_director_plan_gate({"plan_action": "proceed"}) == "inventory_resolve"
        assert route_after_director_plan_gate({}) == "inventory_resolve"

    def test_concept_gate_regenerate_routing(self):
        """concept_action=regenerate → critic."""
        from services.agent.routing import route_after_concept_gate

        assert route_after_concept_gate({"concept_action": "regenerate"}) == "critic"
        assert route_after_concept_gate({"concept_action": "select"}) == "writer"
        assert route_after_concept_gate({}) == "writer"
