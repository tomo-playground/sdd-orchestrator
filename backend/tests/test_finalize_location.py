"""Finalize Location Map 태그 주입 테스트."""

from __future__ import annotations

import json  # noqa: F401 — TestAlignImagePromptKoEnvironment에서 사용
from unittest.mock import AsyncMock, patch  # noqa: F401

import pytest  # noqa: F401

from services.agent.nodes.finalize import (
    _align_image_prompt_ko_environment,
    _collect_cinematic_palette,
    _inject_location_map_tags,
    _inject_location_negative_tags,
    _pick_anchor,
    _stabilize_location_cinematic,
)


class TestInjectLocationMapTags:
    """_inject_location_map_tags 테스트."""

    def test_inject_location_map_tags(self):
        """Location Map 태그가 environment에 주입된다."""
        scenes = [
            {"context_tags": {"environment": ["indoors"]}},
            {"context_tags": {"environment": ["indoors"]}},
        ]
        writer_plan = {
            "locations": [
                {"name": "kitchen", "scenes": [0, 1], "tags": ["kitchen", "indoors"]},
            ],
        }
        _inject_location_map_tags(scenes, writer_plan)

        env0 = scenes[0]["context_tags"]["environment"]
        # kitchen이 앞에, indoors가 뒤에 배치
        assert "kitchen" in env0
        assert env0.index("kitchen") < env0.index("indoors")

    def test_inject_location_map_tags_no_plan(self):
        """writer_plan 없으면 변경 없음."""
        scenes = [{"context_tags": {"environment": ["indoors"]}}]
        original = list(scenes[0]["context_tags"]["environment"])

        _inject_location_map_tags(scenes, None)
        assert scenes[0]["context_tags"]["environment"] == original

        _inject_location_map_tags(scenes, {})
        assert scenes[0]["context_tags"]["environment"] == original

    def test_inject_no_duplicate_tags(self):
        """이미 존재하는 태그는 중복 추가하지 않음."""
        scenes = [
            {"context_tags": {"environment": ["classroom", "indoors"]}},
        ]
        writer_plan = {
            "locations": [
                {"name": "classroom", "scenes": [0], "tags": ["classroom", "indoors"]},
            ],
        }
        _inject_location_map_tags(scenes, writer_plan)

        env = scenes[0]["context_tags"]["environment"]
        assert env.count("classroom") == 1
        assert env.count("indoors") == 1

    def test_inject_out_of_range_scene_inherits_last_location(self):
        """Revise로 씬 수 증가 → 계획 범위 초과 씬은 마지막 위치 태그를 상속한다."""
        # 원래 계획: 씬 0,1 → office (계획된 2씬)
        # Revise Tier 2 후: 씬 2가 추가됨 (범위 초과)
        scenes = [
            {"context_tags": {}},  # 씬 0: office
            {"context_tags": {}},  # 씬 1: office
            {"context_tags": {}},  # 씬 2: 계획에 없음 → 상속
        ]
        writer_plan = {
            "locations": [
                {"name": "office", "scenes": [0, 1], "tags": ["office", "indoors"]},
            ],
        }
        _inject_location_map_tags(scenes, writer_plan)

        # 씬 2는 마지막 계획된 위치(office)의 태그를 상속해야 함
        env2 = scenes[2]["context_tags"]["environment"]
        assert "office" in env2
        assert "indoors" in env2

    def test_inject_multiple_locations_out_of_range_inherits_last(self):
        """다수 location 중 마지막 location 태그를 초과 씬이 상속한다."""
        scenes = [
            {"context_tags": {}},  # 씬 0: cafe (location A)
            {"context_tags": {}},  # 씬 1: rooftop (location B)
            {"context_tags": {}},  # 씬 2: 계획 초과 → rooftop 상속
            {"context_tags": {}},  # 씬 3: 계획 초과 → rooftop 상속
        ]
        writer_plan = {
            "locations": [
                {"name": "cafe", "scenes": [0], "tags": ["cafe", "indoors"]},
                {"name": "rooftop", "scenes": [1], "tags": ["rooftop", "outdoors"]},
            ],
        }
        _inject_location_map_tags(scenes, writer_plan)

        # 씬 2, 3은 마지막 location(rooftop)의 태그를 상속
        for i in (2, 3):
            env = scenes[i]["context_tags"]["environment"]
            assert "rooftop" in env
            assert "outdoors" in env

        # 씬 0은 cafe 태그
        assert "cafe" in scenes[0]["context_tags"]["environment"]


