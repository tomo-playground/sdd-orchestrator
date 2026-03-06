"""Tests for _enforce_character_clothing in finalize.py."""

from unittest.mock import MagicMock

from services.agent.nodes.finalize import _enforce_character_clothing


def _make_char_with_clothing(tags_data: list[tuple[str, str]]):
    """Create a mock Character with tags.

    tags_data: list of (tag_name, group_name)
    """
    char = MagicMock()
    mock_tags = []
    for name, group in tags_data:
        ct = MagicMock()
        ct.tag = MagicMock()
        ct.tag.name = name
        ct.tag.group_name = group
        mock_tags.append(ct)
    char.tags = mock_tags
    return char


def _make_db(char_a=None, char_b=None):
    """Create a mock DB that returns characters by ID."""

    def _query(model):
        q = MagicMock()
        q.options.return_value = q

        def _filter(*args, **kwargs):
            fq = MagicMock()
            # Determine which character based on filter arg
            fq.first.return_value = char_a  # default
            return fq

        q.filter = MagicMock(side_effect=_filter)
        return q

    db = MagicMock()
    # Track call count to return char_a first, char_b second
    call_count = [0]
    original_query = _query

    def _tracked_query(model):
        q = MagicMock()
        q.options.return_value = q

        def _filter(*args, **kwargs):
            fq = MagicMock()
            if call_count[0] == 0:
                fq.first.return_value = char_a
            else:
                fq.first.return_value = char_b
            call_count[0] += 1
            return fq

        q.filter = MagicMock(side_effect=_filter)
        return q

    db.query = MagicMock(side_effect=_tracked_query)
    return db


class TestEnforceCharacterClothing:
    """캐릭터 DB 복장 태그 보강 테스트."""

    def test_injects_missing_clothing(self):
        """image_prompt에 없는 clothing 태그를 보강."""
        char = _make_char_with_clothing(
            [
                ("school_uniform", "clothing"),
                ("red_ribbon", "accessory"),
            ]
        )
        db = _make_db(char_a=char)
        scenes = [{"speaker": "A", "image_prompt": "1girl, brown_hair, smile"}]

        _enforce_character_clothing(scenes, 1, None, db)

        prompt = scenes[0]["image_prompt"]
        assert "school_uniform" in prompt
        assert "red_ribbon" in prompt

    def test_skips_already_present_tags(self):
        """이미 있는 태그는 중복 추가하지 않음."""
        char = _make_char_with_clothing([("school_uniform", "clothing")])
        db = _make_db(char_a=char)
        scenes = [{"speaker": "A", "image_prompt": "1girl, school_uniform, smile"}]

        _enforce_character_clothing(scenes, 1, None, db)

        prompt = scenes[0]["image_prompt"]
        assert prompt.count("school_uniform") == 1

    def test_skips_narrator_scenes(self):
        """Narrator 씬은 건너뜀."""
        char = _make_char_with_clothing([("school_uniform", "clothing")])
        db = _make_db(char_a=char)
        scenes = [{"speaker": "Narrator", "image_prompt": "no_humans, scenery"}]

        _enforce_character_clothing(scenes, 1, None, db)

        assert "school_uniform" not in scenes[0]["image_prompt"]

    def test_skips_clothing_override_scenes(self):
        """clothing_override가 있는 씬은 건너뜀 (의도적 변경)."""
        char = _make_char_with_clothing([("school_uniform", "clothing")])
        db = _make_db(char_a=char)
        scenes = [
            {
                "speaker": "A",
                "image_prompt": "1girl, summer_dress, smile",
                "clothing_override": ["summer_dress"],
            }
        ]

        _enforce_character_clothing(scenes, 1, None, db)

        assert "school_uniform" not in scenes[0]["image_prompt"]

    def test_no_character_id_noop(self):
        """character_id가 None이면 아무것도 하지 않음."""
        scenes = [{"speaker": "A", "image_prompt": "1girl, smile"}]
        db = MagicMock()

        _enforce_character_clothing(scenes, None, None, db)

        assert scenes[0]["image_prompt"] == "1girl, smile"

    def test_speaker_b_uses_char_b_tags(self):
        """Speaker B는 char_b의 복장 태그를 사용."""
        char_a = _make_char_with_clothing([("school_uniform", "clothing")])
        char_b = _make_char_with_clothing([("hoodie", "clothing")])
        db = _make_db(char_a=char_a, char_b=char_b)
        scenes = [
            {"speaker": "A", "image_prompt": "1girl, smile"},
            {"speaker": "B", "image_prompt": "1boy, smile"},
        ]

        _enforce_character_clothing(scenes, 1, 2, db)

        assert "school_uniform" in scenes[0]["image_prompt"]
        assert "hoodie" in scenes[1]["image_prompt"]
        assert "hoodie" not in scenes[0]["image_prompt"]
        assert "school_uniform" not in scenes[1]["image_prompt"]

    def test_multiple_clothing_groups(self):
        """clothing_top, clothing_bottom 등 다양한 group도 처리."""
        char = _make_char_with_clothing(
            [
                ("white_shirt", "clothing_top"),
                ("plaid_skirt", "clothing_bottom"),
                ("glasses", "accessory"),
            ]
        )
        db = _make_db(char_a=char)
        scenes = [{"speaker": "A", "image_prompt": "1girl, brown_hair"}]

        _enforce_character_clothing(scenes, 1, None, db)

        prompt = scenes[0]["image_prompt"]
        assert "white_shirt" in prompt
        assert "plaid_skirt" in prompt
        assert "glasses" in prompt

    def test_no_clothing_tags_noop(self):
        """캐릭터에 clothing 태그가 없으면 아무것도 하지 않음."""
        char = _make_char_with_clothing([("brown_hair", "hair_color")])
        db = _make_db(char_a=char)
        scenes = [{"speaker": "A", "image_prompt": "1girl, smile"}]

        _enforce_character_clothing(scenes, 1, None, db)

        assert scenes[0]["image_prompt"] == "1girl, smile"
