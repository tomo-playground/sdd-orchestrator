"""Tests for multi-character support (Phase 30-O)."""

from models.lora import LoRA
from models.scene import Scene
from models.storyboard import Storyboard

# ── Scene model defaults ─────────────────────────────────────────────


class TestMultiCharacterModels:
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


# ── Character action resolver multi scene ─────────────────────────────


class TestCharacterActionResolverMulti:
    def test_multi_scene_mode_populates_both_characters(self, db_session):
        """scene_mode='multi' -> both characters get actions."""
        from models.tag import Tag
        from services.characters import auto_populate_character_actions

        tag = Tag(name="smile", default_layer=7, category="scene", group_name="expression")
        db_session.add(tag)
        db_session.flush()

        scenes = [
            {
                "scene_id": 1,
                "speaker": "speaker_1",
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

        tag = Tag(name="angry", default_layer=7, category="scene", group_name="expression")
        db_session.add(tag)
        db_session.flush()

        scenes = [
            {
                "scene_id": 1,
                "speaker": "speaker_1",
                "scene_mode": "single",
                "context_tags": {"expression": ["angry"]},
            }
        ]
        result = auto_populate_character_actions(scenes, 100, 200, db_session)

        actions = result[0].get("character_actions", [])
        char_ids = {a["character_id"] for a in actions}
        assert 100 in char_ids, "Speaker A should have actions"
        assert 200 not in char_ids, "Speaker B should NOT have actions in single mode"


# ── MultiCharacterComposer ───────────────────────────────────────────


def _make_char_with_tags(db, name, gender, tag_defs, loras=None):
    """Helper: create Character with CharacterTag rows.

    tag_defs: list of (tag_name, layer, weight)
    """
    from models.associations import CharacterTag
    from models.character import Character
    from models.tag import Tag

    char = Character(name=name, gender=gender, group_id=1, loras=loras)
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
    """MultiCharacterComposer unit tests."""

    def test_subject_layer_mixed_gender(self, db_session):
        """male + female -> '1boy, 1girl' in subject."""
        from services.prompt.composition import PromptBuilder
        from services.prompt.multi_character import MultiCharacterComposer

        char_a = _make_char_with_tags(db_session, "hero", "male", [("red_hair", 2, 1.0)])
        char_b = _make_char_with_tags(db_session, "heroine", "female", [("blue_hair", 2, 1.0)])

        builder = PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(char_a, char_b, ["classroom"])

        assert "1boy" in result
        assert "1girl" in result

    def test_subject_layer_same_gender(self, db_session):
        """female + female -> '2girls' in subject."""
        from services.prompt.composition import PromptBuilder
        from services.prompt.multi_character import MultiCharacterComposer

        char_a = _make_char_with_tags(db_session, "sister_a", "female", [("red_hair", 2, 1.0)])
        char_b = _make_char_with_tags(db_session, "sister_b", "female", [("blue_hair", 2, 1.0)])

        builder = PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(char_a, char_b, ["classroom"])

        assert "2girls" in result
        assert "1boy" not in result

    def test_identity_tags_both_preserved(self, db_session):
        """Both characters' identity tags appear in output."""
        from services.prompt.composition import PromptBuilder
        from services.prompt.multi_character import MultiCharacterComposer

        char_a = _make_char_with_tags(db_session, "char_a", "male", [("red_hair", 2, 1.0)])
        char_b = _make_char_with_tags(db_session, "char_b", "female", [("blue_hair", 2, 1.0)])

        builder = PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(char_a, char_b, ["classroom"])

        assert "red_hair" in result
        assert "blue_hair" in result

    def test_break_structure(self, db_session):
        """BREAK 토큰으로 공통/CharA/CharB 분리."""
        from services.prompt.composition import PromptBuilder
        from services.prompt.multi_character import MultiCharacterComposer

        char_a = _make_char_with_tags(db_session, "brk_a", "male", [("red_hair", 2, 1.0)])
        char_b = _make_char_with_tags(db_session, "brk_b", "female", [("blue_hair", 2, 1.0)])

        builder = PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(char_a, char_b, ["classroom"])

        sections = result.split("\nBREAK\n")
        assert len(sections) == 3, f"Expected 3 BREAK sections, got {len(sections)}"
        # 공통: quality + subject + scene
        assert "1boy" in sections[0]
        # 개별 캐릭터
        assert "red_hair" in sections[1]
        assert "blue_hair" in sections[2]

    def test_per_break_dedup(self, db_session):
        """Per-BREAK dedup: 양쪽 캐릭터에 같은 태그가 있으면 각 섹션에 유지."""
        from services.prompt.composition import PromptBuilder
        from services.prompt.multi_character import MultiCharacterComposer

        char_a = _make_char_with_tags(db_session, "dd_a", "male", [("school_uniform", 4, 1.0)])
        char_b = _make_char_with_tags(db_session, "dd_b", "female", [("school_uniform", 4, 1.0)])

        builder = PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(char_a, char_b, ["classroom"])

        sections = result.split("\nBREAK\n")
        # 각 캐릭터 섹션에 school_uniform 유지 (per-BREAK dedup)
        assert "school_uniform" in sections[1]
        assert "school_uniform" in sections[2]

    def test_banned_tags_solo_removed(self, db_session):
        """solo 태그가 멀티캐릭터 씬에서 제거됨."""
        from models.associations import CharacterTag
        from models.tag import Tag
        from services.prompt.composition import PromptBuilder
        from services.prompt.multi_character import MultiCharacterComposer

        # solo 태그를 가진 캐릭터
        char_a = _make_char_with_tags(db_session, "solo_a", "male", [("red_hair", 2, 1.0)])
        solo_tag = db_session.query(Tag).filter(Tag.name == "solo").first()
        if not solo_tag:
            solo_tag = Tag(name="solo", default_layer=1)
            db_session.add(solo_tag)
            db_session.flush()
        ct = CharacterTag(character_id=char_a.id, tag_id=solo_tag.id, weight=1.0)
        db_session.add(ct)
        db_session.flush()
        db_session.refresh(char_a)

        char_b = _make_char_with_tags(db_session, "solo_b", "female", [("blue_hair", 2, 1.0)])

        builder = PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(char_a, char_b, ["classroom"])

        # solo 는 BREAK 어디에도 없어야 함
        for section in result.split("\nBREAK\n"):
            tokens = [t.strip().lower() for t in section.split(",")]
            assert "solo" not in tokens, f"solo should be removed, found in: {section}"

    def test_lora_dedup_same_style(self, db_session):
        """Shared style LoRA only injected once."""
        from services.prompt.composition import PromptBuilder
        from services.prompt.multi_character import MultiCharacterComposer

        char_a = _make_char_with_tags(db_session, "a1", "male", [("red_hair", 2, 1.0)])
        char_b = _make_char_with_tags(db_session, "b1", "female", [("blue_hair", 2, 1.0)])

        builder = PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        style_loras = [
            {"name": "flat_color", "weight": 0.7, "trigger_words": []},
            {"name": "flat_color", "weight": 0.7, "trigger_words": []},
        ]
        result = composer.compose(char_a, char_b, ["classroom"], style_loras=style_loras)

        assert result.count("<lora:flat_color:") == 1

    def test_scene_character_lora_scale_applied(self, db_session):
        """SCENE_CHARACTER_LORA_SCALE 적용으로 LoRA weight 감소."""
        from config import SCENE_CHARACTER_LORA_SCALE
        from services.prompt.composition import PromptBuilder
        from services.prompt.multi_character import MultiCharacterComposer

        lora = LoRA(name="char_lora_scaled", lora_type="character", default_weight=1.0)
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

        builder = PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(char_a, char_b, ["classroom"])

        expected_weight = round(1.0 * SCENE_CHARACTER_LORA_SCALE, 2)
        assert f"<lora:char_lora_scaled:{expected_weight}>" in result

    def test_lora_weight_cap_total(self, db_session):
        """총 LoRA weight > MULTI_CHAR_MAX_TOTAL_LORA_WEIGHT 시 비례 축소."""
        from config import MULTI_CHAR_MAX_TOTAL_LORA_WEIGHT, SCENE_CHARACTER_LORA_SCALE
        from services.prompt.composition import PromptBuilder
        from services.prompt.multi_character import MultiCharacterComposer

        # 높은 weight LoRA 2개 생성
        lora_a = LoRA(name="heavy_lora_a", lora_type="character", default_weight=1.0)
        lora_b = LoRA(name="heavy_lora_b", lora_type="character", default_weight=1.0)
        db_session.add_all([lora_a, lora_b])
        db_session.flush()

        # 높은 weight 로 설정 → 스케일 후에도 합산이 상한 초과하도록
        high_w = round(MULTI_CHAR_MAX_TOTAL_LORA_WEIGHT / SCENE_CHARACTER_LORA_SCALE + 1.0, 2)
        char_a = _make_char_with_tags(
            db_session,
            "heavy_a",
            "male",
            [("red_hair", 2, 1.0)],
            loras=[{"lora_id": lora_a.id, "weight": high_w}],
        )
        char_b = _make_char_with_tags(
            db_session,
            "heavy_b",
            "female",
            [("blue_hair", 2, 1.0)],
            loras=[{"lora_id": lora_b.id, "weight": high_w}],
        )

        builder = PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(char_a, char_b, ["classroom"])

        # LoRA weight 합산이 상한 이하로 축소되었는지 확인
        import re

        weights = [float(m) for m in re.findall(r"<lora:\w+:([\d.]+)>", result)]
        assert len(weights) == 2, f"Expected 2 LoRAs, got {len(weights)}"
        assert sum(weights) <= MULTI_CHAR_MAX_TOTAL_LORA_WEIGHT + 0.01

    def test_interaction_tag_injected(self, db_session):
        """interaction 태그 없으면 facing_another 자동 주입."""
        from services.prompt.composition import PromptBuilder
        from services.prompt.multi_character import MultiCharacterComposer

        char_a = _make_char_with_tags(db_session, "int_a", "male", [("red_hair", 2, 1.0)])
        char_b = _make_char_with_tags(db_session, "int_b", "female", [("blue_hair", 2, 1.0)])

        builder = PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        # scene_tags에 interaction 태그 없음
        result = composer.compose(char_a, char_b, ["classroom"])

        assert "facing_another" in result

    def test_interaction_tag_not_injected_when_present(self, db_session):
        """이미 interaction 태그가 scene_tags에 있으면 facing_another 추가 안 함."""
        from services.prompt.composition import PromptBuilder
        from services.prompt.multi_character import MultiCharacterComposer

        char_a = _make_char_with_tags(db_session, "int2_a", "male", [("red_hair", 2, 1.0)])
        char_b = _make_char_with_tags(db_session, "int2_b", "female", [("blue_hair", 2, 1.0)])

        builder = PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        # eye_contact 은 interaction 태그 → facing_another 추가 불필요
        result = composer.compose(char_a, char_b, ["eye_contact", "classroom"])

        assert "facing_another" not in result

    def test_camera_prefers_wide_framing(self, db_session):
        """Multi-char prefer wide_shot over close-up."""
        from services.prompt.composition import PromptBuilder
        from services.prompt.multi_character import MultiCharacterComposer

        char_a = _make_char_with_tags(db_session, "cam_a", "male", [("red_hair", 2, 1.0)])
        char_b = _make_char_with_tags(db_session, "cam_b", "female", [("blue_hair", 2, 1.0)])

        builder = PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(char_a, char_b, ["close-up", "classroom"])

        assert "wide_shot" in result
        assert "close-up" not in result

    def test_single_char_unchanged(self, db_session):
        """compose_for_character() not affected (regression)."""
        from services.prompt.composition import PromptBuilder

        char = _make_char_with_tags(db_session, "solo_char", "female", [("red_hair", 2, 1.0)])

        builder = PromptBuilder(db_session)
        result = builder.compose_for_character(char.id, ["classroom"], character=char)

        assert "red_hair" in result
        assert "2girls" not in result
        assert "1boy" not in result

    def test_gender_only_subject_no_trigger_prompt(self, db_session):
        """trigger_prompt 제거 후 성별 기반 subject만 사용."""
        from services.prompt.composition import PromptBuilder
        from services.prompt.multi_character import MultiCharacterComposer

        char_a = _make_char_with_tags(db_session, "gen_a", "male", [("red_hair", 2, 1.0)])
        char_b = _make_char_with_tags(db_session, "gen_b", "female", [("blue_hair", 2, 1.0)])

        builder = PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(char_a, char_b, ["classroom"])

        # 공통 섹션에 성별 태그
        common_section = result.split("\nBREAK\n")[0]
        assert "1boy, 1girl" in common_section


# ── _resolve_effective_character_b_id ─────────────────────────────────


class TestResolveEffectiveCharacterBId:
    """Backend scene_mode gating for character_b_id."""

    def test_multi_scene_returns_character_b_id(self, db_session):
        """scene_mode='multi' -> returns character_b_id."""
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
        effective_b_id, warnings = _resolve_effective_character_b_id(request, db_session)
        assert effective_b_id == 2
        assert warnings == []

    def test_single_scene_ignores_character_b_id(self, db_session):
        """scene_mode='single' -> returns None even with character_b_id."""
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
        effective_b_id, warnings = _resolve_effective_character_b_id(request, db_session)
        assert effective_b_id is None
        assert warnings == []

    def test_no_scene_id_returns_none(self, db_session):
        """No scene_id -> returns None."""
        from schemas import SceneGenerateRequest
        from services.generation import _resolve_effective_character_b_id

        request = SceneGenerateRequest(
            prompt="test",
            character_id=1,
            character_b_id=2,
        )
        effective_b_id, warnings = _resolve_effective_character_b_id(request, db_session)
        assert effective_b_id is None
        assert warnings == []

    def test_no_character_b_id_returns_none(self, db_session):
        """scene_mode=multi + no character_b_id -> None + warning."""
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
        )
        effective_b_id, warnings = _resolve_effective_character_b_id(request, db_session)
        assert effective_b_id is None
        assert len(warnings) == 1
        assert "single" in warnings[0]

    def test_same_character_a_b_returns_none(self, db_session):
        """character_b_id == character_id -> returns None (동일 캐릭터 방어)."""
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
            character_id=5,
            character_b_id=5,
        )
        effective_b_id, warnings = _resolve_effective_character_b_id(request, db_session)
        assert effective_b_id is None