class TestInjectLocationNegativeTags:
    """_inject_location_negative_tags 테스트."""

    def test_indoor_scene_gets_outdoors_negative(self):
        """indoor 장소 씬 → negative에 'outdoors' 추가."""
        scenes = [{"negative_prompt": ""}]
        writer_plan = {
            "locations": [
                {"name": "kitchen", "scenes": [0], "tags": ["kitchen", "indoors"]},
            ],
        }
        _inject_location_negative_tags(scenes, writer_plan)
        assert "outdoors" in scenes[0]["negative_prompt"]

    def test_outdoor_scene_gets_indoors_negative(self):
        """outdoor 장소 씬 → negative에 'indoors' 추가."""
        scenes = [{"negative_prompt": ""}]
        writer_plan = {
            "locations": [
                {"name": "park", "scenes": [0], "tags": ["park", "outdoors"]},
            ],
        }
        _inject_location_negative_tags(scenes, writer_plan)
        assert "indoors" in scenes[0]["negative_prompt"]

    def test_no_plan_no_change(self):
        """writer_plan 없으면 변경 없음."""
        scenes = [{"negative_prompt": ""}]
        _inject_location_negative_tags(scenes, None)
        assert scenes[0]["negative_prompt"] == ""

    def test_existing_negative_preserved(self):
        """기존 negative_prompt가 보존되며 새 태그 추가."""
        scenes = [{"negative_prompt": "rain, cloud"}]
        writer_plan = {
            "locations": [
                {"name": "classroom", "scenes": [0], "tags": ["classroom", "indoors"]},
            ],
        }
        _inject_location_negative_tags(scenes, writer_plan)
        neg = scenes[0]["negative_prompt"]
        assert "rain" in neg
        assert "cloud" in neg
        assert "outdoors" in neg

    def test_post_location_conflict_removes_positive(self):
        """Location negative 주입 후 재검사로 positive↔negative 충돌이 제거된다."""
        from services.agent.nodes._prompt_conflict_resolver import _resolve_positive_negative_conflicts

        scenes = [
            {
                "image_prompt": "1girl, outdoors, park",
                "negative_prompt": "lowres",
            }
        ]
        writer_plan = {
            "locations": [
                {"name": "kitchen", "scenes": [0], "tags": ["kitchen", "indoors"]},
            ],
        }
        _inject_location_negative_tags(scenes, writer_plan)
        assert "outdoors" in scenes[0]["negative_prompt"]

        _resolve_positive_negative_conflicts(scenes)
        assert "outdoors" not in scenes[0]["image_prompt"]
        assert "1girl" in scenes[0]["image_prompt"]
        assert "park" in scenes[0]["image_prompt"]


