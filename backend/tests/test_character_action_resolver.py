"""Tests for character_action_resolver and resolve_action_tag_ids."""

from models.tag import Tag
from schemas import SceneActionSave
from services.characters import auto_populate_character_actions, extract_actions_from_context_tags
from services.storyboard import resolve_action_tag_ids

# ── Helpers ──────────────────────────────────────────────────────────


def _seed_tags(db_session, names_layers) -> dict[str, int]:
    """Insert tags into DB and return {name: id} mapping.

    Each item is (name, layer) or (name, layer, group_name).
    Default group_name is 'expression'.
    """
    result: dict[str, int] = {}
    tags: list[tuple[str, Tag]] = []
    for item in names_layers:
        if len(item) == 3:
            name, layer, group_name = item
        else:
            name, layer = item
            group_name = "expression"
        tag = Tag(name=name, default_layer=layer, category="scene", group_name=group_name)
        db_session.add(tag)
        tags.append((name, tag))
    db_session.flush()
    for name, tag in tags:
        result[name] = tag.id
    return result


def _scene(speaker: str, context_tags: dict | None = None, **extra) -> dict:
    """Build a minimal scene dict."""
    return {"speaker": speaker, "context_tags": context_tags, **extra}


# ── Tests ────────────────────────────────────────────────────────────


class TestBasicPopulation:
    """Core speaker→character mapping and tag resolution."""

    def test_speaker_a_maps_to_character_id(self, db_session):
        tag_ids = _seed_tags(db_session, [("smile", 7)])
        scenes = [_scene("speaker_1", {"expression": ["smile"]})]

        result = auto_populate_character_actions(scenes, character_id=100, character_b_id=None, db=db_session)

        actions = result[0]["character_actions"]
        assert len(actions) == 1
        assert actions[0]["character_id"] == 100
        assert actions[0]["tag_id"] == tag_ids["smile"]
        assert actions[0]["weight"] == 1.0

    def test_speaker_b_maps_to_character_b_id(self, db_session):
        _seed_tags(db_session, [("angry", 7)])
        scenes = [_scene("speaker_2", {"expression": ["angry"]})]

        result = auto_populate_character_actions(scenes, character_id=100, character_b_id=200, db=db_session)

        actions = result[0]["character_actions"]
        assert actions[0]["character_id"] == 200

    def test_narrator_skipped(self, db_session):
        """Narrator scenes should not get character_actions."""
        _seed_tags(db_session, [("smile", 7)])
        scenes = [_scene("narrator", {"expression": ["smile"]})]

        result = auto_populate_character_actions(scenes, character_id=100, character_b_id=200, db=db_session)

        assert "character_actions" not in result[0]


class TestContextTagCategories:
    """All _ACTION_GROUPS (expression, gaze, pose, action) are extracted."""

    def test_expression_list(self, db_session):
        _seed_tags(db_session, [("smile", 7), ("blush", 7)])
        scenes = [_scene("speaker_1", {"expression": ["smile", "blush"]})]

        result = auto_populate_character_actions(scenes, character_id=1, character_b_id=None, db=db_session)

        names = {a["tag_id"] for a in result[0]["character_actions"]}
        assert len(names) == 2

    def test_gaze_string(self, db_session):
        """gaze is a single string in context_tags, not a list."""
        _seed_tags(db_session, [("looking_at_viewer", 7, "gaze")])
        scenes = [_scene("speaker_1", {"gaze": "looking_at_viewer"})]

        result = auto_populate_character_actions(scenes, character_id=1, character_b_id=None, db=db_session)

        assert len(result[0]["character_actions"]) == 1

    def test_pose_list(self, db_session):
        _seed_tags(db_session, [("standing", 8, "pose")])
        scenes = [_scene("speaker_1", {"pose": ["standing"]})]

        result = auto_populate_character_actions(scenes, character_id=1, character_b_id=None, db=db_session)

        assert result[0]["character_actions"][0]["tag_id"] is not None

    def test_action_list(self, db_session):
        _seed_tags(db_session, [("holding_sword", 8, "action_hand")])
        scenes = [_scene("speaker_1", {"action": ["holding_sword"]})]

        result = auto_populate_character_actions(scenes, character_id=1, character_b_id=None, db=db_session)

        assert len(result[0]["character_actions"]) == 1

    def test_non_action_categories_ignored(self, db_session):
        """camera, environment, mood etc. should NOT produce character_actions."""
        _seed_tags(db_session, [("close-up", 5), ("night", 3)])
        scenes = [_scene("speaker_1", {"camera": ["close-up"], "environment": ["night"]})]

        result = auto_populate_character_actions(scenes, character_id=1, character_b_id=None, db=db_session)

        assert "character_actions" not in result[0]

    def test_multiple_categories_combined(self, db_session):
        """Tags from expression + gaze + pose should all be included."""
        _seed_tags(db_session, [("smile", 7), ("looking_away", 7, "gaze"), ("sitting", 8, "pose")])
        scenes = [
            _scene("speaker_1", {"expression": ["smile"], "gaze": "looking_away", "pose": ["sitting"]}),
        ]

        result = auto_populate_character_actions(scenes, character_id=1, character_b_id=None, db=db_session)

        assert len(result[0]["character_actions"]) == 3


