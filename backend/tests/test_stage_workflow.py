"""Tests for Phase 18 Stage Workflow — background generation pipeline.

Covers:
- Location extraction from scenes
- Background-to-scene assignment
- compose_for_background prompt building
- calculate_auto_pin_flags with background_id
"""

from unittest.mock import MagicMock, patch


def _mock_scene(scene_id: int, env_tags: list[str] | None = None, background_id: int | None = None):
    """Create a mock Scene with context_tags and background_id."""
    scene = MagicMock()
    scene.id = scene_id
    scene.context_tags = {"environment": env_tags} if env_tags else {}
    scene.background_id = background_id
    scene.environment_reference_id = None
    scene.order = scene_id
    return scene


# ── extract_locations_from_scenes ────────────────────────────────────


def _patch_location_db():
    """Return context managers that bypass DB-dependent helpers in extract_locations_from_scenes.

    _filter_location_tags is patched to return all input tags (no DB filtering),
    and TagAliasCache.initialize is a no-op so no real DB session is needed.
    """
    p1 = patch(
        "services.stage.background_generator._filter_location_tags",
        side_effect=lambda tags, db: tags,
    )
    p2 = patch(
        "services.stage.background_generator.TagAliasCache.initialize",
    )
    p3 = patch(
        "services.stage.background_generator._resolve_location_aliases",
        side_effect=lambda tags: tags,
    )
    return p1, p2, p3


class TestExtractLocations:
    def test_groups_scenes_by_env_tags(self):
        from services.stage.background_generator import extract_locations_from_scenes

        scenes = [
            _mock_scene(1, ["cafe", "indoors"]),
            _mock_scene(2, ["park", "outdoors"]),
            _mock_scene(3, ["cafe", "indoors"]),
        ]
        p1, p2, p3 = _patch_location_db()
        with p1, p2, p3:
            result = extract_locations_from_scenes(scenes, MagicMock())

        assert len(result) == 2
        # Key is sorted tags joined
        cafe_key = "_".join(sorted(["cafe", "indoors"]))
        park_key = "_".join(sorted(["park", "outdoors"]))
        assert cafe_key in result
        assert park_key in result
        assert result[cafe_key]["scene_ids"] == [1, 3]
        assert result[park_key]["scene_ids"] == [2]

    def test_empty_env_tags_skipped(self):
        from services.stage.background_generator import extract_locations_from_scenes

        scenes = [
            _mock_scene(1, ["cafe"]),
            _mock_scene(2, []),
            _mock_scene(3, None),
        ]
        # scene 2 has empty tags, scene 3 has no context_tags
        scenes[2].context_tags = {}
        p1, p2, p3 = _patch_location_db()
        with p1, p2, p3:
            result = extract_locations_from_scenes(scenes, MagicMock())

        assert len(result) == 1

    def test_no_scenes_returns_empty(self):
        from services.stage.background_generator import extract_locations_from_scenes

        p1, p2, p3 = _patch_location_db()
        with p1, p2, p3:
            result = extract_locations_from_scenes([], MagicMock())
        assert result == {}

    def test_location_name_derived_from_first_tag(self):
        from services.stage.background_generator import extract_locations_from_scenes

        scenes = [_mock_scene(1, ["dark_alley", "outdoors"])]
        p1, p2, p3 = _patch_location_db()
        with p1, p2, p3:
            result = extract_locations_from_scenes(scenes, MagicMock())

        key = "_".join(sorted(["dark_alley", "outdoors"]))
        assert result[key]["name"] == "Dark Alley"

    def test_tags_preserved_in_original_order(self):
        from services.stage.background_generator import extract_locations_from_scenes

        scenes = [_mock_scene(1, ["classroom", "indoors", "desk"])]
        p1, p2, p3 = _patch_location_db()
        with p1, p2, p3:
            result = extract_locations_from_scenes(scenes, MagicMock())

        key = "_".join(sorted(["classroom", "indoors", "desk"]))
        assert result[key]["tags"] == ["classroom", "indoors", "desk"]


# ── assign_backgrounds_to_scenes ─────────────────────────────────────