class TestStabilizeLocationCinematic:
    """_stabilize_location_cinematic 테스트."""

    def _make_scene(self, cinematic=None):
        return {
            "context_tags": {"cinematic": cinematic or []},
            "image_prompt": "",
            "negative_prompt": "",
        }

    def test_basic_stabilization(self):
        """4개 씬: 팔레트와 다른 cinematic을 가진 중간 씬이 안정화된다.

        valid = [0, 1, 2, 3]
        팔레트 = 씬0+씬1 cinematic = {"soft_lighting"}
        valid[:-1] = [0, 1, 2] 순회 → 씬2가 팔레트 미포함이므로 안정화됨.
        씬3(마지막)은 순회 제외.
        """
        scenes = [
            self._make_scene(["soft_lighting"]),  # 0: 팔레트 기준
            self._make_scene(["soft_lighting"]),  # 1: 팔레트 기준
            self._make_scene(["high_contrast"]),  # 2: 팔레트 미포함 → 안정화 대상
            self._make_scene(["high_contrast"]),  # 3: 마지막 씬 → 제외
        ]
        writer_plan = {
            "locations": [
                {"name": "회의실", "scenes": [0, 1, 2, 3], "tags": ["indoors"]},
            ]
        }
        _stabilize_location_cinematic(scenes, writer_plan)

        # 씬2: 팔레트 태그("soft_lighting")가 cinematic 앞에 추가됨
        cinematic_2 = scenes[2]["context_tags"]["cinematic"]
        assert "soft_lighting" in cinematic_2
        assert cinematic_2[0] == "soft_lighting"

        # 씬3(마지막): 팔레트와 달라도 수정 안 됨
        cinematic_3 = scenes[3]["context_tags"]["cinematic"]
        assert cinematic_3 == ["high_contrast"]

    def test_fewer_than_3_scenes_skip(self):
        """location에 씬이 2개만 있으면 안정화를 skip한다."""
        scenes = [
            self._make_scene(["soft_lighting"]),  # 0
            self._make_scene(["high_contrast"]),  # 1
        ]
        writer_plan = {
            "locations": [
                {"name": "카페", "scenes": [0, 1], "tags": ["indoors"]},
            ]
        }
        original_0 = list(scenes[0]["context_tags"]["cinematic"])
        original_1 = list(scenes[1]["context_tags"]["cinematic"])

        _stabilize_location_cinematic(scenes, writer_plan)

        # 2개 씬이므로 변경 없음
        assert scenes[0]["context_tags"]["cinematic"] == original_0
        assert scenes[1]["context_tags"]["cinematic"] == original_1

    def test_no_palette_tags_skip(self):
        """처음 2개 씬에 cinematic 태그가 없으면 팔레트 미구성 → skip한다."""
        scenes = [
            self._make_scene([]),  # 0: cinematic 없음
            self._make_scene([]),  # 1: cinematic 없음
            self._make_scene(["high_contrast"]),  # 2
        ]
        writer_plan = {
            "locations": [
                {"name": "공원", "scenes": [0, 1, 2], "tags": ["outdoors"]},
            ]
        }
        original = list(scenes[2]["context_tags"]["cinematic"])
        _stabilize_location_cinematic(scenes, writer_plan)

        # 팔레트가 비어있으므로 씬2 변경 없음
        assert scenes[2]["context_tags"]["cinematic"] == original

    def test_no_writer_plan_returns_immediately(self):
        """writer_plan=None이면 즉시 return, 씬 변경 없음."""
        scenes = [
            self._make_scene(["soft_lighting"]),
            self._make_scene(["soft_lighting"]),
            self._make_scene(["high_contrast"]),
        ]
        original = [list(s["context_tags"]["cinematic"]) for s in scenes]

        _stabilize_location_cinematic(scenes, None)

        for i, scene in enumerate(scenes):
            assert scene["context_tags"]["cinematic"] == original[i]

    def test_last_scene_excluded_from_stabilization(self):
        """마지막 씬은 팔레트에 없는 cinematic이어도 수정하지 않는다 (감정 절정 보존)."""
        scenes = [
            self._make_scene(["soft_lighting"]),  # 0: 팔레트 기준
            self._make_scene(["soft_lighting"]),  # 1: 팔레트 기준
            self._make_scene(["soft_lighting"]),  # 2: 팔레트 포함 → 변경 없음
            self._make_scene(["dramatic"]),  # 3: 마지막 → 제외
        ]
        writer_plan = {
            "locations": [
                {"name": "옥상", "scenes": [0, 1, 2, 3], "tags": ["outdoors"]},
            ]
        }
        _stabilize_location_cinematic(scenes, writer_plan)

        # 씬3(마지막)은 팔레트와 달라도 "dramatic" 유지
        assert scenes[3]["context_tags"]["cinematic"] == ["dramatic"]


class TestCollectCinematicPalette:
    """_collect_cinematic_palette 테스트."""

    def test_collects_from_first_two_scenes(self):
        scenes = [
            {"context_tags": {"cinematic": ["soft_lighting", "warm_tones"]}},
            {"context_tags": {"cinematic": ["golden_hour"]}},
            {"context_tags": {"cinematic": ["high_contrast"]}},
        ]
        result = _collect_cinematic_palette(scenes, [0, 1, 2])
        assert result == {"soft_lighting", "warm_tones", "golden_hour"}
        assert "high_contrast" not in result

    def test_returns_empty_for_no_cinematic_tags(self):
        scenes = [
            {"context_tags": {}},
            {"context_tags": {"cinematic": []}},
        ]
        result = _collect_cinematic_palette(scenes, [0, 1])
        assert result == set()

    def test_handles_none_context_tags(self):
        scenes = [
            {"context_tags": None},
            {"context_tags": {"cinematic": ["soft_lighting"]}},
        ]
        result = _collect_cinematic_palette(scenes, [0, 1])
        assert result == {"soft_lighting"}