class TestEdgeCases:
    """Empty/missing data, pre-existing actions, whitespace, etc."""

    def test_no_characters_returns_unchanged(self, db_session):
        scenes = [_scene("speaker_1", {"expression": ["smile"]})]

        result = auto_populate_character_actions(scenes, character_id=None, character_b_id=None, db=db_session)

        assert "character_actions" not in result[0]

    def test_no_context_tags_returns_unchanged(self, db_session):
        scenes = [_scene("speaker_1", None)]

        result = auto_populate_character_actions(scenes, character_id=1, character_b_id=None, db=db_session)

        assert "character_actions" not in result[0]

    def test_empty_context_tags(self, db_session):
        scenes = [_scene("speaker_1", {})]

        result = auto_populate_character_actions(scenes, character_id=1, character_b_id=None, db=db_session)

        assert "character_actions" not in result[0]

    def test_tag_not_in_db_skipped(self, db_session):
        """Tags not found in DB should be silently skipped."""
        scenes = [_scene("speaker_1", {"expression": ["nonexistent_tag_xyz"]})]

        result = auto_populate_character_actions(scenes, character_id=1, character_b_id=None, db=db_session)

        assert "character_actions" not in result[0]

    def test_existing_actions_preserved(self, db_session):
        """Scenes with pre-existing character_actions should not be overwritten."""
        _seed_tags(db_session, [("smile", 7)])
        existing = [{"character_id": 999, "tag_id": 1, "weight": 0.5}]
        scenes = [_scene("speaker_1", {"expression": ["smile"]}, character_actions=existing)]

        result = auto_populate_character_actions(scenes, character_id=1, character_b_id=None, db=db_session)

        assert result[0]["character_actions"] is existing

    def test_whitespace_tag_names_trimmed(self, db_session):
        _seed_tags(db_session, [("smile", 7)])
        scenes = [_scene("speaker_1", {"expression": ["  smile  "]})]

        result = auto_populate_character_actions(scenes, character_id=1, character_b_id=None, db=db_session)

        assert len(result[0]["character_actions"]) == 1

    def test_empty_string_tag_skipped(self, db_session):
        _seed_tags(db_session, [("smile", 7)])
        scenes = [_scene("speaker_1", {"expression": ["", "  ", "smile"]})]

        result = auto_populate_character_actions(scenes, character_id=1, character_b_id=None, db=db_session)

        assert len(result[0]["character_actions"]) == 1


class TestMultiScene:
    """Multiple scenes with alternating speakers (typical dialogue storyboard)."""

    def test_dialogue_alternating_speakers(self, db_session):
        _seed_tags(db_session, [("smile", 7), ("angry", 7), ("looking_at_viewer", 7, "gaze")])
        scenes = [
            _scene("speaker_1", {"expression": ["smile"], "gaze": "looking_at_viewer"}),
            _scene("speaker_2", {"expression": ["angry"]}),
            _scene("narrator", {"expression": ["smile"]}),
            _scene("speaker_1", {"expression": ["angry"]}),
        ]

        result = auto_populate_character_actions(
            scenes,
            character_id=10,
            character_b_id=20,
            db=db_session,
        )

        # Scene 0: Speaker A → char 10, 2 actions
        assert len(result[0]["character_actions"]) == 2
        assert all(a["character_id"] == 10 for a in result[0]["character_actions"])

        # Scene 1: Speaker B → char 20, 1 action
        assert len(result[1]["character_actions"]) == 1
        assert result[1]["character_actions"][0]["character_id"] == 20

        # Scene 2: Narrator → no actions
        assert "character_actions" not in result[2]

        # Scene 3: Speaker A → char 10, 1 action
        assert len(result[3]["character_actions"]) == 1
        assert result[3]["character_actions"][0]["character_id"] == 10

    def test_mutates_original_list(self, db_session):
        """Function modifies scenes in-place and returns the same list object."""
        _seed_tags(db_session, [("smile", 7)])
        scenes = [_scene("speaker_1", {"expression": ["smile"]})]

        result = auto_populate_character_actions(scenes, character_id=1, character_b_id=None, db=db_session)

        assert result is scenes


