"""파이프라인 플로우 검수에서 발견된 이슈별 테스트 시나리오.

각 이슈를 재현·방어하는 시나리오:
1. [MEDIUM] state["topic"] 직접 접근 KeyError (writer, revise)
2. [MEDIUM] interrupt() 반환값 비-dict 방어 (director_plan_gate, concept_gate)
3. [LOW] human_gate revision_count 리셋 후 무한 수정 가능성
4. [LOW] learn 노드 draft_character_id vs character_id 불일치
5. [INFO] routing 엣지 케이스 (review_result=None, 중첩 루프 카운터)
6. [Phase 28-A] 빈 씬 가드 + 라우팅 방어 + SSE falsy 체크
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
    @patch("services.agent.nodes.writer.generate_script", new_callable=AsyncMock)
    @patch("services.agent.nodes.writer.compile_prompt")
    async def test_writer_missing_topic_no_crash(self, mock_compile, mock_gen_script):
        """topic 누락 시 KeyError 없이 error 또는 draft_scenes 반환."""
        from services.agent.nodes.writer import writer_node

        mock_compile.return_value = MagicMock(system="sys", user="user", langfuse_prompt=None)
        mock_gen_script.return_value = {
            "scenes": [{"script": "test", "duration": 3.0, "speaker": "speaker_1", "image_prompt": "1girl"}],
            "character_id": None,
            "character_b_id": None,
        }

        state = {
            "description": "설명",
            "duration": 30,
            "language": "korean",
            "structure": "monologue",
        }
        result = await writer_node(state)
        assert "error" in result or "draft_scenes" in result

    @pytest.mark.asyncio
    @patch("services.agent.nodes.writer.generate_script", new_callable=AsyncMock)
    @patch("services.agent.nodes.writer.compile_prompt")
    async def test_writer_empty_topic_no_crash(self, mock_compile, mock_gen_script):
        """topic이 빈 문자열이면 crash 없이 진행."""
        from services.agent.nodes.writer import writer_node

        mock_compile.return_value = MagicMock(system="sys", user="user", langfuse_prompt=None)
        mock_gen_script.return_value = {
            "scenes": [{"script": "test", "duration": 3.0, "speaker": "speaker_1", "image_prompt": "1girl"}],
            "character_id": None,
            "character_b_id": None,
        }

        state = {
            "topic": "",
            "description": "",
            "duration": 30,
            "language": "korean",
            "structure": "monologue",
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
        """피드백이 revision_feedback 필드에 저장된다 (description 누적 없음)."""
        from services.agent.nodes.director_plan_gate import _handle_revise

        state = {"plan_revision_count": 0, "description": "원본"}
        result = _handle_revise(state, {"feedback": "더 감성적으로"})
        assert result["plan_action"] == "revise"
        assert result["revision_feedback"] == "더 감성적으로"
        assert "description" not in result  # description에 누적하지 않음
        assert result["plan_revision_count"] == 1

    def test_handle_revise_empty_feedback(self):
        """피드백이 비어있으면 revision_feedback은 빈 문자열."""
        from services.agent.nodes.director_plan_gate import _handle_revise

        state = {"plan_revision_count": 0, "description": "원본"}
        result = _handle_revise(state, {})
        assert result["revision_feedback"] == ""
        assert "description" not in result  # description 불변

    @pytest.mark.asyncio
    async def test_fast_track_mode_skips_interrupt(self):
        """fast_track 모드 → interrupt 없이 즉시 proceed."""
        from services.agent.nodes.director_plan_gate import director_plan_gate_node

        state = {"interaction_mode": "fast_track", "director_plan": {"goal": "test"}}
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
    async def test_fast_track_mode_skips_interrupt(self):
        """fast_track 모드 → interrupt 없이 즉시 select."""
        from services.agent.nodes.concept_gate import concept_gate_node

        state = {"interaction_mode": "fast_track", "critic_result": {"selected_concept": {"title": "A"}}}
        result = await concept_gate_node(state)
        assert result["concept_action"] == "select"


# ═══════════════════════════════════════════════════════
# 3. human_gate revision_count 리셋
# ═══════════════════════════════════════════════════════


class TestHumanGateRevisionReset:
    """human_gate에서 revision_count 리셋 시나리오."""

    @pytest.mark.asyncio
    async def test_any_mode_returns_halt_sentinel(self):
        """human_gate는 halt sentinel을 반환한다 (예기치 않은 도달 감지)."""
        from services.agent.nodes.human_gate import human_gate_node

        for mode in ["fast_track", "guided"]:
            state = {"interaction_mode": mode}
            result = await human_gate_node(state)
            assert result["human_action"] == "required"
            assert result["human_gate_reason"] == "checkpoint_fallback"

    @pytest.mark.asyncio
    async def test_returns_halt_sentinel_as_fallback(self):
        """human_gate는 halt sentinel 반환 (hands_on 폐기)."""
        from services.agent.nodes.human_gate import human_gate_node

        state = {"interaction_mode": "guided", "revision_count": 3}
        result = await human_gate_node(state)
        assert result["human_action"] == "required"
        assert result["human_gate_reason"] == "checkpoint_fallback"


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
        return [{"scene_id": 1, "script": "테스트", "speaker": "speaker_1", "duration": 3}]

    @pytest.mark.asyncio
    async def test_uses_character_id_not_draft(self, store, config, scenes):
        """learn은 character_id(원본)을 사용하고 draft_character_id는 무시한다."""
        from services.agent.nodes.learn import learn_node

        state = {
            "topic": "테스트",
            "final_scenes": scenes,
            "structure": "monologue",
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
            "structure": "dialogue",
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
            "structure": "monologue",
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
        assert route_after_review(state) == "location_planner"

    def test_review_max_revisions_always_director_checkpoint(self):
        """SP-057: revision 한도 → 항상 director_checkpoint (production skip 분기 제거)."""
        from services.agent.routing import route_after_review

        state = {
            "review_result": {"passed": False},
            "revision_count": 3,
            "skip_stages": ["production"],
        }
        assert route_after_review(state) == "location_planner"

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

    def test_director_fast_track_approve_goes_finalize(self):
        """fast_track 모드 + approve → finalize."""
        from services.agent.routing import route_after_director

        state = {
            "director_decision": "approve",
            "interaction_mode": "fast_track",
        }
        assert route_after_director(state) == "finalize"

    def test_director_error_goes_finalize(self):
        """error decision → finalize."""
        from services.agent.routing import route_after_director

        state = {
            "director_decision": "error",
            "interaction_mode": "guided",
        }
        assert route_after_director(state) == "finalize"

    def test_human_gate_default_approve(self):
        """human_action 미지정 → approve → finalize."""
        from services.agent.routing import route_after_human_gate

        assert route_after_human_gate({}) == "finalize"
        assert route_after_human_gate({"human_action": "approve"}) == "finalize"

    def test_human_gate_halt_sentinel_routes_to_finalize(self):
        """human_action=required (halt sentinel) → finalize."""
        from services.agent.routing import route_after_human_gate

        assert route_after_human_gate({"human_action": "required"}) == "finalize"

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


# ═══════════════════════════════════════════════════════
# 6. Phase 28-A: 빈 씬 가드 + 라우팅 방어
# ═══════════════════════════════════════════════════════


class TestRouteAfterWriterEmptyScenes:
    """Phase 28-A: route_after_writer 빈 씬 검사."""

    def test_empty_scenes_routes_to_finalize(self):
        """draft_scenes: [] → finalize short-circuit."""
        from services.agent.routing import route_after_writer

        state = {"draft_scenes": []}
        assert route_after_writer(state) == "finalize"

    def test_missing_scenes_routes_to_finalize(self):
        """draft_scenes 키 없음 → finalize short-circuit."""
        from services.agent.routing import route_after_writer

        assert route_after_writer({}) == "finalize"

    def test_none_scenes_routes_to_finalize(self):
        """draft_scenes: None → finalize short-circuit."""
        from services.agent.routing import route_after_writer

        state = {"draft_scenes": None}
        assert route_after_writer(state) == "finalize"

    def test_valid_scenes_routes_to_review(self):
        """정상 씬 → review 경로."""
        from services.agent.routing import route_after_writer

        state = {"draft_scenes": [{"script": "hello", "duration": 5}]}
        assert route_after_writer(state) == "review"

    def test_error_takes_precedence_over_empty_scenes(self):
        """error + 빈 씬 → error가 우선 (finalize)."""
        from services.agent.routing import route_after_writer

        state = {"error": "some error", "draft_scenes": []}
        assert route_after_writer(state) == "finalize"


class TestWriterEmptySceneRetry:
    """Phase 28-A: writer_node 빈 씬 재시도 로직."""

    @pytest.mark.asyncio
    @patch("services.agent.nodes.writer.get_llm_provider")
    @patch("services.agent.nodes.writer.get_db_session")
    @patch("services.agent.nodes.writer.generate_script")
    async def test_empty_scenes_triggers_retry(self, mock_gen, mock_db, mock_llm_provider):
        """빈 씬 반환 → 힌트 추가 1회 재시도."""
        from services.agent.nodes.writer import writer_node

        mock_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=RuntimeError("planning skip"))
        mock_llm_provider.return_value = mock_provider

        # 1차: 빈 씬, 2차: 정상
        mock_gen.side_effect = [
            {"scenes": [], "character_id": 1},
            {"scenes": [{"script": "retry ok", "duration": 5}], "character_id": 1},
        ]

        state = {"topic": "test", "duration": 10}
        result = await writer_node(state)

        assert "error" not in result
        assert len(result["draft_scenes"]) == 1
        assert mock_gen.call_count == 2

    @pytest.mark.asyncio
    @patch("services.agent.nodes.writer.get_llm_provider")
    @patch("services.agent.nodes.writer.get_db_session")
    @patch("services.agent.nodes.writer.generate_script")
    async def test_both_attempts_empty_returns_error(self, mock_gen, mock_db, mock_llm_provider):
        """2회 모두 빈 씬 → error 반환."""
        from services.agent.nodes.writer import writer_node

        mock_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=RuntimeError("planning skip"))
        mock_llm_provider.return_value = mock_provider

        mock_gen.return_value = {"scenes": [], "character_id": 1}

        state = {"topic": "test", "duration": 10}
        result = await writer_node(state)

        assert "error" in result
        assert "빈 스크립트" in result["error"]

    @pytest.mark.asyncio
    @patch("services.agent.nodes.writer.get_llm_provider")
    @patch("services.agent.nodes.writer.get_db_session")
    @patch("services.agent.nodes.writer.generate_script")
    async def test_all_empty_scripts_treated_as_empty(self, mock_gen, mock_db, mock_llm_provider):
        """모든 씬의 script가 빈 문자열 → 빈 씬 취급."""
        from services.agent.nodes.writer import writer_node

        mock_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=RuntimeError("planning skip"))
        mock_llm_provider.return_value = mock_provider

        mock_gen.return_value = {
            "scenes": [{"script": "", "duration": 5}, {"script": "   ", "duration": 5}],
            "character_id": 1,
        }

        state = {"topic": "test", "duration": 10}
        result = await writer_node(state)

        assert "error" in result

    @pytest.mark.asyncio
    @patch("services.agent.nodes.writer.get_llm_provider")
    @patch("services.agent.nodes.writer.get_db_session")
    @patch("services.agent.nodes.writer.generate_script")
    async def test_retry_exception_returns_error(self, mock_gen, mock_db, mock_llm_provider):
        """재시도 중 예외 → error 반환."""
        from services.agent.nodes.writer import writer_node

        mock_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=RuntimeError("planning skip"))
        mock_llm_provider.return_value = mock_provider

        mock_gen.side_effect = [
            {"scenes": [], "character_id": 1},
            Exception("Gemini timeout"),
        ]

        state = {"topic": "test", "duration": 10}
        result = await writer_node(state)

        assert "error" in result
        assert "재시도 실패" in result["error"]


class TestCinematographerNullGuard:
    """Phase 28-A: cinematographer characters_tags None → {} 폴백."""

    def test_load_characters_tags_returns_empty_dict_on_no_character(self):
        """character_id 없으면 _load_characters_tags → None, 호출부에서 {} 폴백."""
        from services.agent.nodes.cinematographer import _load_characters_tags

        state = {}
        result = _load_characters_tags(state, MagicMock())
        # 함수 자체는 None 반환, 호출부에서 `or {}` 적용
        assert result is None


# ═══════════════════════════════════════════════════════
# 7. Phase 28-B: Error Recovery + 글로벌 리비전 상한
# ═══════════════════════════════════════════════════════


class TestCopyrightReviewerFallbackWarn:
    """Phase 28-B #8: copyright_reviewer API 실패 시 WARN 반환."""

    @pytest.mark.asyncio
    @patch("services.agent.nodes.copyright_reviewer.run_production_step")
    async def test_fallback_returns_warn_not_pass(self, mock_run):
        """API 실패 시 fallback은 WARN + fallback_reason."""
        from services.agent.nodes.copyright_reviewer import copyright_reviewer_node

        mock_run.side_effect = Exception("API timeout")
        state = {"cinematographer_result": {"scenes": [{"order": 1}]}}
        result = await copyright_reviewer_node(state)

        cr = result["copyright_reviewer_result"]
        assert cr["overall"] == "WARN"
        assert cr["fallback_reason"] == "api_error"
        assert cr["confidence"] == 0.0