class TestPickAnchor:
    """_pick_anchor 테스트."""

    def test_picks_most_frequent_tag(self):
        """처음 2개 씬에서 가장 자주 등장하는 태그를 anchor로 선택"""
        scenes = [
            {"context_tags": {"cinematic": ["soft_lighting", "warm_tones"]}},
            {"context_tags": {"cinematic": ["soft_lighting", "golden_hour"]}},
        ]
        palette = {"soft_lighting", "warm_tones", "golden_hour"}
        anchor = _pick_anchor(scenes, [0, 1], palette)
        assert anchor == "soft_lighting"  # 2회 등장

    def test_tiebreak_uses_alphabetical_order(self):
        """동점 시 알파벳 순서 첫 번째 태그 선택"""
        scenes = [
            {"context_tags": {"cinematic": ["golden_hour"]}},
            {"context_tags": {"cinematic": ["soft_lighting"]}},
        ]
        palette = {"golden_hour", "soft_lighting"}
        anchor = _pick_anchor(scenes, [0, 1], palette)
        assert anchor == "golden_hour"  # g < s

    def test_returns_first_of_palette_if_no_matches(self):
        """씬에 palette 태그가 없으면 sorted(palette)[0] 반환"""
        scenes = [
            {"context_tags": {"cinematic": ["unrelated_tag"]}},
            {"context_tags": {"cinematic": []}},
        ]
        palette = {"soft_lighting", "warm_tones"}
        anchor = _pick_anchor(scenes, [0, 1], palette)
        assert anchor == sorted(palette)[0]


def _mock_llm_response(results: list[dict]) -> AsyncMock:
    """LLM provider.generate를 mock하여 지정된 JSON 결과를 반환."""
    import json as _json
    from unittest.mock import AsyncMock as _AsyncMock

    from services.llm import LLMResponse

    mock_provider = _AsyncMock()
    mock_provider.generate.return_value = LLMResponse(text=_json.dumps(results, ensure_ascii=False))
    return mock_provider


