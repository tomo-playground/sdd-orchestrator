"""Intake 노드 단위 테스트.

라우팅, resume 파싱, summary 생성, fallback 등을 검증한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agent.nodes.intake import _build_intake_summary, intake_node
from services.agent.routing import route_after_start

# -- 라우팅 테스트 --


def test_intake_guided_enters():
    """Guided 모드 → route_after_start가 'intake' 반환."""
    assert route_after_start({"interaction_mode": "guided"}) == "intake"
    assert route_after_start({}) == "intake"  # 기본값 = guided


def test_intake_fast_track_skipped():
    """FastTrack 모드 → route_after_start가 'director_plan' 반환."""
    assert route_after_start({"interaction_mode": "fast_track"}) == "director_plan"


def test_intake_skip_stages_bypasses():
    """skip_stages 설정 → 'writer' 반환 (기존 동작 보존)."""
    assert route_after_start({"skip_stages": ["research"]}) == "writer"


# -- Graph 엣지 테스트 --


def test_graph_intake_edge():
    """intake → director_plan 엣지 존재 확인."""
    from services.agent.script_graph import build_script_graph

    graph = build_script_graph()
    # StateGraph.edges: list of tuples (source, target)
    edge_pairs = [(src, tgt) for src, tgt in graph.edges]
    assert ("intake", "director_plan") in edge_pairs


# -- resume 파싱 테스트 --


@dataclass
class _MockChar:
    id: int
    name: str
    gender: str = "female"
    appearance_summary: str = ""


def _make_state(**overrides) -> dict:
    """테스트용 기본 state."""
    base = {
        "topic": "학교 괴담",
        "description": "무서운 이야기",
        "group_id": 1,
        "interaction_mode": "guided",
    }
    base.update(overrides)
    return base


def _mock_analysis(structure="dialogue", tone="suspense"):
    return {
        "suggested_structure": structure,
        "suggested_tone": tone,
        "reasoning": "테스트 분석 결과",
    }


@pytest.fixture
def mock_deps():
    """intake_node의 외부 의존성을 모킹한다."""
    chars = [_MockChar(id=5, name="미도리"), _MockChar(id=8, name="하루")]
    with (
        patch(
            "services.agent.nodes.intake._load_inventory",
            return_value={"characters": chars},
        ) as inv,
        patch(
            "services.agent.nodes.intake._analyze_topic",
            new_callable=AsyncMock,
            return_value=_mock_analysis(),
        ) as analyze,
        patch("services.agent.nodes.intake.interrupt") as interrupt_mock,
    ):
        yield {"inventory": inv, "analyze": analyze, "interrupt": interrupt_mock, "chars": chars}


@pytest.mark.asyncio
async def test_intake_structure_from_resume(mock_deps):
    """resume에서 structure 올바르게 파싱."""
    mock_deps["interrupt"].return_value = {"structure": "monologue", "tone": "intimate"}
    result = await intake_node(_make_state())
    assert result["structure"] == "monologue"


@pytest.mark.asyncio
async def test_intake_tone_from_resume(mock_deps):
    """resume에서 tone 올바르게 파싱."""
    mock_deps["interrupt"].return_value = {"structure": "dialogue", "tone": "humorous"}
    result = await intake_node(_make_state())
    assert result["tone"] == "humorous"


@pytest.mark.asyncio
async def test_intake_characters_from_resume(mock_deps):
    """resume에서 character_id, character_b_id 파싱."""
    mock_deps["interrupt"].return_value = {
        "structure": "dialogue",
        "tone": "suspense",
        "character_id": 5,
        "character_b_id": 8,
    }
    result = await intake_node(_make_state())
    assert result["character_id"] == 5
    assert result["character_b_id"] == 8


@pytest.mark.asyncio
async def test_intake_fallback_to_suggestion(mock_deps):
    """resume에 값 없으면 LLM 제안값 사용."""
    mock_deps["interrupt"].return_value = {}  # 빈 resume
    result = await intake_node(_make_state())
    assert result["structure"] == "dialogue"  # LLM 제안
    assert result["tone"] == "suspense"  # LLM 제안


@pytest.mark.asyncio
async def test_intake_fallback_to_default(mock_deps):
    """LLM 제안도 없으면 기본값 (monologue/intimate)."""
    mock_deps["analyze"].return_value = {}  # 빈 분석 결과
    mock_deps["interrupt"].return_value = {}
    result = await intake_node(_make_state())
    assert result["structure"] == "monologue"
    assert result["tone"] == "intimate"


@pytest.mark.asyncio
async def test_intake_monologue_clears_char_b(mock_deps):
    """monologue 선택 시 character_b_id = None."""
    mock_deps["interrupt"].return_value = {
        "structure": "monologue",
        "tone": "intimate",
        "character_id": 5,
        "character_b_id": 8,
    }
    result = await intake_node(_make_state())
    assert result["character_b_id"] is None


@pytest.mark.asyncio
async def test_intake_invalid_structure_coerced(mock_deps):
    """잘못된 structure 값 → coerce_structure_id 정규화."""
    mock_deps["interrupt"].return_value = {"structure": "invalid_mode", "tone": "intimate"}
    result = await intake_node(_make_state())
    assert result["structure"] == "monologue"  # 기본값으로 fallback


@pytest.mark.asyncio
async def test_intake_invalid_tone_coerced(mock_deps):
    """잘못된 tone 값 → coerce_tone_id 정규화."""
    mock_deps["interrupt"].return_value = {"structure": "monologue", "tone": "unknown_tone"}
    result = await intake_node(_make_state())
    assert result["tone"] == "intimate"  # 기본값으로 fallback


@pytest.mark.asyncio
async def test_intake_characters_preserved_if_set(mock_deps):
    """state에 char 이미 설정 + resume에 없으면 기존값 유지."""
    mock_deps["interrupt"].return_value = {"structure": "dialogue", "tone": "suspense"}
    state = _make_state(character_id=5, character_b_id=8)
    result = await intake_node(state)
    assert result["character_id"] == 5
    assert result["character_b_id"] == 8


@pytest.mark.asyncio
async def test_intake_empty_group_no_characters(mock_deps):
    """그룹에 캐릭터 0명 → characters 빈 배열 전달."""
    mock_deps["inventory"].return_value = {"characters": []}
    mock_deps["interrupt"].return_value = {"structure": "monologue", "tone": "intimate"}
    result = await intake_node(_make_state())
    # interrupt payload의 characters 항목이 빈 배열인지 확인
    call_args = mock_deps["interrupt"].call_args[0][0]
    char_question = next(q for q in call_args["questions"] if q["key"] == "characters")
    assert char_question["characters"] == []
    assert result["structure"] == "monologue"


# -- Summary 테스트 --


def test_intake_summary_format():
    """intake_summary가 올바른 형식으로 생성된다."""
    chars = [_MockChar(id=5, name="미도리"), _MockChar(id=8, name="하루")]
    summary = _build_intake_summary("학교 괴담", "dialogue", "suspense", chars, 5, 8)
    assert "학교 괴담" in summary
    assert "대화형" in summary
    assert "서스펜스" in summary
    assert "미도리↔하루" in summary


def test_intake_summary_single_character():
    """1인 구조 summary에 캐릭터 1명만 표시."""
    chars = [_MockChar(id=5, name="미도리")]
    summary = _build_intake_summary("혼잣말", "monologue", "intimate", chars, 5, None)
    assert "미도리" in summary
    assert "↔" not in summary


def test_intake_summary_no_characters():
    """캐릭터 없는 summary."""
    summary = _build_intake_summary("혼잣말", "monologue", "intimate", [], None, None)
    assert "혼잣말" in summary
    assert "독백" in summary


# -- needs_two 동적 계산 테스트 --


@pytest.mark.asyncio
async def test_needs_two_true_for_dialogue(mock_deps):
    """dialogue 제안 시 needs_two=True."""
    mock_deps["analyze"].return_value = _mock_analysis(structure="dialogue")
    mock_deps["interrupt"].return_value = {"structure": "dialogue", "tone": "suspense"}
    await intake_node(_make_state())
    payload = mock_deps["interrupt"].call_args[0][0]
    char_q = next(q for q in payload["questions"] if q["key"] == "characters")
    assert char_q["needs_two"] is True


@pytest.mark.asyncio
async def test_needs_two_false_for_monologue(mock_deps):
    """monologue 제안 시 needs_two=False."""
    mock_deps["analyze"].return_value = _mock_analysis(structure="monologue")
    mock_deps["interrupt"].return_value = {"structure": "monologue", "tone": "intimate"}
    await intake_node(_make_state())
    payload = mock_deps["interrupt"].call_args[0][0]
    char_q = next(q for q in payload["questions"] if q["key"] == "characters")
    assert char_q["needs_two"] is False


# -- IntakeResumeValue 스키마 검증 --


def test_intake_resume_value_rejects_extra_fields():
    """IntakeResumeValue가 미등록 필드를 거부한다."""
    from pydantic import ValidationError

    from schemas import IntakeResumeValue

    with pytest.raises(ValidationError):
        IntakeResumeValue(structure="monologue", evil_key="hack")


def test_intake_resume_value_allows_valid_fields():
    """IntakeResumeValue가 등록된 필드만 허용한다."""
    from schemas import IntakeResumeValue

    v = IntakeResumeValue(structure="dialogue", tone="intimate", character_id=5, character_b_id=8)
    dump = v.model_dump(exclude_none=True)
    assert dump == {"structure": "dialogue", "tone": "intimate", "character_id": 5, "character_b_id": 8}


# -- LangFuse fallback 테스트 --


@pytest.mark.asyncio
async def test_analyze_topic_langfuse_missing():
    """LangFuse 프롬프트 없을 때 fallback 동작."""
    from services.agent.nodes.intake import _analyze_topic

    mock_compiled = MagicMock()
    mock_compiled.system = ""
    mock_compiled.user = ""
    mock_compiled.langfuse_prompt = None

    mock_response = MagicMock()
    mock_response.text = '{"suggested_structure": "monologue", "suggested_tone": "intimate", "reasoning": "test"}'
    mock_response.observation_id = None

    mock_provider = MagicMock(generate=AsyncMock(return_value=mock_response))
    with (
        patch("services.agent.langfuse_prompt.compile_prompt", return_value=mock_compiled),
        patch("services.llm.registry.get_llm_provider", return_value=mock_provider),
    ):
        result = await _analyze_topic("test topic", "")
        assert result.get("suggested_structure") == "monologue"
        # fallback 시 langfuse_prompt=None이 전달되어야 함
        call_kwargs = mock_provider.generate.call_args.kwargs
        assert call_kwargs["langfuse_prompt"] is None


@pytest.mark.asyncio
async def test_analyze_topic_llm_failure():
    """LLM 호출 실패 시 빈 dict 반환."""
    from services.agent.nodes.intake import _analyze_topic

    mock_compiled = MagicMock()
    mock_compiled.system = "system"
    mock_compiled.user = "user"
    mock_compiled.langfuse_prompt = None

    with (
        patch("services.agent.langfuse_prompt.compile_prompt", return_value=mock_compiled),
        patch(
            "services.llm.registry.get_llm_provider",
            return_value=MagicMock(generate=AsyncMock(side_effect=Exception("API error"))),
        ),
    ):
        result = await _analyze_topic("test", "")
        assert result == {}