class TestDirectorUnknownDecisionLogging:
    """Phase 28-B #9: 미등록 decision 경고 로깅."""

    def test_unknown_decision_logs_warning_and_returns_finalize(self):
        """미등록 decision → 경고 로그 + finalize fallback."""
        from services.agent.routing import route_after_director

        state = {"director_decision": "invalid_action", "director_revision_count": 0}
        with patch("services.agent.routing.logger") as mock_logger:
            result = route_after_director(state)
            assert result == "finalize"
            warning_msgs = [str(c) for c in mock_logger.warning.call_args_list]
            assert any("미등록 decision" in m for m in warning_msgs)


class TestTotalRevisionsFunction:
    """Phase 28-B #10: _total_revisions 파생 계산 함수."""

    def test_sums_all_revision_counters(self):
        """3개 카운터 합산."""
        from services.agent.routing import _total_revisions

        state = {
            "revision_count": 2,
            "director_checkpoint_revision_count": 3,
            "director_revision_count": 1,
        }
        assert _total_revisions(state) == 6

    def test_defaults_to_zero_for_missing_counters(self):
        """카운터 없으면 0."""
        from services.agent.routing import _total_revisions

        assert _total_revisions({}) == 0

    def test_partial_counters(self):
        """일부 카운터만 있을 때."""
        from services.agent.routing import _total_revisions

        assert _total_revisions({"revision_count": 5}) == 5


