"""Finalize Location Map 태그 주입 테스트."""

from __future__ import annotations

from services.agent.nodes.finalize import _inject_location_map_tags, _inject_location_negative_tags


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


class TestInjectLocationNegativeTags:
    """_inject_location_negative_tags 테스트."""

    def test_indoor_scene_gets_outdoors_negative(self):
        """indoor 장소 씬 → negative에 'outdoors' 추가."""
        scenes = [{"negative_prompt_extra": ""}]
        writer_plan = {
            "locations": [
                {"name": "kitchen", "scenes": [0], "tags": ["kitchen", "indoors"]},
            ],
        }
        _inject_location_negative_tags(scenes, writer_plan)
        assert "outdoors" in scenes[0]["negative_prompt_extra"]

    def test_outdoor_scene_gets_indoors_negative(self):
        """outdoor 장소 씬 → negative에 'indoors' 추가."""
        scenes = [{"negative_prompt_extra": ""}]
        writer_plan = {
            "locations": [
                {"name": "park", "scenes": [0], "tags": ["park", "outdoors"]},
            ],
        }
        _inject_location_negative_tags(scenes, writer_plan)
        assert "indoors" in scenes[0]["negative_prompt_extra"]

    def test_no_plan_no_change(self):
        """writer_plan 없으면 변경 없음."""
        scenes = [{"negative_prompt_extra": ""}]
        _inject_location_negative_tags(scenes, None)
        assert scenes[0]["negative_prompt_extra"] == ""

    def test_existing_negative_preserved(self):
        """기존 negative_prompt_extra가 보존되며 새 태그 추가."""
        scenes = [{"negative_prompt_extra": "rain, cloud"}]
        writer_plan = {
            "locations": [
                {"name": "classroom", "scenes": [0], "tags": ["classroom", "indoors"]},
            ],
        }
        _inject_location_negative_tags(scenes, writer_plan)
        neg = scenes[0]["negative_prompt_extra"]
        assert "rain" in neg
        assert "cloud" in neg
        assert "outdoors" in neg
