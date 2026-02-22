"""Cinematographer 경쟁 모듈 단위 테스트."""

from __future__ import annotations

import pytest

from services.agent.cinematographer_competition import (
    CINEMATOGRAPHER_PERSPECTIVES,
    score_cinematography,
)

# ── score_cinematography 단위 테스트 ─────────────────────────


class TestScoreCinematography:
    """score_cinematography 스코어링 로직 검증."""

    def test_empty_scenes(self):
        """빈 씬 리스트 → 0.0."""
        assert score_cinematography([]) == 0.0

    def test_single_scene_minimal(self):
        """최소 씬 → 0보다 큰 점수."""
        scenes = [{"image_prompt": "1girl, close-up", "camera": "close-up"}]
        score = score_cinematography(scenes)
        assert 0.0 < score <= 1.0

    def test_diverse_scenes_higher_score(self):
        """다양한 카메라/태그 씬이 단조로운 씬보다 높은 점수."""
        diverse = [
            {"image_prompt": "1girl, close-up, backlighting, depth_of_field", "camera": "close-up"},
            {"image_prompt": "1girl, from_below, silhouette, moonlight", "camera": "from_below"},
            {"image_prompt": "1girl, wide_shot, golden_hour, bokeh", "camera": "wide_shot"},
            {"image_prompt": "1girl, dutch_angle, sidelighting, chromatic_aberration", "camera": "dutch_angle"},
        ]
        monotone = [
            {"image_prompt": "1girl, close-up, looking_at_viewer", "camera": "close-up"},
            {"image_prompt": "1girl, close-up, looking_at_viewer", "camera": "close-up"},
            {"image_prompt": "1girl, close-up, looking_at_viewer", "camera": "close-up"},
            {"image_prompt": "1girl, close-up, looking_at_viewer", "camera": "close-up"},
        ]
        assert score_cinematography(diverse) > score_cinematography(monotone)

    def test_looking_at_viewer_penalty(self):
        """looking_at_viewer 과다 사용 시 gaze_balance 감점."""
        high_lat = [
            {"image_prompt": "1girl, looking_at_viewer, close-up, backlighting", "camera": "close-up"},
            {"image_prompt": "1girl, looking_at_viewer, from_below, sunlight", "camera": "from_below"},
            {"image_prompt": "1girl, looking_at_viewer, wide_shot, bokeh", "camera": "wide_shot"},
            {"image_prompt": "1girl, looking_at_viewer, dutch_angle", "camera": "dutch_angle"},
        ]
        low_lat = [
            {"image_prompt": "1girl, looking_at_viewer, close-up, backlighting", "camera": "close-up"},
            {"image_prompt": "1girl, looking_down, from_below, sunlight", "camera": "from_below"},
            {"image_prompt": "1girl, looking_afar, wide_shot, bokeh", "camera": "wide_shot"},
            {"image_prompt": "1girl, looking_to_the_side, dutch_angle", "camera": "dutch_angle"},
        ]
        assert score_cinematography(low_lat) > score_cinematography(high_lat)

    def test_lighting_richness(self):
        """라이팅 태그 보유 씬이 많을수록 높은 점수."""
        with_lighting = [
            {"image_prompt": "1girl, backlighting, close-up", "camera": "close-up"},
            {"image_prompt": "1girl, sunlight, from_below", "camera": "from_below"},
            {"image_prompt": "1girl, golden_hour, wide_shot", "camera": "wide_shot"},
        ]
        without_lighting = [
            {"image_prompt": "1girl, close-up", "camera": "close-up"},
            {"image_prompt": "1girl, from_below", "camera": "from_below"},
            {"image_prompt": "1girl, wide_shot", "camera": "wide_shot"},
        ]
        assert score_cinematography(with_lighting) > score_cinematography(without_lighting)

    def test_score_bounded(self):
        """점수가 항상 0.0-1.0 범위."""
        scenes = [
            {"image_prompt": f"1girl, tag_{i}, backlighting, depth_of_field, bokeh", "camera": f"cam_{i}"}
            for i in range(10)
        ]
        score = score_cinematography(scenes)
        assert 0.0 <= score <= 1.0

    def test_narrative_flow_monotone_penalty(self):
        """동일 카메라 반복 시 narrative_flow 감점."""
        same_camera = [
            {"image_prompt": "1girl, close-up", "camera": "close-up"},
            {"image_prompt": "1girl, close-up", "camera": "close-up"},
            {"image_prompt": "1girl, close-up", "camera": "close-up"},
        ]
        varied_camera = [
            {"image_prompt": "1girl, close-up", "camera": "close-up"},
            {"image_prompt": "1girl, from_below", "camera": "from_below"},
            {"image_prompt": "1girl, wide_shot", "camera": "wide_shot"},
        ]
        assert score_cinematography(varied_camera) > score_cinematography(same_camera)


