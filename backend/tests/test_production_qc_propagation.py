"""TTS/Sound/Copyright QC 결과 → Director 전파 테스트.

검증 범위:
1. 각 노드(TTS, Sound, Copyright)가 QC 결과를 state에 저장하는지
2. build_production_qc_section() 빌더 함수의 포맷팅
3. Director template_vars에 production_qc_section이 포함되는지
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.agent.prompt_builders_b import build_production_qc_section

# ── build_production_qc_section 빌더 테스트 ──


class TestBuildProductionQcSection:
    """build_production_qc_section 포맷팅 테스트."""

    def test_all_ok_returns_empty(self):
        """모든 QC가 ok이면 빈 문자열."""
        state = {
            "tts_qc_result": {"ok": True, "issues": []},
            "sound_qc_result": {"ok": True, "issues": []},
            "copyright_qc_result": {"ok": True, "issues": []},
        }
        assert build_production_qc_section(state) == ""

    def test_all_none_returns_empty(self):
        """QC 결과가 없으면 빈 문자열."""
        assert build_production_qc_section({}) == ""

    def test_tts_qc_issues_formatted(self):
        """TTS QC 이슈가 포맷팅된다."""
        state = {
            "tts_qc_result": {
                "ok": False,
                "issues": ["Scene 0: missing voice_design_prompt"],
            },
        }
        result = build_production_qc_section(state)
        assert "TTS Design QC Warnings" in result
        assert "missing voice_design_prompt" in result
        assert "revise_tts_designer" in result

    def test_sound_qc_issues_formatted(self):
        """Sound QC 이슈가 포맷팅된다."""
        state = {
            "sound_qc_result": {
                "ok": False,
                "issues": ["Missing music prompt"],
            },
        }
        result = build_production_qc_section(state)
        assert "Sound Design QC Warnings" in result
        assert "Missing music prompt" in result
        assert "revise_sound_designer" in result

    def test_copyright_qc_issues_formatted(self):
        """Copyright QC 이슈가 포맷팅된다."""
        state = {
            "copyright_qc_result": {
                "ok": False,
                "issues": ["character_similarity: Possible IP issue"],
            },
        }
        result = build_production_qc_section(state)
        assert "Copyright QC Warnings" in result
        assert "Possible IP issue" in result
        assert "revise_copyright_reviewer" in result

    def test_multiple_qc_failures_combined(self):
        """여러 QC 실패가 하나의 문자열로 합쳐진다."""
        state = {
            "tts_qc_result": {"ok": False, "issues": ["TTS issue"]},
            "sound_qc_result": {"ok": True, "issues": []},
            "copyright_qc_result": {"ok": False, "issues": ["Copyright issue"]},
        }
        result = build_production_qc_section(state)
        assert "TTS Design QC Warnings" in result
        assert "Copyright QC Warnings" in result
        assert "Sound Design QC Warnings" not in result

    def test_partial_none_handled(self):
        """일부 QC만 None이어도 정상 동작."""
        state = {
            "tts_qc_result": None,
            "sound_qc_result": {"ok": False, "issues": ["Invalid duration"]},
        }
        result = build_production_qc_section(state)
        assert "Sound Design QC Warnings" in result
        assert "TTS Design QC Warnings" not in result


# ── TTS Designer 노드 QC 전파 테스트 ──


@pytest.mark.asyncio
@patch("services.agent.nodes.tts_designer.run_production_step", new_callable=AsyncMock)
@patch("services.agent.nodes.tts_designer._load_character_voice_context", return_value=None)
async def test_tts_designer_stores_qc_result(mock_voice, mock_run):
    """TTS Designer가 tts_qc_result를 state에 저장한다."""
    from services.agent.nodes.tts_designer import tts_designer_node

    mock_run.return_value = {
        "tts_designs": [
            {
                "speaker": "speaker_1",
                "voice_design_prompt": "calm female",
                "pacing": {"head_padding": 0.1, "tail_padding": 0.3},
            },
        ],
    }

    state = {
        "cinematographer_result": {"scenes": [{"order": 1}]},
        "critic_result": {},
        "director_feedback": None,
        "director_plan": None,
        "writer_plan": None,
        "skip_stages": [],
    }
    result = await tts_designer_node(state)

    assert "tts_qc_result" in result
    assert result["tts_qc_result"]["ok"] is True


@pytest.mark.asyncio
@patch("services.agent.nodes.tts_designer.run_production_step", new_callable=AsyncMock)
@patch("services.agent.nodes.tts_designer._load_character_voice_context", return_value=None)
async def test_tts_designer_qc_failure_stored(mock_voice, mock_run):
    """TTS Designer QC 실패 시에도 결과가 저장된다."""
    from services.agent.nodes.tts_designer import tts_designer_node

    mock_run.return_value = {
        "tts_designs": [
            {"speaker": "speaker_1", "pacing": {"head_padding": 0.1, "tail_padding": 0.3}},
        ],
    }

    state = {
        "cinematographer_result": {"scenes": [{"order": 1}]},
        "critic_result": {},
        "director_feedback": None,
        "director_plan": None,
        "writer_plan": None,
        "skip_stages": [],
    }
    result = await tts_designer_node(state)

    assert "tts_qc_result" in result
    assert result["tts_qc_result"]["ok"] is False
    assert any("missing voice_design_prompt" in i for i in result["tts_qc_result"]["issues"])


# ── Sound Designer 노드 QC 전파 테스트 ──


@pytest.mark.asyncio
@patch("services.agent.nodes.sound_designer.run_production_step", new_callable=AsyncMock)
async def test_sound_designer_stores_qc_result(mock_run):
    """Sound Designer가 sound_qc_result를 state에 저장한다."""
    from services.agent.nodes.sound_designer import sound_designer_node

    mock_run.return_value = {
        "recommendation": {"prompt": "calm piano", "mood": "peaceful", "duration": 30},
    }

    state = {
        "cinematographer_result": {"scenes": [{"order": 1}]},
        "critic_result": {},
        "duration": 30,
        "language": "korean",
        "director_feedback": None,
        "writer_plan": None,
        "skip_stages": [],
    }
    result = await sound_designer_node(state)

    assert "sound_qc_result" in result
    assert result["sound_qc_result"]["ok"] is True


@pytest.mark.asyncio
@patch("services.agent.nodes.sound_designer.run_production_step", new_callable=AsyncMock)
async def test_sound_designer_qc_failure_stored(mock_run):
    """Sound Designer QC 실패 시에도 결과가 저장된다."""
    from services.agent.nodes.sound_designer import sound_designer_node

    mock_run.return_value = {
        "recommendation": {"prompt": "", "mood": "", "duration": 5},
    }

    state = {
        "cinematographer_result": {"scenes": [{"order": 1}]},
        "critic_result": {},
        "duration": 30,
        "language": "korean",
        "director_feedback": None,
        "writer_plan": None,
        "skip_stages": [],
    }
    result = await sound_designer_node(state)

    assert "sound_qc_result" in result
    assert result["sound_qc_result"]["ok"] is False


# ── Copyright Reviewer 노드 QC 전파 테스트 ──


@pytest.mark.asyncio
@patch("services.agent.nodes.copyright_reviewer.run_production_step", new_callable=AsyncMock)
async def test_copyright_reviewer_stores_qc_result(mock_run):
    """Copyright Reviewer가 copyright_qc_result를 state에 저장한다."""
    from services.agent.nodes.copyright_reviewer import copyright_reviewer_node

    mock_run.return_value = {
        "checks": [
            {"type": "character_similarity", "status": "PASS", "detail": "OK", "suggestion": None},
        ],
        "overall": "PASS",
    }

    state = {
        "cinematographer_result": {"scenes": [{"order": 1}]},
        "language": "korean",
        "director_feedback": None,
        "skip_stages": [],
    }
    result = await copyright_reviewer_node(state)

    assert "copyright_qc_result" in result
    assert result["copyright_qc_result"]["ok"] is True


@pytest.mark.asyncio
@patch("services.agent.nodes.copyright_reviewer.run_production_step", new_callable=AsyncMock)
async def test_copyright_reviewer_qc_failure_stored(mock_run):
    """Copyright Reviewer QC FAIL 시에도 결과가 저장된다."""
    from services.agent.nodes.copyright_reviewer import copyright_reviewer_node

    mock_run.return_value = {
        "checks": [
            {
                "type": "character_similarity",
                "status": "FAIL",
                "detail": "Too similar to IP X",
                "suggestion": "Modify design",
            },
        ],
        "overall": "FAIL",
    }

    state = {
        "cinematographer_result": {"scenes": [{"order": 1}]},
        "language": "korean",
        "director_feedback": None,
        "skip_stages": [],
    }
    result = await copyright_reviewer_node(state)

    assert "copyright_qc_result" in result
    assert result["copyright_qc_result"]["ok"] is False
    assert any("Too similar to IP X" in i for i in result["copyright_qc_result"]["issues"])


# ── Director production_qc_section 주입 테스트 ──


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_production_qc_in_template_vars(mock_run):
    """production_qc_section이 Director template_vars에 포함된다."""
    from services.agent.nodes.director import director_node
    from services.agent.state import ScriptState

    captured_vars: list[dict] = []

    async def capture_and_approve(*args, **kwargs):
        captured_vars.append(dict(kwargs["template_vars"]))
        return {"observe": "QC 확인", "think": "승인", "act": "approve"}

    mock_run.side_effect = capture_and_approve

    state: ScriptState = {  # type: ignore[typeddict-item]
        "cinematographer_result": {"scenes": [{"order": 1}]},
        "tts_designer_result": {"tts_designs": []},
        "sound_designer_result": {"recommendation": {}},
        "copyright_reviewer_result": {"checks": [], "overall": "PASS"},
        "tts_qc_result": {"ok": False, "issues": ["TTS issue found"]},
        "sound_qc_result": {"ok": True, "issues": []},
        "copyright_qc_result": None,
        "visual_qc_result": None,
        "director_revision_count": 0,
        "revision_count": 0,
        "concept_regen_count": 0,
        "skip_stages": [],
    }

    await director_node(state, {})

    assert len(captured_vars) == 1
    pqs = captured_vars[0]["production_qc_section"]
    assert "TTS Design QC Warnings" in pqs
    assert "TTS issue found" in pqs


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_production_qc_empty_when_all_ok(mock_run):
    """모든 QC 통과 시 production_qc_section은 빈 문자열."""
    from services.agent.nodes.director import director_node
    from services.agent.state import ScriptState

    captured_vars: list[dict] = []

    async def capture_and_approve(*args, **kwargs):
        captured_vars.append(dict(kwargs["template_vars"]))
        return {"observe": "정상", "think": "승인", "act": "approve"}

    mock_run.side_effect = capture_and_approve

    state: ScriptState = {  # type: ignore[typeddict-item]
        "cinematographer_result": {"scenes": [{"order": 1}]},
        "tts_designer_result": {"tts_designs": []},
        "sound_designer_result": {"recommendation": {}},
        "copyright_reviewer_result": {"checks": [], "overall": "PASS"},
        "tts_qc_result": {"ok": True, "issues": []},
        "sound_qc_result": {"ok": True, "issues": []},
        "copyright_qc_result": {"ok": True, "issues": []},
        "visual_qc_result": None,
        "director_revision_count": 0,
        "revision_count": 0,
        "concept_regen_count": 0,
        "skip_stages": [],
    }

    await director_node(state, {})

    assert len(captured_vars) == 1
    assert captured_vars[0]["production_qc_section"] == ""
