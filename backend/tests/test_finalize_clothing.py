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


def _make_tag_rows(tags_data: list[tuple[str, str]]):
    """Create mock Tag rows for db.query(Tag).filter().all()."""
    rows = []
    for name, group in tags_data:
        row = MagicMock()
        row.name = name
        row.group_name = group
        rows.append(row)
    return rows


def _make_db(char_a=None, char_b=None, tag_rows=None):
    """Create a mock DB that returns characters by ID and tags by name."""
    from models.tag import Tag  # noqa: F811

    char_call_count = [0]

    def _query(*models):
        from models.character import Character as CharModel

        # Character query path uses exactly 1 arg == Character
        is_char = len(models) == 1 and models[0] is CharModel
        if not is_char:
            # Tag query path: db.query(Tag) or db.query(Tag.name, Tag.group_name)
            q = MagicMock()

            def _tag_filter(*_a, **_kw):
                fq = MagicMock()
                fq.all.return_value = tag_rows or []
                return fq

            q.filter = MagicMock(side_effect=_tag_filter)
            return q

        # Character query path
        q = MagicMock()
        q.options.return_value = q

        def _filter(*_a, **_kw):
            fq = MagicMock()
            if char_call_count[0] == 0:
                fq.first.return_value = char_a
            else:
                fq.first.return_value = char_b
            char_call_count[0] += 1
            return fq

        q.filter = MagicMock(side_effect=_filter)
        return q

    db = MagicMock()
    db.query = MagicMock(side_effect=_query)
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


class TestStripNonDbClothing:
    """Gemini가 자의적으로 추가한 비-DB 복장 태그 제거 테스트."""

    def test_removes_gemini_added_clothing(self):
        """DB에 없는 복장 태그를 제거하고 DB 태그를 보강."""
        char = _make_char_with_clothing([("pink_dress", "clothing_outfit")])
        tag_rows = _make_tag_rows(
            [
                ("pink_dress", "clothing_outfit"),
                ("blue_skirt", "clothing_bottom"),
            ]
        )
        db = _make_db(char_a=char, tag_rows=tag_rows)
        scenes = [{"speaker": "A", "image_prompt": "1girl, blue_skirt, smile"}]

        _enforce_character_clothing(scenes, 1, None, db)

        prompt = scenes[0]["image_prompt"]
        assert "blue_skirt" not in prompt
        assert "pink_dress" in prompt

    def test_keeps_non_clothing_tags(self):
        """복장이 아닌 태그(카메라, 환경 등)는 유지."""
        char = _make_char_with_clothing([("school_uniform", "clothing")])
        tag_rows = _make_tag_rows(
            [
                ("school_uniform", "clothing"),
                ("close-up", "camera"),
                ("kitchen", "environment"),
            ]
        )
        db = _make_db(char_a=char, tag_rows=tag_rows)
        scenes = [{"speaker": "A", "image_prompt": "1girl, close-up, kitchen"}]

        _enforce_character_clothing(scenes, 1, None, db)

        prompt = scenes[0]["image_prompt"]
        assert "close-up" in prompt
        assert "kitchen" in prompt
        assert "school_uniform" in prompt

    def test_removes_multiple_conflicting_clothing(self):
        """Gemini가 여러 복장 태그를 추가해도 모두 제거."""
        char = _make_char_with_clothing(
            [
                ("green_hoodie", "clothing_top"),
                ("cargo_pants", "clothing_bottom"),
            ]
        )
        tag_rows = _make_tag_rows(
            [
                ("green_hoodie", "clothing_top"),
                ("cargo_pants", "clothing_bottom"),
                ("white_shirt", "clothing_top"),
                ("brown_pants", "clothing_bottom"),
                ("checkered_shirt", "clothing_top"),
            ]
        )
        db = _make_db(char_a=char, tag_rows=tag_rows)
        scenes = [
            {
                "speaker": "A",
                "image_prompt": "1boy, white_shirt, brown_pants, checkered_shirt, smile",
            }
        ]

        _enforce_character_clothing(scenes, 1, None, db)

        prompt = scenes[0]["image_prompt"]
        assert "white_shirt" not in prompt
        assert "brown_pants" not in prompt
        assert "checkered_shirt" not in prompt
        assert "green_hoodie" in prompt
        assert "cargo_pants" in prompt

    def test_preserves_db_clothing_in_prompt(self):
        """DB 복장 태그가 이미 prompt에 있으면 유지 + 중복 추가 안 함."""
        char = _make_char_with_clothing([("school_uniform", "clothing")])
        tag_rows = _make_tag_rows([("school_uniform", "clothing")])
        db = _make_db(char_a=char, tag_rows=tag_rows)
        scenes = [{"speaker": "A", "image_prompt": "1girl, school_uniform, smile"}]

        _enforce_character_clothing(scenes, 1, None, db)

        prompt = scenes[0]["image_prompt"]
        assert prompt.count("school_uniform") == 1

    def test_clothing_override_bypasses_strip(self):
        """clothing_override 씬은 비-DB 복장 제거도 건너뜀."""
        char = _make_char_with_clothing([("school_uniform", "clothing")])
        tag_rows = _make_tag_rows(
            [
                ("summer_dress", "clothing_outfit"),
            ]
        )
        db = _make_db(char_a=char, tag_rows=tag_rows)
        scenes = [
            {
                "speaker": "A",
                "image_prompt": "1girl, summer_dress, smile",
                "clothing_override": ["summer_dress"],
            }
        ]

        _enforce_character_clothing(scenes, 1, None, db)

        prompt = scenes[0]["image_prompt"]
        assert "summer_dress" in prompt
        assert "school_uniform" not in prompt

    def test_speaker_b_strip_and_inject(self):
        """Speaker B도 비-DB 복장 제거 + DB 복장 보강 적용."""
        char_a = _make_char_with_clothing([("pink_dress", "clothing_outfit")])
        char_b = _make_char_with_clothing([("hoodie", "clothing_top")])
        tag_rows = _make_tag_rows(
            [
                ("pink_dress", "clothing_outfit"),
                ("hoodie", "clothing_top"),
                ("blue_jacket", "clothing_top"),
            ]
        )
        db = _make_db(char_a=char_a, char_b=char_b, tag_rows=tag_rows)
        scenes = [
            {"speaker": "A", "image_prompt": "1girl, smile"},
            {"speaker": "B", "image_prompt": "1boy, blue_jacket, smile"},
        ]

        _enforce_character_clothing(scenes, 1, 2, db)

        prompt_a = scenes[0]["image_prompt"]
        assert "pink_dress" in prompt_a

        prompt_b = scenes[1]["image_prompt"]
        assert "blue_jacket" not in prompt_b
        assert "hoodie" in prompt_b

    def test_unknown_tag_not_in_db_preserved(self):
        """DB Tag 테이블에 없는 토큰(group_name 불명)은 제거하지 않음."""
        char = _make_char_with_clothing([("school_uniform", "clothing")])
        # tag_rows에 invented_tag이 없음 → group_name을 알 수 없으므로 유지
        tag_rows = _make_tag_rows([("school_uniform", "clothing")])
        db = _make_db(char_a=char, tag_rows=tag_rows)
        scenes = [{"speaker": "A", "image_prompt": "1girl, invented_tag, smile"}]

        _enforce_character_clothing(scenes, 1, None, db)

        prompt = scenes[0]["image_prompt"]
        assert "invented_tag" in prompt
        assert "school_uniform" in prompt