class TestGlobalRevisionCap:
    """Phase 28-B #10: 글로벌 리비전 상한 (10회)."""

    def test_review_global_cap_forces_through(self):
        """review: 글로벌 상한 도달 → revise 대신 강제 통과."""
        from services.agent.routing import route_after_review

        state = {
            "review_result": {"passed": False},
            "revision_count": 2,
            "director_checkpoint_revision_count": 5,
            "director_revision_count": 3,  # total=10
        }
        result = route_after_review(state)
        # 강제 통과 → director_checkpoint 또는 finalize
        assert result != "revise"

    def test_director_global_cap_forces_finalize(self):
        """director: 글로벌 상한 도달 → finalize."""
        from services.agent.routing import route_after_director

        state = {
            "director_decision": "revise_script",
            "revision_count": 3,
            "director_checkpoint_revision_count": 3,
            "director_revision_count": 4,  # total=10
        }
        assert route_after_director(state) == "finalize"

    def test_checkpoint_global_cap_forces_cinematographer(self):
        """checkpoint: 글로벌 상한 도달 → cinematographer 강제."""
        from services.agent.routing import route_after_director_checkpoint

        state = {
            "director_checkpoint_decision": "revise",
            "revision_count": 3,
            "director_checkpoint_revision_count": 4,
            "director_revision_count": 3,  # total=10
        }
        assert route_after_director_checkpoint(state) == "cinematographer"

    def test_below_cap_allows_revise(self):
        """글로벌 상한 미만 → 정상 revise 허용."""
        from services.agent.routing import route_after_review

        state = {
            "review_result": {"passed": False},
            "revision_count": 1,
            "director_checkpoint_revision_count": 1,
            "director_revision_count": 1,  # total=3
        }
        assert route_after_review(state) == "revise"


