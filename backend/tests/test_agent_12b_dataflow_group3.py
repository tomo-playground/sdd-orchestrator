"""Phase 12-B Group C 단위 테스트 (12-B-4, 12-B-7, 12-B-8, 12-B-9, 12-B-10).

검증 항목:
1. 12-B-8: Review narrative_weights 재배분 (script_image_sync 0.15)
2. 12-B-9: Finalize 메타데이터 구조 분리 (sound/copyright top-level)
3. 12-B-4: Learn 저장 데이터 확충 (quality_score, narrative_score, hook_strategy 등)
4. 12-B-10: Human Gate interrupt payload 확장 (Director 판단 근거)
5. 12-B-7: Revise placeholder 동적 생성 (gender/style 반영)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from langgraph.store.memory import InMemoryStore

# ── 12-B-8: Review narrative_weights 재배분 ─────────────────


class TestNarrativeWeightsRebalanced:
    """_NARRATIVE_WEIGHTS 가중치가 재배분되었는지 검증한다."""

    def test_weights_sum_to_one(self):
        """가중치 합이 정확히 1.0이어야 한다."""
        from services.agent.nodes.review import _NARRATIVE_WEIGHTS

        total = sum(_NARRATIVE_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9, f"가중치 합: {total}"

    def test_script_image_sync_weight(self):
        """script_image_sync 가중치가 0.10으로 조정되었다."""
        from services.agent.nodes.review import _NARRATIVE_WEIGHTS

        assert _NARRATIVE_WEIGHTS["script_image_sync"] == 0.10

    def test_hook_weight(self):
        """hook 가중치가 0.25이다."""
        from services.agent.nodes.review import _NARRATIVE_WEIGHTS

        assert _NARRATIVE_WEIGHTS["hook"] == 0.25

    def test_twist_payoff_weight(self):
        """twist_payoff 가중치가 0.10이다."""
        from services.agent.nodes.review import _NARRATIVE_WEIGHTS

        assert _NARRATIVE_WEIGHTS["twist_payoff"] == 0.10

    def test_emotional_arc_weight(self):
        """emotional_arc 가중치가 0.15이다."""
        from services.agent.nodes.review import _NARRATIVE_WEIGHTS

        assert _NARRATIVE_WEIGHTS["emotional_arc"] == 0.15

    def test_speaker_tone_weight(self):
        """speaker_tone 가중치가 0.05이다."""
        from services.agent.nodes.review import _NARRATIVE_WEIGHTS

        assert _NARRATIVE_WEIGHTS["speaker_tone"] == 0.05

    def test_new_dimensions_exist(self):
        """Phase 36에서 추가된 3개 차원이 존재한다."""
        from services.agent.nodes.review import _NARRATIVE_WEIGHTS

        assert _NARRATIVE_WEIGHTS["spoken_naturalness"] == 0.15
        assert _NARRATIVE_WEIGHTS["retention_flow"] == 0.10
        assert _NARRATIVE_WEIGHTS["pacing_rhythm"] == 0.10


# ── 12-B-9: Finalize 메타데이터 구조 분리 ───────────────────


class TestFinalizeMetadataSeparation:
    """Finalize가 sound/copyright를 top-level로 반환하는지 검증한다."""

    async def test_full_mode_returns_top_level_metadata(self):
        """Full 모드에서 sound_recommendation/copyright_result가 top-level에 존재한다."""
        from services.agent.nodes.finalize import finalize_node

        state = {
            "skip_stages": [],
            "cinematographer_result": {
                "scenes": [{"scene_id": 1, "script": "테스트"}],
            },
            "tts_designer_result": {"tts_designs": [{"voice": "narrator"}]},
            "sound_designer_result": {"recommendation": {"mood": "calm", "bpm": 80}},
            "copyright_reviewer_result": {"overall": "PASS", "checks": []},
        }
        result = await finalize_node(state, {})

        assert "sound_recommendation" in result
        assert result["sound_recommendation"] == {"mood": "calm", "bpm": 80}
        assert "copyright_result" in result
        assert result["copyright_result"]["overall"] == "PASS"

    async def test_full_mode_scenes_no_embedded_metadata(self):
        """Full 모드에서 scenes[0]에 _sound_recommendation/_copyright_result가 없다."""
        from services.agent.nodes.finalize import finalize_node

        state = {
            "skip_stages": [],
            "cinematographer_result": {
                "scenes": [{"scene_id": 1, "script": "테스트"}],
            },
            "tts_designer_result": {"tts_designs": []},
            "sound_designer_result": {"recommendation": {"mood": "epic"}},
            "copyright_reviewer_result": {"overall": "WARN"},
        }
        result = await finalize_node(state, {})

        scenes = result["final_scenes"]
        assert len(scenes) > 0
        assert "_sound_recommendation" not in scenes[0]
        assert "_copyright_result" not in scenes[0]

    async def test_quick_mode_returns_fallback_sound(self):
        """Quick 모드에서 BGM fallback이 적용된다."""
        from services.agent.nodes.finalize import finalize_node

        state = {
            "skip_stages": ["research", "concept", "production", "explain"],
            "draft_scenes": [{"scene_id": 1, "script": "퀵"}],
        }
        result = await finalize_node(state, {})

        # BGM fallback: sound_designer 미실행 시 기본 추천 생성
        assert result["sound_recommendation"] is not None
        assert "prompt" in result["sound_recommendation"]
        assert result["copyright_result"] is None

    async def test_full_mode_without_sound_result_uses_fallback(self):
        """sound_designer_result가 없을 때 BGM fallback이 적용된다."""
        from services.agent.nodes.finalize import finalize_node

        state = {
            "skip_stages": [],
            "cinematographer_result": {
                "scenes": [{"scene_id": 1}],
            },
            "tts_designer_result": {"tts_designs": []},
        }
        result = await finalize_node(state, {})

        # BGM fallback: sound_designer 미실행 시 기본 추천 생성
        assert result["sound_recommendation"] is not None
        assert "prompt" in result["sound_recommendation"]
        assert result["copyright_result"] is None


# ── 12-B-4: Learn 저장 데이터 확충 ──────────────────────────


class TestLearnExtractHelpers:
    """Learn 헬퍼 함수들이 올바르게 데이터를 추출하는지 검증한다."""

    def test_extract_quality_score_present(self):
        """state에 director_checkpoint_score가 있으면 반환한다."""
        from services.agent.nodes.learn import _extract_quality_score

        state = {"director_checkpoint_score": 0.85}
        assert _extract_quality_score(state) == 0.85

    def test_extract_quality_score_missing(self):
        """state에 director_checkpoint_score가 없으면 None 반환."""
        from services.agent.nodes.learn import _extract_quality_score

        assert _extract_quality_score({}) is None

    def test_extract_narrative_score_present(self):
        """review_result에 narrative_score.overall이 있으면 반환한다."""
        from services.agent.nodes.learn import _extract_narrative_score

        state = {"review_result": {"narrative_score": {"overall": 0.72}}}
        assert _extract_narrative_score(state) == 0.72

    def test_extract_narrative_score_missing_review(self):
        """review_result가 없으면 None 반환."""
        from services.agent.nodes.learn import _extract_narrative_score

        assert _extract_narrative_score({}) is None

    def test_extract_narrative_score_no_ns(self):
        """review_result에 narrative_score가 없으면 None 반환."""
        from services.agent.nodes.learn import _extract_narrative_score

        state = {"review_result": {"passed": True}}
        assert _extract_narrative_score(state) is None

    def test_extract_hook_strategy_present(self):
        """writer_plan에 hook_strategy가 있으면 반환한다."""
        from services.agent.nodes.learn import _extract_hook_strategy

        state = {"writer_plan": {"hook_strategy": "질문으로 시작"}}
        assert _extract_hook_strategy(state) == "질문으로 시작"

    def test_extract_hook_strategy_missing(self):
        """writer_plan이 없으면 None 반환."""
        from services.agent.nodes.learn import _extract_hook_strategy

        assert _extract_hook_strategy({}) is None


class TestLearnEnrichedEntry:
    """learn_node가 확충된 entry를 저장하는지 통합 검증한다."""

    @pytest.fixture
    def store(self):
        return InMemoryStore()

    @pytest.fixture
    def config(self):
        return {"configurable": {"thread_id": "test-thread"}}

    async def test_enriched_entry_stored(self, store, config):
        """풍부한 state에서 모든 추가 필드가 entry에 저장된다."""
        from services.agent.nodes.learn import learn_node

        state = {
            "topic": "풍부한 테스트",
            "final_scenes": [
                {"scene_id": 1, "script": "첫 씬", "duration": 3},
            ],
            "structure": "monologue",
            "skip_stages": [],
            "revision_count": 2,
            "director_checkpoint_score": 0.9,
            "review_result": {"narrative_score": {"overall": 0.75}},
            "writer_plan": {"hook_strategy": "통계로 시작"},
        }

        result = await learn_node(state, config, store=store)
        assert result["learn_result"]["stored"] is True

        # 저장된 entry 조회
        from services.agent.utils import topic_key

        topic_ns = ("topic", topic_key("풍부한 테스트"))
        items = await store.asearch(topic_ns, limit=1)
        assert len(items) == 1

        entry = items[0].value
        assert entry["quality_score"] == 0.9
        assert entry["narrative_score"] == 0.75
        assert entry["hook_strategy"] == "통계로 시작"
        assert entry["revision_count"] == 2
        assert entry["skip_stages"] == []
        assert entry["scene_count"] == 1
        assert "created_at" in entry

    async def test_minimal_state_stores_nones(self, store, config):
        """최소 state에서 추가 필드는 None/기본값으로 저장된다."""
        from services.agent.nodes.learn import learn_node

        state = {
            "topic": "최소 테스트",
            "final_scenes": [{"scene_id": 1, "script": "씬"}],
        }
        await learn_node(state, config, store=store)

        from services.agent.utils import topic_key

        topic_ns = ("topic", topic_key("최소 테스트"))
        items = await store.asearch(topic_ns, limit=1)
        entry = items[0].value

        assert entry["quality_score"] is None
        assert entry["narrative_score"] is None
        assert entry["hook_strategy"] is None
        assert entry["revision_count"] == 0
        assert entry["skip_stages"] == []


# ── 12-B-10: Human Gate interrupt payload 확장 ──────────────


class TestHumanGatePayloadExtended:
    """interrupt payload에 Director 판단 근거가 포함되는지 검증한다."""

    async def test_interrupt_payload_contains_director_fields(self):
        """interrupt payload에 6개 필드가 존재한다 (hands_on 모드)."""
        from services.agent.nodes.human_gate import human_gate_node

        state = {
            "interaction_mode": "hands_on",
            "draft_scenes": [{"scene_id": 1}],
            "review_result": {"passed": True},
            "scene_reasoning": [{"why": "hook"}],
            "director_decision": "proceed",
            "director_feedback": "좋은 구성입니다",
            "director_reasoning_steps": [{"step": 1, "observe": "ok", "think": "good", "act": "proceed"}],
        }

        captured_payload = {}

        def mock_interrupt(payload):
            captured_payload.update(payload)
            return {"action": "approve"}

        with patch("services.agent.nodes.human_gate.interrupt", side_effect=mock_interrupt):
            await human_gate_node(state)

        assert captured_payload["type"] == "review_approval"
        assert captured_payload["scenes"] == [{"scene_id": 1}]
        assert captured_payload["review_result"]["passed"] is True
        assert captured_payload["scene_reasoning"] == [{"why": "hook"}]
        assert captured_payload["director_decision"] == "proceed"
        assert captured_payload["director_feedback"] == "좋은 구성입니다"
        assert len(captured_payload["director_reasoning_steps"]) == 1

    async def test_interrupt_payload_none_fields(self):
        """Director 필드가 없는 state에서도 None으로 포함된다 (hands_on 모드)."""
        from services.agent.nodes.human_gate import human_gate_node

        state = {
            "interaction_mode": "hands_on",
            "draft_scenes": [{"scene_id": 1}],
            "review_result": {"passed": True},
        }

        captured_payload = {}

        def mock_interrupt(payload):
            captured_payload.update(payload)
            return {"action": "approve"}

        with patch("services.agent.nodes.human_gate.interrupt", side_effect=mock_interrupt):
            await human_gate_node(state)

        assert captured_payload["director_decision"] is None
        assert captured_payload["director_feedback"] is None
        assert captured_payload["director_reasoning_steps"] is None


# ── 12-B-7: Revise placeholder 동적 생성 ────────────────────


class TestRevisePlaceholderPrompt:
    """_generate_placeholder_prompt가 gender/style에 따라 올바른 placeholder를 생성하는지 검증한다."""

    def test_female_anime(self):
        """female + anime → '1girl, solo, anime'."""
        from services.agent.nodes.revise import _generate_placeholder_prompt

        state = {"actor_a_gender": "female", "style": "Anime"}
        assert _generate_placeholder_prompt(state) == "1girl, solo, anime"

    def test_male_anime(self):
        """male + anime → '1boy, solo, anime'."""
        from services.agent.nodes.revise import _generate_placeholder_prompt

        state = {"actor_a_gender": "male", "style": "Anime"}
        assert _generate_placeholder_prompt(state) == "1boy, solo, anime"

    def test_custom_style(self):
        """female + Realistic → '1girl, solo, realistic'."""
        from services.agent.nodes.revise import _generate_placeholder_prompt

        state = {"actor_a_gender": "female", "style": "Realistic"}
        assert _generate_placeholder_prompt(state) == "1girl, solo, realistic"

    def test_default_gender_and_style(self):
        """gender/style 미설정 시 기본값 사용."""
        from services.agent.nodes.revise import _generate_placeholder_prompt

        assert _generate_placeholder_prompt({}) == "1girl, solo, anime"

    def test_none_style_fallback(self):
        """style이 None이면 'anime' 기본값 사용."""
        from services.agent.nodes.revise import _generate_placeholder_prompt

        state = {"actor_a_gender": "male", "style": None}
        assert _generate_placeholder_prompt(state) == "1boy, solo, anime"


class TestReviseRuleFixUsesPlaceholder:
    """_try_rule_fix가 fallback_prompt를 사용하는지 검증한다."""

    def test_image_prompt_uses_fallback(self):
        """image_prompt 누락 시 fallback_prompt가 적용된다."""
        from services.agent.nodes.revise import _try_rule_fix

        scenes = [{"script": "ok", "speaker": "A", "duration": 3}]
        errors = ["씬 1: 필수 필드 'image_prompt' 누락"]
        _try_rule_fix(scenes, errors, fallback_prompt="1boy, solo, realistic")
        assert scenes[0]["image_prompt"] == "1boy, solo, realistic"

    def test_default_fallback_prompt(self):
        """fallback_prompt 미지정 시 기본값 '1girl, solo' 사용."""
        from services.agent.nodes.revise import _try_rule_fix

        scenes = [{"script": "ok", "speaker": "A", "duration": 3}]
        errors = ["씬 1: 필수 필드 'image_prompt' 누락"]
        _try_rule_fix(scenes, errors)
        assert scenes[0]["image_prompt"] == "1girl, solo"

    def test_script_placeholder_unchanged(self):
        """script 누락 시 여전히 '(placeholder)'를 사용한다."""
        from services.agent.nodes.revise import _try_rule_fix

        scenes = [{"speaker": "A", "duration": 3, "image_prompt": "ok"}]
        errors = ["씬 1: 필수 필드 'script' 누락"]
        _try_rule_fix(scenes, errors, fallback_prompt="1boy, solo, realistic")
        assert scenes[0]["script"] == "(placeholder)"