# ── resolve_action_tag_ids Tests ─────────────────────────────────────


class TestResolveActionTagIds:
    """Tests for storyboard.resolve_action_tag_ids (tag_name → tag_id)."""

    def test_resolves_tag_id_zero_by_name(self, db_session):
        """tag_id=0 + tag_name → resolved to actual tag_id."""
        tag_ids = _seed_tags(db_session, [("smile", 7)])
        actions = [SceneActionSave(character_id=1, tag_id=0, tag_name="smile", weight=1.0)]

        resolved = resolve_action_tag_ids(actions, db_session)

        assert len(resolved) == 1
        assert resolved[0].tag_id == tag_ids["smile"]
        assert resolved[0].character_id == 1
        assert resolved[0].weight == 1.0

    def test_known_tag_id_unchanged(self, db_session):
        """tag_id > 0 should pass through unchanged."""
        actions = [SceneActionSave(character_id=1, tag_id=42, weight=0.8)]

        resolved = resolve_action_tag_ids(actions, db_session)

        assert len(resolved) == 1
        assert resolved[0].tag_id == 42

    def test_unknown_tag_name_dropped(self, db_session):
        """tag_id=0 + unknown tag_name → entry dropped."""
        actions = [SceneActionSave(character_id=1, tag_id=0, tag_name="nonexistent_xyz")]

        resolved = resolve_action_tag_ids(actions, db_session)

        assert len(resolved) == 0

    def test_mixed_resolved_and_existing(self, db_session):
        """Mix of tag_id=0 (needs resolve) and tag_id>0 (pass-through)."""
        tag_ids = _seed_tags(db_session, [("angry", 7)])
        actions = [
            SceneActionSave(character_id=1, tag_id=99, weight=1.0),
            SceneActionSave(character_id=1, tag_id=0, tag_name="angry", weight=0.5),
            SceneActionSave(character_id=2, tag_id=0, tag_name="missing_tag"),
        ]

        resolved = resolve_action_tag_ids(actions, db_session)

        assert len(resolved) == 2
        assert resolved[0].tag_id == 99  # pass-through
        assert resolved[1].tag_id == tag_ids["angry"]  # resolved
        assert resolved[1].weight == 0.5

    def test_no_unresolved_returns_same(self, db_session):
        """No tag_id=0 entries → return as-is without DB query."""
        actions = [SceneActionSave(character_id=1, tag_id=10)]

        resolved = resolve_action_tag_ids(actions, db_session)

        assert len(resolved) == 1
        assert resolved[0].tag_id == 10

    def test_empty_list(self, db_session):
        resolved = resolve_action_tag_ids([], db_session)
        assert resolved == []


# ── extract_actions_from_context_tags Tests ──────────────────────────


class TestExtractActionsFromContextTags:
    """Tests for single-scene context_tags → character_actions extraction."""

    def test_extracts_expression_and_pose(self, db_session):
        tag_ids = _seed_tags(db_session, [("smile", 7), ("standing", 8, "pose")])
        ctx = {"expression": ["smile"], "pose": ["standing"]}

        actions = extract_actions_from_context_tags(ctx, character_id=10, db=db_session)

        assert actions is not None
        assert len(actions) == 2
        assert all(a["character_id"] == 10 for a in actions)
        ids = {a["tag_id"] for a in actions}
        assert ids == {tag_ids["smile"], tag_ids["standing"]}

    def test_gaze_string_extracted(self, db_session):
        _seed_tags(db_session, [("looking_at_viewer", 7, "gaze")])
        ctx = {"gaze": "looking_at_viewer"}

        actions = extract_actions_from_context_tags(ctx, character_id=1, db=db_session)

        assert actions is not None
        assert len(actions) == 1

    def test_no_context_tags_returns_none(self, db_session):
        assert extract_actions_from_context_tags(None, character_id=1, db=db_session) is None
        assert extract_actions_from_context_tags({}, character_id=1, db=db_session) is None

    def test_no_character_id_returns_none(self, db_session):
        ctx = {"expression": ["smile"]}
        assert extract_actions_from_context_tags(ctx, character_id=0, db=db_session) is None

    def test_non_action_categories_ignored(self, db_session):
        _seed_tags(db_session, [("night", 3)])
        ctx = {"environment": ["night"], "camera": ["close-up"]}

        actions = extract_actions_from_context_tags(ctx, character_id=1, db=db_session)

        assert actions is None

    def test_unknown_tags_skipped(self, db_session):
        ctx = {"expression": ["nonexistent_tag"]}

        actions = extract_actions_from_context_tags(ctx, character_id=1, db=db_session)

        assert actions is None