class TestFinalizeEmptyGroupWarning:
    """Phase 28-A: finalize 빈 그룹 경고 로깅."""

    def test_empty_group_returns_none_with_logging(self):
        """빈 그룹 → (None, None) + 경고 로그."""
        from services.agent.nodes.finalize import _resolve_characters_from_group

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        with patch("services.agent.nodes.finalize.logger") as mock_logger:
            result = _resolve_characters_from_group(6, "monologue", mock_db)
            assert result == (None, None)
            mock_logger.warning.assert_called_once()
            assert "Group 6" in mock_logger.warning.call_args[0][0] % mock_logger.warning.call_args[0][1:]


# ═══════════════════════════════════════════════════════
# 8. Phase 28-C: Observability — fallback_reason 표준화 + SSE 키 확장
# ═══════════════════════════════════════════════════════


class TestProductionFallbackReason:
    """Phase 28-C #11: 3개 Production 노드 모두 fallback_reason 포함."""

    @pytest.mark.asyncio
    @patch("services.agent.nodes.tts_designer.run_production_step")
    async def test_tts_fallback_has_reason(self, mock_run):
        """TTS Designer 실패 → fallback_reason 포함."""
        from services.agent.nodes.tts_designer import tts_designer_node

        mock_run.side_effect = Exception("timeout")
        state = {"cinematographer_result": {"scenes": []}}
        result = await tts_designer_node(state)

        tts = result["tts_designer_result"]
        assert tts["fallback_reason"] == "api_error"
        assert tts["tts_designs"] == []

    @pytest.mark.asyncio
    @patch("services.agent.nodes.sound_designer.run_production_step")
    async def test_sound_fallback_has_reason(self, mock_run):
        """Sound Designer 실패 → fallback_reason 포함."""
        from services.agent.nodes.sound_designer import sound_designer_node

        mock_run.side_effect = Exception("timeout")
        state = {"cinematographer_result": {"scenes": []}}
        result = await sound_designer_node(state)

        sound = result["sound_designer_result"]
        assert sound["fallback_reason"] == "api_error"
        assert sound["recommendation"]["mood"] == "neutral"

    @pytest.mark.asyncio
    @patch("services.agent.nodes.copyright_reviewer.run_production_step")
    async def test_copyright_fallback_has_reason(self, mock_run):
        """Copyright Reviewer 실패 → fallback_reason 포함 (Phase B 검증 재확인)."""
        from services.agent.nodes.copyright_reviewer import copyright_reviewer_node

        mock_run.side_effect = Exception("timeout")
        state = {"cinematographer_result": {"scenes": []}}
        result = await copyright_reviewer_node(state)

        cr = result["copyright_reviewer_result"]
        assert cr["fallback_reason"] == "api_error"
        assert cr["overall"] == "WARN"