# ── PERSPECTIVES 정의 검증 ───────────────────────────────────


class TestPerspectives:
    """경쟁 Lens 정의 검증."""

    def test_three_perspectives(self):
        """3개 Lens 정의."""
        assert len(CINEMATOGRAPHER_PERSPECTIVES) == 3

    def test_unique_roles(self):
        """모든 Lens의 role이 고유."""
        roles = [p["role"] for p in CINEMATOGRAPHER_PERSPECTIVES]
        assert len(set(roles)) == 3

    def test_required_fields(self):
        """모든 Lens에 필수 필드 존재."""
        for p in CINEMATOGRAPHER_PERSPECTIVES:
            assert "role" in p
            assert "name" in p
            assert "instruction" in p
            assert "techniques" in p
            assert "temperature" in p
            assert isinstance(p["techniques"], list)
            assert 0.0 < p["temperature"] <= 1.0

    def test_techniques_non_empty(self):
        """각 Lens에 최소 5개 이상 기법 태그."""
        for p in CINEMATOGRAPHER_PERSPECTIVES:
            assert len(p["techniques"]) >= 5, f"{p['role']}: techniques < 5"


# ── run_cinematographer_competition 통합 테스트 ──────────────


@pytest.mark.asyncio
async def test_competition_all_fail():
    """모든 Lens 실패 시 None 결과 반환."""
    from unittest.mock import AsyncMock, MagicMock, patch

    with patch(
        "services.agent.cinematographer_competition.call_with_tools",
        new_callable=AsyncMock,
        side_effect=RuntimeError("API error"),
    ):
        from services.agent.cinematographer_competition import run_cinematographer_competition

        state = {
            "draft_scenes": [{"order": 1, "text": "test"}],
            "character_id": None,
            "director_feedback": None,
            "skip_stages": [],
        }
        result = await run_cinematographer_competition(state, MagicMock(), "base prompt", None)
        assert result["scenes"] is None
        assert result["winner"] is None


@pytest.mark.asyncio
async def test_competition_selects_highest_score():
    """가장 높은 점수의 Lens가 winner로 선택된다."""
    import json
    from unittest.mock import MagicMock, patch

    # 3개 Lens에 다른 품질의 응답을 순서대로 반환
    diverse_scenes = json.dumps(
        {
            "scenes": [
                {"order": 0, "image_prompt": "1girl, close-up, backlighting, depth_of_field", "camera": "close-up"},
                {"order": 1, "image_prompt": "1girl, from_below, silhouette, moonlight", "camera": "from_below"},
                {"order": 2, "image_prompt": "1girl, wide_shot, golden_hour, bokeh", "camera": "wide_shot"},
            ]
        }
    )
    monotone_scenes = json.dumps(
        {
            "scenes": [
                {"order": 0, "image_prompt": "1girl, close-up", "camera": "close-up"},
                {"order": 1, "image_prompt": "1girl, close-up", "camera": "close-up"},
                {"order": 2, "image_prompt": "1girl, close-up", "camera": "close-up"},
            ]
        }
    )

    call_count = 0

    async def mock_call_with_tools(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return f"```json\n{diverse_scenes}\n```", []  # tension (highest)
        return f"```json\n{monotone_scenes}\n```", []

    with patch(
        "services.agent.cinematographer_competition.call_with_tools",
        side_effect=mock_call_with_tools,
    ):
        from services.agent.cinematographer_competition import run_cinematographer_competition

        state = {
            "draft_scenes": [{"order": 1}],
            "character_id": None,
            "director_feedback": None,
            "skip_stages": [],
        }
        result = await run_cinematographer_competition(state, MagicMock(), "base", None)
        assert result["winner"] == "tension"
        assert result["scores"]["tension"] > result["scores"]["intimacy"]
        assert len(result["scenes"]) == 3
