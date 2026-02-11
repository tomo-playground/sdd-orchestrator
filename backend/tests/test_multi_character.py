"""Tests for multi-character support (Phase 1-4)."""

from models.lora import LoRA
from models.scene import Scene
from models.storyboard import Storyboard

# ── Phase 1: Model defaults ──────────────────────────────────────────


class TestMultiCharacterModels:
    def test_lora_multi_character_default_false(self, db_session):
        """is_multi_character_capable defaults to False."""
        lora = LoRA(name="test_lora")
        db_session.add(lora)
        db_session.flush()

        assert lora.is_multi_character_capable is False
        assert lora.multi_char_weight_scale is None
        assert lora.multi_char_trigger_prompt is None

    def test_lora_multi_character_enabled(self, db_session):
        """LoRA with multi-character fields set correctly."""
        lora = LoRA(
            name="j_huiben",
            is_multi_character_capable=True,
            multi_char_weight_scale=0.75,
            multi_char_trigger_prompt="a boy and a girl",
        )
        db_session.add(lora)
        db_session.flush()

        fetched = db_session.query(LoRA).filter(LoRA.name == "j_huiben").first()
        assert fetched.is_multi_character_capable is True
        assert float(fetched.multi_char_weight_scale) == 0.75
        assert fetched.multi_char_trigger_prompt == "a boy and a girl"

    def test_scene_mode_default_single(self, db_session):
        """scene_mode defaults to 'single'."""
        sb = Storyboard(title="test", group_id=1)
        db_session.add(sb)
        db_session.flush()

        scene = Scene(storyboard_id=sb.id, order=0)
        db_session.add(scene)
        db_session.flush()

        assert scene.scene_mode == "single"

    def test_scene_mode_multi(self, db_session):
        """scene_mode can be set to 'multi'."""
        sb = Storyboard(title="test", group_id=1)
        db_session.add(sb)
        db_session.flush()

        scene = Scene(storyboard_id=sb.id, order=0, scene_mode="multi")
        db_session.add(scene)
        db_session.flush()

        fetched = db_session.query(Scene).filter(Scene.id == scene.id).first()
        assert fetched.scene_mode == "multi"


# ── Phase 2: Multi-character capability check ────────────────────────


class TestMultiCharacterCapable:
    def test_check_multi_character_capable_true(self, db_session):
        """LoRA with is_multi_character_capable=True -> returns True."""
        from models.character import Character
        from services.storyboard import _check_multi_character_capable

        lora = LoRA(name="multi_lora", is_multi_character_capable=True)
        db_session.add(lora)
        db_session.flush()

        char_a = Character(name="char_a", loras=[{"lora_id": lora.id, "weight": 1.0}])
        char_b = Character(name="char_b", loras=[])
        db_session.add_all([char_a, char_b])
        db_session.flush()

        result = _check_multi_character_capable(char_a.id, char_b.id, db_session)
        assert result is True

    def test_check_multi_character_capable_false(self, db_session):
        """LoRA without multi-character flag -> returns False."""
        from models.character import Character
        from services.storyboard import _check_multi_character_capable

        lora = LoRA(name="single_lora", is_multi_character_capable=False)
        db_session.add(lora)
        db_session.flush()

        char_a = Character(name="char_c", loras=[{"lora_id": lora.id, "weight": 1.0}])
        char_b = Character(name="char_d", loras=[])
        db_session.add_all([char_a, char_b])
        db_session.flush()

        result = _check_multi_character_capable(char_a.id, char_b.id, db_session)
        assert result is False

    def test_check_multi_character_capable_no_loras(self, db_session):
        """Characters with no LoRAs -> returns False."""
        from models.character import Character
        from services.storyboard import _check_multi_character_capable

        char_a = Character(name="char_e", loras=[])
        char_b = Character(name="char_f", loras=[])
        db_session.add_all([char_a, char_b])
        db_session.flush()

        result = _check_multi_character_capable(char_a.id, char_b.id, db_session)
        assert result is False


# ── Phase 2: Character action resolver multi scene ───────────────────


class TestCharacterActionResolverMulti:
    def test_multi_scene_mode_populates_both_characters(self, db_session):
        """scene_mode='multi' -> both characters get actions."""
        from models.tag import Tag
        from services.characters import auto_populate_character_actions

        tag = Tag(name="smile", default_layer=7)
        db_session.add(tag)
        db_session.flush()

        scenes = [
            {
                "scene_id": 1,
                "speaker": "A",
                "scene_mode": "multi",
                "context_tags": {"expression": ["smile"]},
            }
        ]
        result = auto_populate_character_actions(scenes, 100, 200, db_session)

        actions = result[0].get("character_actions", [])
        char_ids = {a["character_id"] for a in actions}
        assert 100 in char_ids, "Speaker A character should have actions"
        assert 200 in char_ids, "Speaker B character should have actions"

    def test_single_scene_mode_populates_only_speaker(self, db_session):
        """scene_mode='single' -> only speaking character gets actions."""
        from models.tag import Tag
        from services.characters import auto_populate_character_actions

        tag = Tag(name="angry", default_layer=7)
        db_session.add(tag)
        db_session.flush()

        scenes = [
            {
                "scene_id": 1,
                "speaker": "A",
                "scene_mode": "single",
                "context_tags": {"expression": ["angry"]},
            }
        ]
        result = auto_populate_character_actions(scenes, 100, 200, db_session)

        actions = result[0].get("character_actions", [])
        char_ids = {a["character_id"] for a in actions}
        assert 100 in char_ids, "Speaker A should have actions"
        assert 200 not in char_ids, "Speaker B should NOT have actions in single mode"


