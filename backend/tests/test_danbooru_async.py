"""Tests for async Danbooru validation + background scheduling.

Covers:
- validate_tags_with_danbooru_async: DB cache only, fail-open for unknown tags
- schedule_background_classification: safe in both async and sync contexts
- DirectorCheckpointOutput feedback null coercion
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# -- validate_tags_with_danbooru_async --


@pytest.mark.asyncio
async def test_validate_async_db_hit():
    """DB에 있는 태그는 validated, unknown 비어있음."""
    mock_db = MagicMock()
    mock_tag = MagicMock()
    mock_tag.name = "blue_hair"
    mock_db.query.return_value.all.return_value = [mock_tag]

    with patch("database.SessionLocal", return_value=mock_db):
        from services.prompt.prompt import validate_tags_with_danbooru_async

        validated, unknown = await validate_tags_with_danbooru_async(["blue_hair"])

    assert validated == ["blue_hair"]
    assert unknown == []


@pytest.mark.asyncio
async def test_validate_async_db_miss_failopen():
    """DB에 없는 태그는 fail-open으로 validated + unknown 양쪽에 추가."""
    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = []

    with patch("database.SessionLocal", return_value=mock_db):
        from services.prompt.prompt import validate_tags_with_danbooru_async

        validated, unknown = await validate_tags_with_danbooru_async(["new_tag"])

    assert "new_tag" in validated
    assert "new_tag" in unknown


@pytest.mark.asyncio
async def test_validate_async_mixed():
    """DB hit + miss 혼합 시나리오."""
    mock_db = MagicMock()
    known = MagicMock()
    known.name = "smile"
    mock_db.query.return_value.all.return_value = [known]

    with patch("database.SessionLocal", return_value=mock_db):
        from services.prompt.prompt import validate_tags_with_danbooru_async

        validated, unknown = await validate_tags_with_danbooru_async(["smile", "invented_tag"])

    assert "smile" in validated
    assert "invented_tag" in validated
    assert unknown == ["invented_tag"]


@pytest.mark.asyncio
async def test_validate_async_space_format_fallback():
    """언더바 태그가 DB에 공백 형식으로 저장된 경우에도 매칭."""
    mock_db = MagicMock()
    space_tag = MagicMock()
    space_tag.name = "blue hair"
    mock_db.query.return_value.all.return_value = [space_tag]

    with patch("database.SessionLocal", return_value=mock_db):
        from services.prompt.prompt import validate_tags_with_danbooru_async

        validated, unknown = await validate_tags_with_danbooru_async(["blue_hair"])

    assert "blue_hair" in validated
    assert unknown == []


# -- schedule_background_classification --


def test_schedule_bg_empty_list():
    """빈 리스트는 아무것도 하지 않음."""
    from services.danbooru import schedule_background_classification

    schedule_background_classification([])


def test_schedule_bg_deduplicates():
    """중복 태그는 set으로 제거."""
    with patch("services.danbooru._classify_tags_background") as mock_bg:
        with patch("services.danbooru.asyncio.get_running_loop", side_effect=RuntimeError):
            from services.danbooru import schedule_background_classification

            schedule_background_classification(["a", "b", "a", "b", "c"])

        called_tags = mock_bg.call_args[0][0]
        assert len(called_tags) == len(set(called_tags))


# -- DirectorCheckpointOutput feedback null coercion --


def test_checkpoint_feedback_none_coerced():
    """feedback=None이 빈 문자열로 변환됨 (Gemini null 반환 대응)."""
    from services.agent.llm_models import DirectorCheckpointOutput

    obj = DirectorCheckpointOutput(
        decision="proceed",
        score=0.8,
        reasoning="Looks good",
        feedback=None,
    )
    assert obj.feedback == ""


def test_checkpoint_feedback_string_preserved():
    """일반 문자열 feedback은 그대로 유지."""
    from services.agent.llm_models import DirectorCheckpointOutput

    obj = DirectorCheckpointOutput(
        decision="revise",
        score=0.3,
        reasoning="Needs work",
        feedback="Fix scene 2",
    )
    assert obj.feedback == "Fix scene 2"


def test_checkpoint_feedback_empty_string():
    """빈 문자열 feedback + proceed는 정상."""
    from services.agent.llm_models import DirectorCheckpointOutput

    obj = DirectorCheckpointOutput(
        decision="proceed",
        score=0.9,
        reasoning="All good",
        feedback="",
    )
    assert obj.feedback == ""


def test_checkpoint_revise_requires_feedback():
    """decision=revise인데 feedback이 없으면 여전히 에러."""
    from pydantic import ValidationError

    from services.agent.llm_models import DirectorCheckpointOutput

    with pytest.raises(ValidationError):
        DirectorCheckpointOutput(
            decision="revise",
            score=0.3,
            reasoning="Bad",
            feedback=None,
        )