# ═══════════════════════════════════════════════════════
# 9. Phase 28-D: Data Integrity — 원본 보존 + 음수 score 방어
# ═══════════════════════════════════════════════════════


class TestExtractReasoningCopyPreservation:
    """Phase 28-D #14: _extract_reasoning이 원본 씬 dict를 변경하지 않는다."""

    def test_original_scene_dicts_not_mutated(self):
        """원본 씬 dict에 reasoning이 보존되는지 확인."""
        from services.agent.nodes.writer import _extract_reasoning

        scene_a = {"script": "안녕하세요", "reasoning": {"intent": "인사"}}
        scene_b = {"script": "반갑습니다"}
        original_a = scene_a.copy()  # 원본 참조 보존

        scenes = [scene_a, scene_b]
        reasoning = _extract_reasoning(scenes)

        # 원본 dict는 변경되지 않아야 한다
        assert "reasoning" in original_a
        assert original_a["reasoning"] == {"intent": "인사"}

        # 추출된 reasoning은 정확해야 한다
        assert reasoning == [{"intent": "인사"}, {}]

        # scenes 리스트의 요소에는 reasoning이 제거되어 있어야 한다
        assert "reasoning" not in scenes[0]
        assert "reasoning" not in scenes[1]

    def test_scenes_list_updated_in_place(self):
        """scenes 리스트가 in-place로 교체되어 downstream에 reasoning 없이 전달."""
        from services.agent.nodes.writer import _extract_reasoning

        scenes = [
            {"script": "A", "reasoning": {"r": 1}},
            {"script": "B", "reasoning": {"r": 2}},
        ]
        reasoning = _extract_reasoning(scenes)

        assert len(scenes) == 2
        assert all("reasoning" not in s for s in scenes)
        assert reasoning == [{"r": 1}, {"r": 2}]

    def test_non_dict_reasoning_treated_as_empty(self):
        """reasoning이 dict가 아니면 빈 dict로 처리."""
        from services.agent.nodes.writer import _extract_reasoning

        scenes = [
            {"script": "A", "reasoning": "string_value"},
            {"script": "B", "reasoning": 42},
            {"script": "C"},
        ]
        reasoning = _extract_reasoning(scenes)

        assert reasoning == [{}, {}, {}]


