"""Tests for Phase 18 Stage Workflow — background generation pipeline.

Covers:
- Location extraction from scenes
- Background-to-scene assignment
- compose_for_background prompt building
- calculate_auto_pin_flags with background_id
- Express mode compatibility (P3-1)
- style_profile_id caching (P3-3)
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
        "services.stage.background_location._filter_location_tags",
        side_effect=lambda tags, db: tags,
    )
    p2 = patch(
        "services.stage.background_location.TagAliasCache.initialize",
    )
    p3 = patch(
        "services.stage.background_location._resolve_location_aliases",
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
        assert result[key]["name"] == "Dark"  # key.split("_")[0].title()

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

        def mock_query(_model):
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
        from services.prompt.composition import LAYER_ENVIRONMENT, PromptBuilder

        builder = PromptBuilder(db)
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
        from services.prompt.composition import CHARACTER_ONLY_LAYERS, PromptBuilder

        db = MagicMock()
        builder = PromptBuilder(db)

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


# ── Express mode compatibility (P3-1) ────────────────────────────────


class TestExpressModeCompatibility:
    """Express mode skips planning → writer_plan=None → no location map.
    Scenes still have context_tags.environment from direct LLM generation.
    """

    def test_extract_locations_from_express_mode_scenes(self):
        """Environment tags alone (no writer_plan) should extract locations."""
        from services.stage.background_generator import extract_locations_from_scenes

        scenes = [
            _mock_scene(1, ["street", "night"]),
            _mock_scene(2, ["classroom", "indoors"]),
            _mock_scene(3, ["street", "night"]),
        ]
        p1, p2, p3 = _patch_location_db()
        with p1, p2, p3:
            result = extract_locations_from_scenes(scenes, MagicMock())

        assert len(result) == 2
        street_key = "_".join(sorted(["street", "night"]))
        assert street_key in result
        assert result[street_key]["scene_ids"] == [1, 3]

    def test_stage_status_with_no_environment_tags(self):
        """Scenes with empty context_tags → empty locations, no error."""
        from services.stage.background_generator import extract_locations_from_scenes

        scenes = [
            _mock_scene(1),  # No env tags
            _mock_scene(2),
        ]
        p1, p2, p3 = _patch_location_db()
        with p1, p2, p3:
            result = extract_locations_from_scenes(scenes, MagicMock())

        assert result == {}

    def test_generate_backgrounds_express_no_env_warns(self, caplog):
        """No environment tags → warning log + empty result."""
        import asyncio
        import logging

        from services.stage.background_generator import generate_location_backgrounds

        db = MagicMock()
        sb = MagicMock()
        sb.id = 1
        sb.deleted_at = None
        sb.stage_status = None

        scene = _mock_scene(1)  # No env tags

        db.query.return_value.filter.return_value.first.return_value = sb
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [scene]

        p1, p2, p3 = _patch_location_db()
        with p1, p2, p3, caplog.at_level(logging.WARNING):
            result = asyncio.new_event_loop().run_until_complete(generate_location_backgrounds(1, db))

        assert result == []
        assert any("Express mode" in r.message for r in caplog.records)


# ── style_profile_id caching (P3-3) ──────────────────────────────────


class TestStyleProfileCaching:
    """Background cache should key on (storyboard_id, location_key, style_profile_id)."""

    def _run_generate_with_style(self, style_profile_id, existing_bg):
        """Helper: run generate_location_backgrounds with mocked style & DB."""
        import asyncio

        from services.stage.background_generator import generate_location_backgrounds

        db = MagicMock()
        sb = MagicMock()
        sb.id = 1
        sb.deleted_at = None
        sb.stage_status = None

        scene = _mock_scene(1, ["cafe", "indoors"])
        style_ctx = MagicMock()
        style_ctx.profile_id = style_profile_id
        style_ctx.default_positive = "masterpiece"
        style_ctx.sd_model_name = None

        # DB query routing: 1st call=Storyboard, 2nd call=Scene, 3rd+=Background
        call_count = {"n": 0}

        def mock_query(_model):
            q = MagicMock()
            if call_count["n"] == 0:
                q.filter.return_value.first.return_value = sb
            elif call_count["n"] == 1:
                q.filter.return_value.order_by.return_value.all.return_value = [scene]
            else:
                inner_q = MagicMock()
                inner_q.filter.return_value = inner_q
                inner_q.first.return_value = existing_bg
                q.filter.return_value = inner_q
            call_count["n"] += 1
            return q

        db.query.side_effect = mock_query

        p1, p2, p3 = _patch_location_db()

        asset_mock = MagicMock()
        asset_mock.id = 200
        asset_svc = MagicMock()
        asset_svc.save_background_image.return_value = asset_mock

        # Mock Background constructor so new objects get an id
        new_bg = MagicMock()
        new_bg.id = 99
        new_bg.image_asset_id = None
        new_bg.style_profile_id = style_profile_id

        # db.get() is used in Phase 3 to re-fetch bg after SD call
        db.get = MagicMock(return_value=existing_bg or new_bg)

        with (
            p1,
            p2,
            p3,
            patch("services.stage.background_generator.resolve_style_context", return_value=style_ctx),
            patch("services.stage.background_generator.extract_style_loras", return_value=[]),
            patch(
                "services.stage.background_generator._prepare_bg_prompt",
                return_value={"prompt": "p", "negative": "n", "style_ctx": style_ctx, "style_loras": []},
            ),
            patch("services.stage.background_generator._generate_bg_from_prompt", return_value=b"img"),
            patch("services.stage.background_generator.AssetService", return_value=asset_svc),
            patch("services.stage.background_generator.Background", return_value=new_bg),
        ):
            results = asyncio.new_event_loop().run_until_complete(generate_location_backgrounds(1, db))

        return results

    def test_same_style_profile_cache_hit(self):
        """Same style_profile_id + existing image → status 'exists'."""
        bg = MagicMock()
        bg.id = 10
        bg.image_asset_id = 100
        bg.style_profile_id = 5

        results = self._run_generate_with_style(style_profile_id=5, existing_bg=bg)
        assert any(r["status"] == "exists" for r in results)

    def test_different_style_profile_cache_miss(self):
        """Different style_profile_id → cache miss → new generation."""
        results = self._run_generate_with_style(style_profile_id=7, existing_bg=None)
        assert any(r["status"] == "generated" for r in results)

    def test_regenerate_updates_style_profile_id(self):
        """regenerate_background() should update bg.style_profile_id."""
        import asyncio

        from services.stage.background_generator import regenerate_background

        bg = MagicMock()
        bg.id = 10
        bg.tags = ["cafe"]
        bg.style_profile_id = None

        db = MagicMock()
        db.query.return_value.options.return_value.filter.return_value.first.return_value = bg

        style_ctx = MagicMock()
        style_ctx.profile_id = 7
        style_ctx.default_positive = "masterpiece"
        style_ctx.sd_model_name = None

        asset_mock = MagicMock()
        asset_mock.id = 200
        asset_svc = MagicMock()
        asset_svc.save_background_image.return_value = asset_mock

        # After commit(), db.get() re-fetches the bg record
        db.get = MagicMock(return_value=bg)

        with (
            patch("services.stage.background_generator.resolve_style_context", return_value=style_ctx),
            patch("services.stage.background_generator.extract_style_loras", return_value=[]),
            patch(
                "services.stage.background_generator._prepare_bg_prompt",
                return_value={"prompt": "p", "negative": "n", "style_ctx": style_ctx, "style_loras": []},
            ),
            patch("services.stage.background_generator._generate_bg_from_prompt", return_value=b"fake_img"),
            patch("services.stage.background_generator.AssetService", return_value=asset_svc),
        ):
            result = asyncio.new_event_loop().run_until_complete(regenerate_background(1, "cafe", db))

        assert bg.style_profile_id == 7
        assert result["status"] == "regenerated"

    def test_null_style_profile_cache_hit(self):
        """NULL style_profile_id → existing bg with NULL style → cache hit."""
        bg = MagicMock()
        bg.id = 10
        bg.image_asset_id = 100
        bg.style_profile_id = None

        results = self._run_generate_with_style(style_profile_id=None, existing_bg=bg)
        assert any(r["status"] == "exists" for r in results)
