"""Phase 12-A Agent 버그 수정 단위 테스트.

5가지 버그 수정 검증:
1. language 필드 누락 (tts_designer, sound_designer, copyright_reviewer)
2. _topic_key() 중복 제거 → utils.topic_key() 추출
3. search_similar_compositions await 누락 (AsyncSession 분기)
4. Copyright Reviewer overall 서버사이드 재계산
5. Learn character_b_id 저장 누락
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from langgraph.store.memory import InMemoryStore

from services.agent.nodes.copyright_reviewer import _recalculate_overall
from services.agent.utils import topic_key

# ── 1. topic_key() 유틸 테스트 ───────────────────────────────


class TestTopicKey:
    """topic_key()가 안정적인 12자리 MD5 해시를 반환하는지 검증한다."""

    def test_basic_hash(self):
        """문자열을 12자리 hex 해시로 변환한다."""
        result = topic_key("테스트 토픽")
        assert isinstance(result, str)
        assert len(result) == 12
        assert all(c in "0123456789abcdef" for c in result)

    def test_consistency(self):
        """동일 입력에 대해 항상 같은 해시를 반환한다."""
        a = topic_key("일관성 테스트")
        b = topic_key("일관성 테스트")
        assert a == b

    def test_different_inputs(self):
        """다른 입력에 대해 다른 해시를 반환한다."""
        a = topic_key("토픽A")
        b = topic_key("토픽B")
        assert a != b

    def test_empty_string(self):
        """빈 문자열도 유효한 12자리 해시를 반환한다."""
        result = topic_key("")
        assert isinstance(result, str)
        assert len(result) == 12


# ── 2. _recalculate_overall() 테스트 ────────────────────────


class TestRecalculateOverall:
    """checks 리스트 기반 overall 재계산 로직을 검증한다."""

    def test_all_pass(self):
        """모든 checks가 PASS이면 overall은 PASS."""
        checks = [
            {"type": "originality", "status": "PASS"},
            {"type": "trademark", "status": "PASS"},
            {"type": "likeness", "status": "PASS"},
        ]
        assert _recalculate_overall(checks) == "PASS"

    def test_any_fail(self):
        """하나라도 FAIL이면 overall은 FAIL."""
        checks = [
            {"type": "originality", "status": "PASS"},
            {"type": "trademark", "status": "FAIL"},
            {"type": "likeness", "status": "PASS"},
        ]
        assert _recalculate_overall(checks) == "FAIL"

    def test_fail_takes_precedence_over_warn(self):
        """FAIL과 WARN이 공존하면 FAIL이 우선한다."""
        checks = [
            {"type": "originality", "status": "WARN"},
            {"type": "trademark", "status": "FAIL"},
        ]
        assert _recalculate_overall(checks) == "FAIL"

    def test_any_warn_no_fail(self):
        """FAIL 없이 WARN이 있으면 overall은 WARN."""
        checks = [
            {"type": "originality", "status": "PASS"},
            {"type": "trademark", "status": "WARN"},
            {"type": "likeness", "status": "PASS"},
        ]
        assert _recalculate_overall(checks) == "WARN"

    def test_empty_checks(self):
        """빈 checks 리스트는 PASS로 간주한다."""
        assert _recalculate_overall([]) == "PASS"

    def test_missing_status_defaults_pass(self):
        """status 필드가 없는 check는 PASS로 취급한다."""
        checks = [{"type": "unknown"}]
        assert _recalculate_overall(checks) == "PASS"


# ── 3. language 필드 전달 테스트 (3개 노드) ──────────────────


class TestLanguagePassedToTemplateVars:
    """tts_designer, sound_designer, copyright_reviewer가 language를 template_vars에 전달하는지 검증한다."""

    @pytest.fixture
    def base_state(self):
        """공통 state fixture."""
        return {
            "cinematographer_result": {
                "scenes": [{"scene_id": 1, "script": "테스트 씬"}],
            },
            "critic_result": {"selected_concept": {"theme": "test"}},
            "language": "japanese",
            "duration": 30,
        }

    async def test_tts_designer_passes_language(self, base_state):
        """tts_designer_node가 language를 template_vars에 포함한다."""
        from services.agent.nodes.tts_designer import tts_designer_node

        captured_vars = {}

        async def mock_run_production_step(*, template_vars, **kwargs):
            captured_vars.update(template_vars)
            return {"tts_designs": []}

        with patch(
            "services.agent.nodes.tts_designer.run_production_step",
            side_effect=mock_run_production_step,
        ):
            await tts_designer_node(base_state)

        assert "language" in captured_vars
        assert captured_vars["language"] == "japanese"

    async def test_sound_designer_passes_language(self, base_state):
        """sound_designer_node가 language를 template_vars에 포함한다."""
        from services.agent.nodes.sound_designer import sound_designer_node

        captured_vars = {}

        async def mock_run_production_step(*, template_vars, **kwargs):
            captured_vars.update(template_vars)
            return {"recommendation": {"prompt": "", "mood": "neutral", "duration": 30}}

        with patch(
            "services.agent.nodes.sound_designer.run_production_step",
            side_effect=mock_run_production_step,
        ):
            await sound_designer_node(base_state)

        assert "language" in captured_vars
        assert captured_vars["language"] == "japanese"

    async def test_copyright_reviewer_passes_language(self, base_state):
        """copyright_reviewer_node가 language를 template_vars에 포함한다."""
        from services.agent.nodes.copyright_reviewer import copyright_reviewer_node

        captured_vars = {}

        async def mock_run_production_step(*, template_vars, **kwargs):
            captured_vars.update(template_vars)
            return {
                "overall": "PASS",
                "checks": [{"type": "test", "status": "PASS"}],
            }

        with patch(
            "services.agent.nodes.copyright_reviewer.run_production_step",
            side_effect=mock_run_production_step,
        ):
            await copyright_reviewer_node(base_state)

        assert "language" in captured_vars
        assert captured_vars["language"] == "japanese"

    async def test_language_defaults_to_korean(self):
        """language 미설정 시 기본값 'Korean'이 전달된다."""
        from services.agent.nodes.tts_designer import tts_designer_node

        state_without_language = {
            "cinematographer_result": {"scenes": []},
            "critic_result": {},
        }
        captured_vars = {}

        async def mock_run_production_step(*, template_vars, **kwargs):
            captured_vars.update(template_vars)
            return {"tts_designs": []}

        with patch(
            "services.agent.nodes.tts_designer.run_production_step",
            side_effect=mock_run_production_step,
        ):
            await tts_designer_node(state_without_language)

        assert captured_vars["language"] == "korean"


# ── 4. copyright_reviewer overall 서버사이드 재계산 테스트 ───


class TestCopyrightReviewerOverallRecalculation:
    """LLM이 반환한 overall을 무시하고 checks 기반으로 재계산하는지 검증한다."""

    async def test_llm_overall_overridden_by_recalculation(self):
        """LLM이 PASS라고 해도 checks에 FAIL이 있으면 FAIL로 재계산된다."""
        from services.agent.nodes.copyright_reviewer import copyright_reviewer_node

        state = {
            "cinematographer_result": {"scenes": [{"scene_id": 1}]},
            "language": "korean",
        }

        async def mock_run_production_step(**kwargs):
            # LLM이 overall을 PASS로 잘못 반환하는 상황 시뮬레이션
            return {
                "overall": "PASS",  # LLM이 잘못 판단
                "checks": [
                    {"type": "originality", "status": "PASS"},
                    {"type": "trademark", "status": "FAIL"},  # 실제로는 FAIL
                ],
            }

        with patch(
            "services.agent.nodes.copyright_reviewer.run_production_step",
            side_effect=mock_run_production_step,
        ):
            result = await copyright_reviewer_node(state)

        # 서버사이드 재계산으로 FAIL이 되어야 한다
        assert result["copyright_reviewer_result"]["overall"] == "FAIL"

    async def test_fallback_on_exception(self):
        """run_production_step 예외 시 fallback WARN을 반환한다."""
        from services.agent.nodes.copyright_reviewer import copyright_reviewer_node

        state = {
            "cinematographer_result": {"scenes": []},
            "language": "korean",
        }

        with patch(
            "services.agent.nodes.copyright_reviewer.run_production_step",
            side_effect=RuntimeError("Gemini API 오류"),
        ):
            result = await copyright_reviewer_node(state)

        assert result["copyright_reviewer_result"]["overall"] == "WARN"
        assert result["copyright_reviewer_result"]["checks"][0]["type"] == "api_fallback"


# ── 5. learn_node character_b_id 저장 테스트 ─────────────────


class TestLearnCharacterBId:
    """learn_node가 character_id와 character_b_id 모두 저장하는지 검증한다."""

    @pytest.fixture
    def store(self):
        return InMemoryStore()

    @pytest.fixture
    def config(self):
        return {"configurable": {"thread_id": "test-thread"}}

    @pytest.fixture
    def scenes(self):
        return [
            {"scene_id": 1, "script": "씬 1", "speaker": "speaker_1", "duration": 3},
            {"scene_id": 2, "script": "씬 2", "speaker": "speaker_2", "duration": 3},
        ]

    async def test_both_characters_stored(self, store, config, scenes):
        """character_id와 character_b_id 모두 저장된다."""
        from services.agent.nodes.learn import learn_node

        state = {
            "topic": "듀오 테스트",
            "final_scenes": scenes,
            "structure": "dialogue",
            "character_id": 10,
            "character_b_id": 20,
        }
        result = await learn_node(state, config, store=store)
        assert result["learn_result"]["stored"] is True

        # character_id=10 저장 확인
        char_a_items = await store.asearch(("character", "10"))
        assert len(char_a_items) == 1
        assert char_a_items[0].value["generation_count"] == 1

        # character_b_id=20 저장 확인
        char_b_items = await store.asearch(("character", "20"))
        assert len(char_b_items) == 1
        assert char_b_items[0].value["generation_count"] == 1

    async def test_character_b_id_none_skips(self, store, config, scenes):
        """character_b_id가 None이면 B 캐릭터는 저장하지 않는다."""
        from services.agent.nodes.learn import learn_node

        state = {
            "topic": "솔로 테스트",
            "final_scenes": scenes,
            "structure": "monologue",
            "character_id": 10,
            "character_b_id": None,
        }
        result = await learn_node(state, config, store=store)
        assert result["learn_result"]["stored"] is True

        # character_id=10만 저장
        char_a_items = await store.asearch(("character", "10"))
        assert len(char_a_items) == 1

        # character_b_id는 저장 안 됨 (None → 네임스페이스 자체가 없음)
        # InMemoryStore.asearch는 네임스페이스가 없으면 빈 리스트 반환
        char_b_items = await store.asearch(("character", "None"))
        assert len(char_b_items) == 0

    async def test_both_characters_increment(self, store, config, scenes):
        """2회 생성 시 양쪽 캐릭터 모두 generation_count가 2로 증가한다."""
        from services.agent.nodes.learn import learn_node

        state = {
            "topic": "듀오 반복",
            "final_scenes": scenes,
            "structure": "dialogue",
            "character_id": 10,
            "character_b_id": 20,
        }

        await learn_node(state, config, store=store)
        await learn_node(state, config, store=store)

        char_a_items = await store.asearch(("character", "10"))
        assert char_a_items[0].value["generation_count"] == 2

        char_b_items = await store.asearch(("character", "20"))
        assert char_b_items[0].value["generation_count"] == 2

    async def test_only_character_b_id(self, store, config, scenes):
        """character_id 없이 character_b_id만 있어도 저장된다."""
        from services.agent.nodes.learn import learn_node

        state = {
            "topic": "B만 테스트",
            "final_scenes": scenes,
            "structure": "monologue",
            "character_b_id": 99,
        }
        result = await learn_node(state, config, store=store)
        assert result["learn_result"]["stored"] is True

        char_b_items = await store.asearch(("character", "99"))
        assert len(char_b_items) == 1
        assert char_b_items[0].value["generation_count"] == 1