class TestCheckpointNegativeScore:
    """Phase 28-D #15: director_checkpoint_score 음수 → error 취급."""

    def test_negative_score_returns_error(self):
        """음수 score → decision=error로 오버라이드."""
        from services.agent.nodes.director_checkpoint import _apply_score_override

        decision, feedback = _apply_score_override("proceed", -1.0, "")
        assert decision == "error"
        assert "음수" in feedback or "오류" in feedback

    def test_negative_score_overrides_revise_too(self):
        """revise decision이어도 음수 score면 error로 변경."""
        from services.agent.nodes.director_checkpoint import _apply_score_override

        decision, _feedback = _apply_score_override("revise", -0.5, "기존 피드백")
        assert decision == "error"

    def test_zero_score_not_treated_as_error(self):
        """0점은 음수가 아니므로 error로 취급하지 않는다."""
        from services.agent.nodes.director_checkpoint import _apply_score_override

        decision, _feedback = _apply_score_override("proceed", 0.0, "")
        # 0.0 < LOW_THRESHOLD(0.4) → revise 오버라이드 (기존 로직)
        assert decision == "revise"

    def test_routing_negative_score_to_cinematographer(self):
        """routing: error decision → cinematographer로 graceful proceed."""
        from services.agent.routing import route_after_director_checkpoint

        state = {
            "director_checkpoint_decision": "error",
            "director_checkpoint_score": -1.0,
        }
        assert route_after_director_checkpoint(state) == "cinematographer"


class TestDirectorPlanGateFallback:
    """Phase 28-D #16: director_plan_gate의 None → {} 폴백 확인."""

    @pytest.mark.asyncio
    async def test_none_director_plan_no_error_in_fast_track_mode(self):
        """director_plan=None + fast_track 모드 → 에러 없이 proceed."""
        from services.agent.nodes.director_plan_gate import director_plan_gate_node

        state = {"interaction_mode": "fast_track", "director_plan": None}
        result = await director_plan_gate_node(state)
        assert result["plan_action"] == "proceed"


# ═══════════════════════════════════════════════════════
# 10. Phase 28 추가 시나리오: 누락 커버리지 보강
# ═══════════════════════════════════════════════════════


class TestTopicAnalysisFallback:
    """analyze_topic: Gemini 미설정 시 기본값 반환."""

    @pytest.mark.asyncio
    @patch("config.gemini_client", None)
    async def test_no_gemini_returns_fallback(self):
        """Gemini 클라이언트 없으면 기본값(duration=30, Korean, Monologue) 반환."""
        from services.scripts.topic_analysis import analyze_topic

        result = await analyze_topic("테스트 주제", None, group_id=99)

        assert result.duration == 30
        assert result.language == "korean"
        assert result.structure == "monologue"
        assert result.available_options is not None
        assert result.available_options.durations


class TestWriterSafetyRetryThenEmptyScenes:
    """시나리오 7: Safety 재시도 성공 후에도 빈 씬 → 빈 씬 가드 동작."""

    @pytest.mark.asyncio
    @patch("services.agent.nodes.writer.get_llm_provider")
    @patch("services.agent.nodes.writer.get_db_session")
    @patch("services.agent.nodes.writer.generate_script")
    async def test_safety_retry_then_empty_triggers_guard(self, mock_gen, mock_db, mock_llm_provider):
        """Safety 에러 → 재시도 성공 → 빈 씬 → 빈 씬 가드 재시도 → 복구."""
        from services.agent.nodes.writer import writer_node

        mock_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=RuntimeError("planning skip"))
        mock_llm_provider.return_value = mock_provider

        # 1차: Safety 에러, 2차: Safety 통과 but 빈 씬, 3차: 빈 씬 가드 재시도 성공
        mock_gen.side_effect = [
            Exception("SAFETY filter blocked"),
            {"scenes": [], "character_id": 1},
            {"scenes": [{"script": "복구됨", "duration": 5}], "character_id": 1},
        ]

        state = {"topic": "test", "duration": 10}
        result = await writer_node(state)

        assert "error" not in result
        assert len(result["draft_scenes"]) == 1
        assert mock_gen.call_count == 3

    @pytest.mark.asyncio
    @patch("services.agent.nodes.writer.get_llm_provider")
    @patch("services.agent.nodes.writer.get_db_session")
    @patch("services.agent.nodes.writer.generate_script")
    async def test_safety_retry_then_empty_all_fail(self, mock_gen, mock_db, mock_llm_provider):
        """Safety 에러 → 재시도 성공 → 빈 씬 → 빈 씬 재시도도 빈 씬 → error."""
        from services.agent.nodes.writer import writer_node

        mock_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=RuntimeError("planning skip"))
        mock_llm_provider.return_value = mock_provider

        mock_gen.side_effect = [
            Exception("SAFETY filter blocked"),
            {"scenes": [], "character_id": 1},
            {"scenes": [], "character_id": 1},
        ]

        state = {"topic": "test", "duration": 10}
        result = await writer_node(state)

        assert "error" in result
        assert "빈 스크립트" in result["error"]