# ── Single Character (Monologue) Tests ───────────────────────────────


class TestSingleCharacterPopulation:
    """Phase 1-A: 1인 캐릭터(Monologue) character_actions 생성 테스트."""

    def test_monologue_speaker_a_only(self, db_session):
        """1인 캐릭터(character_b_id=None) + Speaker A → character_actions 생성."""
        _seed_tags(db_session, [("smile", 7), ("standing", 8, "pose")])
        scenes = [
            _scene("speaker_1", {"expression": ["smile"], "pose": ["standing"]}),
        ]

        result = auto_populate_character_actions(scenes, character_id=50, character_b_id=None, db=db_session)

        assert "character_actions" in result[0]
        assert len(result[0]["character_actions"]) == 2
        assert all(a["character_id"] == 50 for a in result[0]["character_actions"])

    def test_monologue_with_narrator_mixed(self, db_session):
        """Monologue: Speaker A + Narrator 혼합 → A만 character_actions."""
        _seed_tags(db_session, [("crying", 7), ("looking_down", 7, "gaze")])
        scenes = [
            _scene("narrator", {"mood": ["sad"]}),
            _scene("speaker_1", {"expression": ["crying"], "gaze": "looking_down"}),
            _scene("narrator", {"environment": ["night"]}),
        ]

        result = auto_populate_character_actions(scenes, character_id=50, character_b_id=None, db=db_session)

        assert "character_actions" not in result[0]  # Narrator
        assert len(result[1]["character_actions"]) == 2  # Speaker A
        assert "character_actions" not in result[2]  # Narrator

    def test_monologue_pose_and_gaze_extracted(self, db_session):
        """context_tags에 pose/gaze 있을 때 정상 추출."""
        _seed_tags(db_session, [("sitting", 8, "pose"), ("looking_to_the_side", 7, "gaze")])
        scenes = [
            _scene("speaker_1", {"pose": ["sitting"], "gaze": "looking_to_the_side"}),
        ]

        result = auto_populate_character_actions(scenes, character_id=50, character_b_id=None, db=db_session)

        assert len(result[0]["character_actions"]) == 2


# ── Group Name Filtering Tests (P0-3) ────────────────────────────────


class TestGroupNameFiltering:
    """P0-3: auto_populate는 (tag_name, group_name) 복합키로 매칭한다."""

    def test_group_name_mismatch_rejected(self, db_session):
        """'standing'이 expression group에만 있으면 pose 매칭 거부."""
        _seed_tags(db_session, [("standing", 8)])  # default group_name="expression"
        scenes = [_scene("speaker_1", {"pose": ["standing"]})]

        result = auto_populate_character_actions(scenes, character_id=1, character_b_id=None, db=db_session)

        assert "character_actions" not in result[0]

    def test_group_name_match_accepted(self, db_session):
        """'standing'이 pose group에 있으면 pose 매칭 성공."""
        _seed_tags(db_session, [("standing", 8, "pose")])
        scenes = [_scene("speaker_1", {"pose": ["standing"]})]

        result = auto_populate_character_actions(scenes, character_id=1, character_b_id=None, db=db_session)

        assert len(result[0]["character_actions"]) == 1

    def test_extract_also_filters_group_name(self, db_session):
        """extract_actions_from_context_tags도 group_name 필터링 적용."""
        _seed_tags(db_session, [("standing", 8)])  # expression (wrong group)
        ctx = {"pose": ["standing"]}

        actions = extract_actions_from_context_tags(ctx, character_id=1, db=db_session)

        assert actions is None