# ── Phase 3: MultiCharacterComposer ─────────────────────────────────


def _make_char_with_tags(db, name, gender, tag_defs, loras=None, prompt_mode="auto"):
    """Helper: create Character with CharacterTag rows.

    tag_defs: list of (tag_name, layer, weight)
    """
    from models.associations import CharacterTag
    from models.character import Character
    from models.tag import Tag

    char = Character(name=name, gender=gender, loras=loras, prompt_mode=prompt_mode)
    db.add(char)
    db.flush()

    for tag_name, layer, weight in tag_defs:
        tag = db.query(Tag).filter(Tag.name == tag_name).first()
        if not tag:
            tag = Tag(name=tag_name, default_layer=layer)
            db.add(tag)
            db.flush()
        ct = CharacterTag(character_id=char.id, tag_id=tag.id, weight=weight)
        db.add(ct)

    db.flush()
    db.refresh(char)
    return char


class TestMultiCharacterComposer:
    """Phase 3: MultiCharacterComposer unit tests."""

    def test_subject_layer_mixed_gender(self, db_session):
        """male + female -> '1boy, 1girl' in subject."""
        from services.prompt.v3_composition import V3PromptBuilder
        from services.prompt.v3_multi_character import MultiCharacterComposer

        char_a = _make_char_with_tags(db_session, "hero", "male", [("red_hair", 2, 1.0)])
        char_b = _make_char_with_tags(db_session, "heroine", "female", [("blue_hair", 2, 1.0)])

        builder = V3PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(char_a, char_b, ["classroom"])

        assert "1boy" in result
        assert "1girl" in result

    def test_subject_layer_same_gender(self, db_session):
        """female + female -> '2girls' in subject."""
        from services.prompt.v3_composition import V3PromptBuilder
        from services.prompt.v3_multi_character import MultiCharacterComposer

        char_a = _make_char_with_tags(db_session, "sister_a", "female", [("red_hair", 2, 1.0)])
        char_b = _make_char_with_tags(db_session, "sister_b", "female", [("blue_hair", 2, 1.0)])

        builder = V3PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(char_a, char_b, ["classroom"])

        assert "2girls" in result
        assert "1boy" not in result

    def test_identity_tags_both_preserved(self, db_session):
        """Both characters' identity tags appear in output."""
        from services.prompt.v3_composition import V3PromptBuilder
        from services.prompt.v3_multi_character import MultiCharacterComposer

        char_a = _make_char_with_tags(db_session, "char_a", "male", [("red_hair", 2, 1.0)])
        char_b = _make_char_with_tags(db_session, "char_b", "female", [("blue_hair", 2, 1.0)])

        builder = V3PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(char_a, char_b, ["classroom"])

        assert "red_hair" in result
        assert "blue_hair" in result

    def test_lora_dedup_same_style(self, db_session):
        """Shared style LoRA only injected once."""
        from services.prompt.v3_composition import V3PromptBuilder
        from services.prompt.v3_multi_character import MultiCharacterComposer

        char_a = _make_char_with_tags(db_session, "a1", "male", [("red_hair", 2, 1.0)])
        char_b = _make_char_with_tags(db_session, "b1", "female", [("blue_hair", 2, 1.0)])

        builder = V3PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        style_loras = [
            {"name": "flat_color", "weight": 0.7, "trigger_words": []},
            {"name": "flat_color", "weight": 0.7, "trigger_words": []},
        ]
        result = composer.compose(char_a, char_b, ["classroom"], style_loras=style_loras)

        assert result.count("<lora:flat_color:") == 1

    def test_lora_weight_scale_applied(self, db_session):
        """multi_char_weight_scale reduces LoRA weight."""
        from services.prompt.v3_composition import V3PromptBuilder
        from services.prompt.v3_multi_character import MultiCharacterComposer

        lora = LoRA(
            name="char_lora_a",
            lora_type="character",
            default_weight=1.0,
            multi_char_weight_scale=0.75,
        )
        db_session.add(lora)
        db_session.flush()

        char_a = _make_char_with_tags(
            db_session,
            "scaled_char",
            "male",
            [("red_hair", 2, 1.0)],
            loras=[{"lora_id": lora.id, "weight": 1.0}],
        )
        char_b = _make_char_with_tags(db_session, "other_char", "female", [("blue_hair", 2, 1.0)])

        builder = V3PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(char_a, char_b, ["classroom"])

        # 1.0 * 0.75 = 0.75
        assert "<lora:char_lora_a:0.75>" in result

    def test_trigger_prompt_used_when_available(self, db_session):
        """LoRA multi_char_trigger_prompt used in subject."""
        from services.prompt.v3_composition import V3PromptBuilder
        from services.prompt.v3_multi_character import MultiCharacterComposer

        lora = LoRA(
            name="j_huiben_test",
            lora_type="character",
            default_weight=0.8,
            is_multi_character_capable=True,
            multi_char_trigger_prompt="a boy and a girl",
        )
        db_session.add(lora)
        db_session.flush()

        char_a = _make_char_with_tags(
            db_session,
            "trigger_char",
            "male",
            [("red_hair", 2, 1.0)],
            loras=[{"lora_id": lora.id, "weight": 0.8}],
        )
        char_b = _make_char_with_tags(db_session, "trigger_char_b", "female", [("blue_hair", 2, 1.0)])

        builder = V3PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(char_a, char_b, ["classroom"])

        assert "a boy and a girl" in result
        assert "1boy, 1girl" not in result

    def test_fallback_to_gender_tags_without_trigger(self, db_session):
        """No trigger prompt -> fallback to gender tags."""
        from services.prompt.v3_composition import V3PromptBuilder
        from services.prompt.v3_multi_character import MultiCharacterComposer

        char_a = _make_char_with_tags(db_session, "no_trigger_a", "male", [("red_hair", 2, 1.0)])
        char_b = _make_char_with_tags(db_session, "no_trigger_b", "female", [("blue_hair", 2, 1.0)])

        builder = V3PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(char_a, char_b, ["classroom"])

        assert "1boy, 1girl" in result

    def test_camera_prefers_wide_framing(self, db_session):
        """Multi-char prefer wide_shot/upper_body over close-up."""
        from services.prompt.v3_composition import V3PromptBuilder
        from services.prompt.v3_multi_character import MultiCharacterComposer

        char_a = _make_char_with_tags(db_session, "cam_a", "male", [("red_hair", 2, 1.0)])
        char_b = _make_char_with_tags(db_session, "cam_b", "female", [("blue_hair", 2, 1.0)])

        builder = V3PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(char_a, char_b, ["close-up", "classroom"])

        assert "wide_shot" in result
        assert "close-up" not in result

    def test_single_char_unchanged(self, db_session):
        """compose_for_character() not affected (regression)."""
        from services.prompt.v3_composition import V3PromptBuilder

        char = _make_char_with_tags(db_session, "solo_char", "female", [("red_hair", 2, 1.0)])

        builder = V3PromptBuilder(db_session)
        result = builder.compose_for_character(char.id, ["classroom"], character=char)

        assert "red_hair" in result
        assert "2girls" not in result
        assert "1boy" not in result