# ── Quality tag compatibility ─────────────────────────────────────────


class TestMultiCharacterComposerQuality:
    """MultiCharacterComposer should not hardcode anime quality tags."""

    def test_quality_uses_fallback_when_no_style(self, db_session):
        """No style profile -> fallback quality tags (masterpiece, best_quality)."""
        from services.prompt.composition import PromptBuilder
        from services.prompt.multi_character import MultiCharacterComposer

        char_a = _make_char_with_tags(db_session, "q_a", "male", [("red_hair", 2, 1.0)])
        char_b = _make_char_with_tags(db_session, "q_b", "female", [("blue_hair", 2, 1.0)])

        builder = PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(char_a, char_b, ["classroom"])

        assert "masterpiece" in result
        assert "best_quality" in result

    def test_quality_respects_style_profile_tags(self, db_session):
        """With realistic quality_tags -> no anime tags injected."""
        from services.prompt.composition import PromptBuilder
        from services.prompt.multi_character import MultiCharacterComposer

        char_a = _make_char_with_tags(db_session, "r_a", "male", [("red_hair", 2, 1.0)])
        char_b = _make_char_with_tags(db_session, "r_b", "female", [("blue_hair", 2, 1.0)])

        builder = PromptBuilder(db_session)
        composer = MultiCharacterComposer(builder)
        result = composer.compose(
            char_a,
            char_b,
            ["classroom"],
            quality_tags=["photorealistic", "raw_photo"],
        )

        assert "photorealistic" in result
        assert "raw_photo" in result
        assert "masterpiece" not in result
        assert "best_quality" not in result