class TestCheckpointLoopEmptyScenes:
    """시나리오 8: Checkpoint → Writer 재실행 후 빈 씬 → 가드 동작.

    라우팅 레벨 빈 씬 검사는 TestRouteAfterWriterEmptyScenes에서 커버.
    이 클래스는 checkpoint 루프 맥락에서 writer_node 자체의 빈 씬 가드를 검증.
    """

    @pytest.mark.asyncio
    @patch("services.agent.nodes.writer.get_llm_provider")
    @patch("services.agent.nodes.writer.get_db_session")
    @patch("services.agent.nodes.writer.generate_script")
    async def test_writer_in_checkpoint_loop_empty_returns_error(self, mock_gen, mock_db, mock_llm_provider):
        """Checkpoint 루프 내 writer → 빈 씬 2회 → error."""
        from services.agent.nodes.writer import writer_node

        mock_db.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=RuntimeError("planning skip"))
        mock_llm_provider.return_value = mock_provider
        mock_gen.return_value = {"scenes": [], "character_id": 1}

        state = {
            "topic": "test",
            "duration": 10,
            "director_checkpoint_revision_count": 1,
            "director_checkpoint_feedback": "더 몰입감 있게",
        }
        result = await writer_node(state)

        assert "error" in result
        assert "빈 스크립트" in result["error"]


class TestMultipleProductionSimultaneousFailure:
    """시나리오 9: Production 2개 이상 동시 실패 → 각각 fallback_reason."""

    @pytest.mark.asyncio
    @patch("services.agent.nodes.copyright_reviewer.run_production_step")
    @patch("services.agent.nodes.sound_designer.run_production_step")
    @patch("services.agent.nodes.tts_designer.run_production_step")
    async def test_all_three_production_fail_combined_state(self, mock_tts_run, mock_sound_run, mock_cr_run):
        """3개 동시 실패 시 state 전체 구조의 fallback_reason 일관성 검증."""
        from services.agent.nodes.copyright_reviewer import copyright_reviewer_node
        from services.agent.nodes.sound_designer import sound_designer_node
        from services.agent.nodes.tts_designer import tts_designer_node

        mock_tts_run.side_effect = Exception("TTS API timeout")
        mock_sound_run.side_effect = Exception("Sound API timeout")
        mock_cr_run.side_effect = Exception("Copyright API timeout")

        state = {"cinematographer_result": {"scenes": [{"order": 1}]}}

        tts_result = await tts_designer_node(state)
        sound_result = await sound_designer_node(state)
        cr_result = await copyright_reviewer_node(state)

        assert tts_result["tts_designer_result"]["fallback_reason"] == "api_error"
        assert sound_result["sound_designer_result"]["fallback_reason"] == "api_error"
        assert cr_result["copyright_reviewer_result"]["fallback_reason"] == "api_error"

    def test_director_routing_with_multiple_fallbacks(self):
        """Director가 복수 fallback 결과 state에서 정상 라우팅."""
        from services.agent.routing import route_after_director

        state = {
            "director_decision": "approve",
            "tts_designer_result": {"tts_designs": [], "fallback_reason": "api_error"},
            "sound_designer_result": {
                "recommendation": {"prompt": "", "mood": "neutral", "duration": 30},
                "fallback_reason": "api_error",
            },
            "copyright_reviewer_result": {
                "overall": "WARN",
                "fallback_reason": "api_error",
            },
        }
        assert route_after_director(state) == "finalize"

    def test_director_routing_with_mixed_results(self):
        """정상 + fallback 혼합 state에서 Director 라우팅 정상."""
        from services.agent.routing import route_after_director

        state = {
            "director_decision": "approve",
            "tts_designer_result": {"tts_designs": [{"voice": "alloy"}]},
            "sound_designer_result": {
                "recommendation": {"prompt": "", "mood": "neutral", "duration": 30},
                "fallback_reason": "api_error",
            },
        }
        assert route_after_director(state) == "finalize"