class TestAssignBackgrounds:
    def _setup_db(self, scenes_data, backgrounds_data):
        """Create mock DB with Scene and Background query results."""
        db = MagicMock()

        scenes = []
        for sid, env_tags, bg_id in scenes_data:
            s = _mock_scene(sid, env_tags, bg_id)
            scenes.append(s)

        bgs = []
        for bg_id, loc_key, has_image in backgrounds_data:
            bg = MagicMock()
            bg.id = bg_id
            bg.location_key = loc_key
            bg.image_asset_id = 100 if has_image else None
            bg.deleted_at = None
            bgs.append(bg)

        # Mock chained query calls
        call_count = {"n": 0}

        def mock_query(model):
            q = MagicMock()
            if call_count["n"] == 0:
                q.filter.return_value.order_by.return_value.all.return_value = scenes
            else:
                q.filter.return_value.all.return_value = bgs
            call_count["n"] += 1
            return q

        db.query.side_effect = mock_query
        db.commit = MagicMock()
        return db, scenes

    def test_assigns_matching_backgrounds(self):
        from services.stage.background_generator import assign_backgrounds_to_scenes

        cafe_key = "_".join(sorted(["cafe", "indoors"]))
        db, scenes = self._setup_db(
            scenes_data=[
                (1, ["cafe", "indoors"], None),
                (2, ["park", "outdoors"], None),
            ],
            backgrounds_data=[
                (10, cafe_key, True),
            ],
        )
        p1, p2, p3 = _patch_location_db()
        with p1, p2, p3:
            result = assign_backgrounds_to_scenes(1, db)

        assert len(result) == 1
        assert result[0]["scene_id"] == 1
        assert result[0]["background_id"] == 10

    def test_skips_already_assigned(self):
        from services.stage.background_generator import assign_backgrounds_to_scenes

        cafe_key = "_".join(sorted(["cafe", "indoors"]))
        db, scenes = self._setup_db(
            scenes_data=[
                (1, ["cafe", "indoors"], 10),  # Already assigned
            ],
            backgrounds_data=[
                (10, cafe_key, True),
            ],
        )
        p1, p2, p3 = _patch_location_db()
        with p1, p2, p3:
            result = assign_backgrounds_to_scenes(1, db)

        assert len(result) == 0  # No new assignments


# ── compose_for_background ───────────────────────────────────────────


class TestComposeForBackground:
    def _get_builder(self):
        db = MagicMock()
        # Mock tag_info to return LAYER_ENVIRONMENT for all tags
        from services.prompt.v3_composition import LAYER_ENVIRONMENT, V3PromptBuilder

        builder = V3PromptBuilder(db)
        builder.get_tag_info = MagicMock(
            return_value={tag: {"layer": LAYER_ENVIRONMENT} for tag in ["classroom", "indoors", "desk"]}
        )
        return builder

    def test_contains_no_humans_and_scenery(self):
        builder = self._get_builder()
        result = builder.compose_for_background(location_tags=["classroom", "indoors"])

        assert "no_humans" in result
        assert "scenery" in result

    def test_contains_wide_shot(self):
        builder = self._get_builder()
        result = builder.compose_for_background(location_tags=["classroom"])

        assert "wide_shot" in result

    def test_contains_location_tags(self):
        builder = self._get_builder()
        result = builder.compose_for_background(location_tags=["classroom", "indoors"])

        assert "classroom" in result
        assert "indoors" in result

    def test_contains_quality_tags_when_provided(self):
        builder = self._get_builder()
        result = builder.compose_for_background(
            location_tags=["classroom"],
            quality_tags=["masterpiece", "best_quality"],
        )

        assert "masterpiece" in result
        assert "best_quality" in result

    def test_style_lora_included(self):
        builder = self._get_builder()
        builder.get_lora_weight_by_name = MagicMock(return_value=0.7)
        result = builder.compose_for_background(
            location_tags=["classroom"],
            style_loras=[{"name": "anime_style", "weight": 0.6}],
        )

        assert "<lora:anime_style:0.6>" in result

    def test_no_character_tags(self):
        """Character-only layer tags should be excluded."""
        from services.prompt.v3_composition import CHARACTER_ONLY_LAYERS, V3PromptBuilder

        db = MagicMock()
        builder = V3PromptBuilder(db)

        # Simulate a tag that maps to CHARACTER layer
        char_layer = list(CHARACTER_ONLY_LAYERS)[0]
        builder.get_tag_info = MagicMock(
            return_value={
                "classroom": {"layer": 10},  # ENVIRONMENT
                "1girl": {"layer": char_layer},
            }
        )
        result = builder.compose_for_background(location_tags=["classroom", "1girl"])

        assert "1girl" not in result
        assert "classroom" in result


# ── calculate_auto_pin_flags with background_id ──────────────────────


class TestAutoPinWithBackgroundId:
    def test_background_id_disables_auto_pin_monologue(self):
        from services.storyboard import calculate_auto_pin_flags

        scenes = [
            _mock_scene(1, ["cafe", "indoors"]),
            _mock_scene(2, ["cafe", "indoors"], background_id=10),
        ]
        result = calculate_auto_pin_flags(scenes)

        assert result[1] is False
        assert result[2] is False  # Has background_id → no auto_pin

    def test_background_id_disables_auto_pin_dialogue(self):
        from services.storyboard import calculate_auto_pin_flags

        scenes = [
            _mock_scene(1, ["cafe"]),
            _mock_scene(2, ["cafe"], background_id=10),
            _mock_scene(3, ["cafe"]),
        ]
        result = calculate_auto_pin_flags(scenes, structure="Dialogue")

        assert result[1] is False
        assert result[2] is False  # Has background_id → no auto_pin
        assert result[3] is True  # No background_id → normal dialogue auto_pin

    def test_mixed_background_and_auto_pin(self):
        from services.storyboard import calculate_auto_pin_flags

        scenes = [
            _mock_scene(1, ["cafe", "indoors"]),
            _mock_scene(2, ["cafe", "indoors"], background_id=10),
            _mock_scene(3, ["cafe", "indoors"]),
        ]
        result = calculate_auto_pin_flags(scenes)

        assert result[1] is False  # First scene
        assert result[2] is False  # Has background_id
        assert result[3] is True  # Same env as scene 2, no background_id