class TestAlignImagePromptKoEnvironment:
    """_align_image_prompt_ko_environment 테스트 (LLM mock 기반)."""

    @pytest.mark.asyncio
    async def test_regenerates_mismatched_location(self):
        """environment=subway_car인데 image_prompt_ko에 '사무실' → LLM이 재생성."""
        scenes = [
            {
                "script": "첫 실수, 사수님께…",
                "context_tags": {"environment": ["subway_car", "indoors"], "emotion": "happy", "action": "greeting"},
                "image_prompt_ko": "밝은 사무실에서 미소 지으며 인사하는 모습",
            },
        ]
        mock_provider = _mock_llm_response(
            [
                {"order": 0, "image_prompt_ko": "붐비는 출근길 지하철 안에서 어색하게 미소 짓는 모습"},
            ]
        )
        with patch("services.llm.get_llm_provider", return_value=mock_provider):
            await _align_image_prompt_ko_environment(scenes)

        assert scenes[0]["image_prompt_ko"] == "붐비는 출근길 지하철 안에서 어색하게 미소 짓는 모습"
        mock_provider.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_when_no_specific_env(self):
        """environment에 generic 태그(indoors)만 있으면 LLM 호출 안 함."""
        scenes = [
            {
                "context_tags": {"environment": ["indoors"]},
                "image_prompt_ko": "사무실에서 웃고 있는 모습",
            },
        ]
        mock_provider = _mock_llm_response([])
        with patch("services.llm.get_llm_provider", return_value=mock_provider):
            await _align_image_prompt_ko_environment(scenes)

        mock_provider.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_no_prompt_ko(self):
        """image_prompt_ko가 없으면 LLM 호출 안 함."""
        scenes = [
            {
                "context_tags": {"environment": ["office", "indoors"]},
            },
        ]
        mock_provider = _mock_llm_response([])
        with patch("services.llm.get_llm_provider", return_value=mock_provider):
            await _align_image_prompt_ko_environment(scenes)

        mock_provider.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_scenes_batch(self):
        """여러 씬을 1회 배치 호출로 재생성."""
        scenes = [
            {
                "script": "사무실에서 일하는 중",
                "context_tags": {"environment": ["office", "indoors"], "emotion": "focused", "action": "typing"},
                "image_prompt_ko": "사무실에서 일하는 모습",
            },
            {
                "script": "지하철에서 인사",
                "context_tags": {"environment": ["subway_car", "indoors"], "emotion": "happy", "action": "greeting"},
                "image_prompt_ko": "사무실에서 인사하는 모습",
            },
        ]
        mock_provider = _mock_llm_response(
            [
                {"order": 0, "image_prompt_ko": "밝은 사무실 책상에서 집중하며 타이핑하는 모습"},
                {"order": 1, "image_prompt_ko": "붐비는 지하철 안에서 반갑게 인사하는 모습"},
            ]
        )
        with patch("services.llm.get_llm_provider", return_value=mock_provider):
            await _align_image_prompt_ko_environment(scenes)

        assert scenes[0]["image_prompt_ko"] == "밝은 사무실 책상에서 집중하며 타이핑하는 모습"
        assert scenes[1]["image_prompt_ko"] == "붐비는 지하철 안에서 반갑게 인사하는 모습"
        # 1회만 호출 (배치)
        assert mock_provider.generate.call_count == 1

    @pytest.mark.asyncio
    async def test_llm_failure_preserves_original(self):
        """LLM 호출 실패 시 원본 image_prompt_ko 유지."""
        scenes = [
            {
                "script": "테스트",
                "context_tags": {"environment": ["subway_car", "indoors"], "emotion": "happy", "action": "greeting"},
                "image_prompt_ko": "밝은 사무실에서 인사하는 모습",
            },
        ]
        original = scenes[0]["image_prompt_ko"]
        mock_provider = AsyncMock()
        mock_provider.generate.side_effect = RuntimeError("API error")
        with patch("services.llm.get_llm_provider", return_value=mock_provider):
            await _align_image_prompt_ko_environment(scenes)

        assert scenes[0]["image_prompt_ko"] == original

    @pytest.mark.asyncio
    async def test_env_string_instead_of_list(self):
        """environment가 str이어도 동작."""
        scenes = [
            {
                "script": "테스트",
                "context_tags": {"environment": "subway_car", "emotion": "happy", "action": "greeting"},
                "image_prompt_ko": "사무실에서 웃는 모습",
            },
        ]
        mock_provider = _mock_llm_response(
            [
                {"order": 0, "image_prompt_ko": "지하철 안에서 환하게 웃는 모습"},
            ]
        )
        with patch("services.llm.get_llm_provider", return_value=mock_provider):
            await _align_image_prompt_ko_environment(scenes)

        assert scenes[0]["image_prompt_ko"] == "지하철 안에서 환하게 웃는 모습"

    @pytest.mark.asyncio
    async def test_partial_llm_response(self):
        """LLM이 일부 씬만 응답해도 해당 씬만 업데이트."""
        scenes = [
            {
                "script": "씬0",
                "context_tags": {"environment": ["office", "indoors"], "emotion": "happy", "action": "working"},
                "image_prompt_ko": "원본0",
            },
            {
                "script": "씬1",
                "context_tags": {"environment": ["cafe", "indoors"], "emotion": "relaxed", "action": "drinking"},
                "image_prompt_ko": "원본1",
            },
        ]
        # order=1만 응답
        mock_provider = _mock_llm_response(
            [
                {"order": 1, "image_prompt_ko": "아늑한 카페에서 여유롭게 커피를 마시는 모습"},
            ]
        )
        with patch("services.llm.get_llm_provider", return_value=mock_provider):
            await _align_image_prompt_ko_environment(scenes)

        assert scenes[0]["image_prompt_ko"] == "원본0"  # 응답 없어서 원본 유지
        assert scenes[1]["image_prompt_ko"] == "아늑한 카페에서 여유롭게 커피를 마시는 모습"