# ── Phase 4: _resolve_effective_character_b_id ────────────────────────


class TestResolveEffectiveCharacterBId:
    """Phase 4: Backend scene_mode gating for character_b_id."""

    def test_multi_scene_returns_character_b_id(self, db_session):
        """scene_mode='multi' → returns character_b_id."""
        from schemas import SceneGenerateRequest
        from services.generation import _resolve_effective_character_b_id

        sb = Storyboard(title="test", group_id=1)
        db_session.add(sb)
        db_session.flush()

        scene = Scene(storyboard_id=sb.id, order=0, scene_mode="multi")
        db_session.add(scene)
        db_session.flush()

        request = SceneGenerateRequest(
            prompt="test",
            scene_id=scene.id,
            character_id=1,
            character_b_id=2,
        )
        result = _resolve_effective_character_b_id(request, db_session)
        assert result == 2

    def test_single_scene_ignores_character_b_id(self, db_session):
        """scene_mode='single' → returns None even with character_b_id."""
        from schemas import SceneGenerateRequest
        from services.generation import _resolve_effective_character_b_id

        sb = Storyboard(title="test", group_id=1)
        db_session.add(sb)
        db_session.flush()

        scene = Scene(storyboard_id=sb.id, order=0, scene_mode="single")
        db_session.add(scene)
        db_session.flush()

        request = SceneGenerateRequest(
            prompt="test",
            scene_id=scene.id,
            character_id=1,
            character_b_id=2,
        )
        result = _resolve_effective_character_b_id(request, db_session)
        assert result is None

    def test_no_scene_id_returns_none(self, db_session):
        """No scene_id → returns None."""
        from schemas import SceneGenerateRequest
        from services.generation import _resolve_effective_character_b_id

        request = SceneGenerateRequest(
            prompt="test",
            character_id=1,
            character_b_id=2,
        )
        result = _resolve_effective_character_b_id(request, db_session)
        assert result is None

    def test_no_character_b_id_returns_none(self, db_session):
        """No character_b_id → returns None."""
        from schemas import SceneGenerateRequest
        from services.generation import _resolve_effective_character_b_id

        request = SceneGenerateRequest(
            prompt="test",
            scene_id=1,
            character_id=1,
        )
        result = _resolve_effective_character_b_id(request, db_session)
        assert result is None
