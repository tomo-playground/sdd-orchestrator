"""Tests for _finalize_validators.py: style modifier filter + IP-Adapter weight normalizer.

Also tests diversify_gazes(), diversify_actions(), diversify_expressions(),
validate_context_tag_categories(), diversify_cameras(), diversify_poses() from _context_tag_utils.py.
And finalize.py helper functions.
"""

from unittest.mock import MagicMock, patch

from services.agent.nodes._context_tag_utils import (
    _coerce_str,
    _infer_emotion_from_script,
    _normalize_emotion,
    derive_expression_from_emotion,
    derive_mood_from_emotion,
    diversify_expressions,
    validate_context_tag_categories,
)
from services.agent.nodes._diversify_utils import diversify_actions, diversify_gazes
from services.agent.nodes._finalize_validators import (
    filter_style_modifiers,
    normalize_ip_adapter_weights,
)

# ── filter_style_modifiers ────────────────────────────────────────────


class TestFilterStyleModifiers:
    """StyleProfile 영역 수식어 제거 테스트."""

    def test_removes_style_modifiers(self):
        scenes = [{"image_prompt": "1girl, brown_hair, high_contrast, smile, highly_detailed"}]
        filter_style_modifiers(scenes)
        assert scenes[0]["image_prompt"] == "1girl, brown_hair, smile"

    def test_preserves_non_style_tags(self):
        scenes = [{"image_prompt": "1girl, masterpiece, best_quality, cowboy_shot"}]
        filter_style_modifiers(scenes)
        assert scenes[0]["image_prompt"] == "1girl, masterpiece, best_quality, cowboy_shot"

    def test_empty_prompt(self):
        scenes = [{"image_prompt": ""}]
        filter_style_modifiers(scenes)
        assert scenes[0]["image_prompt"] == ""

    def test_missing_prompt_skipped(self):
        scenes = [{"speaker": "Narrator"}]
        filter_style_modifiers(scenes)
        assert "image_prompt" not in scenes[0]

    def test_removes_all_style_modifiers(self):
        scenes = [{"image_prompt": "vibrant_colors, soft_colors, pastel_colors, muted_colors"}]
        filter_style_modifiers(scenes)
        assert scenes[0]["image_prompt"] == ""

    def test_case_insensitive_removal(self):
        """공백 형식도 매칭."""
        scenes = [{"image_prompt": "1girl, High Contrast, smile"}]
        filter_style_modifiers(scenes)
        assert scenes[0]["image_prompt"] == "1girl, smile"

    def test_flat_color_removed(self):
        """flat_color은 StyleProfile이 주입하므로 제거."""
        scenes = [{"image_prompt": "1girl, flat_color, smile"}]
        filter_style_modifiers(scenes)
        assert scenes[0]["image_prompt"] == "1girl, smile"

    def test_multiple_scenes(self):
        scenes = [
            {"image_prompt": "1girl, ultra_detailed, smile"},
            {"image_prompt": "no_humans, scenery, very_detailed"},
        ]
        filter_style_modifiers(scenes)
        assert scenes[0]["image_prompt"] == "1girl, smile"
        assert scenes[1]["image_prompt"] == "no_humans, scenery"


# ── normalize_ip_adapter_weights ──────────────────────────────────────


class TestHasCharacterLora:
    """_has_character_lora 헬퍼 테스트."""

    def test_none_cid_returns_false(self):
        from services.agent.nodes._finalize_validators import _has_character_lora

        assert _has_character_lora(None, db=MagicMock()) is False

    def test_none_db_returns_false(self):
        from services.agent.nodes._finalize_validators import _has_character_lora

        assert _has_character_lora(1, db=None) is False

    def test_character_not_found(self):
        from services.agent.nodes._finalize_validators import _has_character_lora

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        assert _has_character_lora(1, db=db) is False

    def test_character_no_loras(self):
        from services.agent.nodes._finalize_validators import _has_character_lora

        db = MagicMock()
        char = MagicMock(loras=[], ip_adapter_weight=None)
        db.execute.return_value.scalar_one_or_none.return_value = char
        assert _has_character_lora(1, db=db) is False

    def test_character_with_non_character_lora(self):
        from services.agent.nodes._finalize_validators import _has_character_lora

        db = MagicMock()
        char = MagicMock(loras=[{"lora_type": "style", "name": "flat_color"}], ip_adapter_weight=None)
        db.execute.return_value.scalar_one_or_none.return_value = char
        assert _has_character_lora(1, db=db) is False

    def test_character_with_character_lora(self):
        from services.agent.nodes._finalize_validators import _has_character_lora

        db = MagicMock()
        char = MagicMock(loras=[{"lora_type": "character", "name": "usagi_drop"}], ip_adapter_weight=None)
        db.execute.return_value.scalar_one_or_none.return_value = char
        assert _has_character_lora(1, db=db) is True


class TestNormalizeIPAdapterWeights:
    """IP-Adapter weight 정규화 테스트."""

    def test_narrator_always_zero(self):
        scenes = [
            {"speaker": "Narrator", "ip_adapter_weight": 0.7},
            {"speaker": "Narrator"},
        ]
        normalize_ip_adapter_weights(scenes, character_id=1)
        assert scenes[0]["ip_adapter_weight"] == 0.0
        assert scenes[1]["ip_adapter_weight"] == 0.0

    def test_preserves_explicit_weight(self):
        """Cinematographer가 명시한 값은 보존."""
        scenes = [{"speaker": "A", "ip_adapter_weight": 0.5}]
        normalize_ip_adapter_weights(scenes, character_id=1)
        assert scenes[0]["ip_adapter_weight"] == 0.5

    @patch(
        "services.agent.nodes._finalize_validators._get_character_info",
        return_value=(0.8, True),
    )
    def test_normalizes_to_character_db_weight(self, mock_info):
        """캐릭터 DB 값으로 통일."""
        scenes = [
            {"speaker": "A", "ip_adapter_weight": None},
            {"speaker": "A"},
        ]
        normalize_ip_adapter_weights(scenes, character_id=42)
        assert scenes[0]["ip_adapter_weight"] == 0.8
        assert scenes[1]["ip_adapter_weight"] == 0.8

    @patch(
        "services.agent.nodes._finalize_validators._get_character_info",
        return_value=(None, True),
    )
    def test_fallback_to_default_when_no_db_weight(self, mock_info):
        """DB에 값 없으면 DEFAULT_IP_ADAPTER_WEIGHT(0.7) 사용."""
        scenes = [{"speaker": "A"}]
        normalize_ip_adapter_weights(scenes, character_id=1)
        assert scenes[0]["ip_adapter_weight"] == 0.7

    @patch(
        "services.agent.nodes._finalize_validators._get_character_info",
    )
    def test_speaker_b_uses_own_weight(self, mock_info):
        """Speaker B는 character_b_id 기반 weight 사용."""
        mock_info.side_effect = lambda cid, db=None: {10: (0.6, True), 20: (0.9, True)}.get(cid, (None, False))
        scenes = [
            {"speaker": "A"},
            {"speaker": "B"},
        ]
        normalize_ip_adapter_weights(scenes, character_id=10, character_b_id=20)
        assert scenes[0]["ip_adapter_weight"] == 0.6
        assert scenes[1]["ip_adapter_weight"] == 0.9

    def test_no_character_id_uses_default(self):
        """character_id=None이면 DEFAULT 사용."""
        scenes = [{"speaker": "A"}]
        normalize_ip_adapter_weights(scenes, character_id=None)
        assert scenes[0]["ip_adapter_weight"] == 0.7


# ── diversify_gazes ───────────────────────────────────────────────────


class TestDiversifyGazes:
    """Gaze 다양성 강제 교정 테스트."""

    def _make_scenes(self, gazes: list[str], emotions: list[str | None] | None = None) -> list[dict]:
        """테스트용 캐릭터 씬 목록 생성."""
        scenes = []
        for i, gaze in enumerate(gazes):
            emotion = emotions[i] if emotions else None
            ctx = {"gaze": gaze}
            if emotion:
                ctx["emotion"] = emotion
            scenes.append({"speaker": "A", "context_tags": ctx})
        return scenes

    def test_looking_at_viewer_dominant_gets_corrected(self):
        """50% 초과 looking_at_viewer → emotion 기반 교정."""
        scenes = self._make_scenes(
            gazes=["looking_at_viewer"] * 5,
            emotions=["sad", "hopeful", "nostalgic", "nervous", "calm"],
        )
        diversify_gazes(scenes)

        gazes = [s["context_tags"]["gaze"] for s in scenes]
        lav_count = gazes.count("looking_at_viewer")
        assert lav_count < 3, f"looking_at_viewer가 여전히 {lav_count}/5로 과다"

    def test_emotion_based_gaze_replacement(self):
        """emotion → gaze 매핑이 정확한지."""
        scenes = self._make_scenes(
            gazes=["looking_at_viewer"] * 4,
            emotions=["sad", "hopeful", "nostalgic", "nervous"],
        )
        diversify_gazes(scenes)

        ctx = [s["context_tags"] for s in scenes]
        assert ctx[0]["gaze"] == "looking_down"  # sad → looking_down
        assert ctx[1]["gaze"] == "looking_up"  # hopeful → looking_up
        assert ctx[2]["gaze"] == "looking_afar"  # nostalgic → looking_afar
        assert ctx[3]["gaze"] == "looking_to_the_side"  # nervous → looking_to_the_side

    def test_sufficient_diversity_skipped(self):
        """이미 다양하면 교정 안 함."""
        scenes = self._make_scenes(
            gazes=["looking_at_viewer", "looking_down", "looking_up", "looking_afar"],
            emotions=["happy", "sad", "hopeful", "nostalgic"],
        )
        original_gazes = [s["context_tags"]["gaze"] for s in scenes]
        diversify_gazes(scenes)
        new_gazes = [s["context_tags"]["gaze"] for s in scenes]
        assert original_gazes == new_gazes

    def test_consecutive_same_gaze_avoided(self):
        """연속 동일 gaze 방지."""
        scenes = self._make_scenes(
            gazes=["looking_at_viewer"] * 5,
            emotions=["sad", "sad", "sad", "sad", "sad"],
        )
        diversify_gazes(scenes)

        gazes = [s["context_tags"]["gaze"] for s in scenes]
        for i in range(1, len(gazes)):
            if gazes[i] != "looking_at_viewer":
                # 교정된 gaze는 이전과 달라야 함
                assert gazes[i] != gazes[i - 1] or gazes[i] == "looking_at_viewer"

    def test_narrator_scenes_excluded(self):
        """Narrator 씬은 건너뜀."""
        scenes = [
            {"speaker": "Narrator", "context_tags": {"gaze": "looking_at_viewer"}},
            {"speaker": "A", "context_tags": {"gaze": "looking_at_viewer", "emotion": "sad"}},
            {"speaker": "A", "context_tags": {"gaze": "looking_at_viewer", "emotion": "happy"}},
            {"speaker": "A", "context_tags": {"gaze": "looking_at_viewer", "emotion": "nervous"}},
        ]
        diversify_gazes(scenes)
        # Narrator gaze는 변경 안 됨
        assert scenes[0]["context_tags"]["gaze"] == "looking_at_viewer"

    def test_no_emotion_scenes_untouched(self):
        """emotion 없는 씬의 gaze는 변경 안 됨."""
        scenes = self._make_scenes(
            gazes=["looking_at_viewer"] * 4,
            emotions=[None, None, None, None],
        )
        diversify_gazes(scenes)
        # emotion 없으므로 교정 불가 → 전부 그대로
        gazes = [s["context_tags"]["gaze"] for s in scenes]
        assert all(g == "looking_at_viewer" for g in gazes)

    def test_few_scenes_skipped(self):
        """3씬 미만이면 건너뜀."""
        scenes = self._make_scenes(
            gazes=["looking_at_viewer", "looking_at_viewer"],
            emotions=["sad", "happy"],
        )
        diversify_gazes(scenes)
        assert scenes[0]["context_tags"]["gaze"] == "looking_at_viewer"
        assert scenes[1]["context_tags"]["gaze"] == "looking_at_viewer"

    def test_non_lav_dominant_gaze_corrected(self):
        """looking_at_viewer 외의 dominant gaze도 교정 (일반화 검증)."""
        scenes = self._make_scenes(
            gazes=["looking_away"] * 4,
            emotions=["sad", "hopeful", "nostalgic", "nervous"],
        )
        diversify_gazes(scenes)
        gazes = [s["context_tags"]["gaze"] for s in scenes]
        away_count = gazes.count("looking_away")
        assert away_count < 3, f"looking_away가 여전히 {away_count}/4로 과다"

    def test_empty_gaze_dominant_skipped(self):
        """빈 문자열 dominant gaze는 교정하지 않음."""
        scenes = self._make_scenes(
            gazes=["", "", "", ""],
            emotions=["sad", "happy", "calm", "angry"],
        )
        diversify_gazes(scenes)
        gazes = [s["context_tags"]["gaze"] for s in scenes]
        assert all(g == "" for g in gazes)


# ── diversify_actions ───────────────────────────────────────────────────


class TestDiversifyActions:
    """Action 반복 교정 테스트."""

    def _make_scenes(self, actions: list[str], emotions: list[str | None] | None = None) -> list[dict]:
        scenes = []
        for i, action in enumerate(actions):
            emotion = emotions[i] if emotions else None
            ctx: dict = {"action": action}
            if emotion:
                ctx["emotion"] = emotion
            scenes.append({"speaker": "A", "context_tags": ctx})
        return scenes

    def test_dominant_action_corrected(self):
        """>40% 동일 action → emotion 기반 교정."""
        scenes = self._make_scenes(
            actions=["waving"] * 5,
            emotions=["sad", "confident", "calm", "angry", "tired"],
        )
        diversify_actions(scenes)
        actions = [s["context_tags"]["action"] for s in scenes]
        waving_count = actions.count("waving")
        assert waving_count < 4, f"waving이 여전히 {waving_count}/5로 과다"

    def test_sufficient_diversity_skipped(self):
        """이미 다양하면 교정 안 함."""
        scenes = self._make_scenes(
            actions=["waving", "sitting", "arms_up", "hugging", "pointing"],
            emotions=["happy", "calm", "excited", "sad", "angry"],
        )
        original = [s["context_tags"]["action"] for s in scenes]
        diversify_actions(scenes)
        current = [s["context_tags"]["action"] for s in scenes]
        assert original == current

    def test_empty_action_dominant_skipped(self):
        """빈 문자열 dominant action은 교정 안 함."""
        scenes = self._make_scenes(
            actions=["", "", "", ""],
            emotions=["sad", "happy", "calm", "angry"],
        )
        diversify_actions(scenes)
        actions = [s["context_tags"]["action"] for s in scenes]
        assert all(a == "" for a in actions)

    def test_no_emotion_untouched(self):
        """emotion 없는 씬의 action은 변경 안 됨."""
        scenes = self._make_scenes(
            actions=["waving"] * 4,
            emotions=[None, None, None, None],
        )
        diversify_actions(scenes)
        actions = [s["context_tags"]["action"] for s in scenes]
        assert all(a == "waving" for a in actions)

    def test_narrator_excluded(self):
        """Narrator 씬은 건너뜀."""
        scenes = [
            {"speaker": "Narrator", "context_tags": {"action": "waving"}},
            {"speaker": "A", "context_tags": {"action": "waving", "emotion": "sad"}},
            {"speaker": "A", "context_tags": {"action": "waving", "emotion": "calm"}},
            {"speaker": "A", "context_tags": {"action": "waving", "emotion": "angry"}},
        ]
        diversify_actions(scenes)
        assert scenes[0]["context_tags"]["action"] == "waving"

    def test_few_scenes_skipped(self):
        """3씬 미만이면 건너뜀."""
        scenes = self._make_scenes(
            actions=["waving", "waving"],
            emotions=["sad", "happy"],
        )
        diversify_actions(scenes)
        assert scenes[0]["context_tags"]["action"] == "waving"

    def test_emotion_to_action_mapping(self):
        """emotion → action 매핑 정확성 검증."""
        scenes = self._make_scenes(
            actions=["waving"] * 4,
            emotions=["sad", "confident", "calm", "embarrassed"],
        )
        diversify_actions(scenes)
        ctx = [s["context_tags"] for s in scenes]
        assert ctx[0]["action"] == "hugging"  # sad → hugging
        assert ctx[1]["action"] == "arms_crossed"  # confident → arms_crossed
        assert ctx[2]["action"] == "sitting"  # calm → sitting
        assert ctx[3]["action"] == "hand_on_face"  # embarrassed → hand_on_face


# ── _resolve_characters_from_group ──────────────────────────────────────


class TestResolveCharactersFromGroup:
    """group_id → character fallback 테스트."""

    def _mock_db(self, chars: list[tuple[int, str]]):
        """Mock DB query returning character rows."""
        db = MagicMock()
        rows = [MagicMock(id=c[0]) for c in chars]
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = rows
        return db

    def test_dialogue_returns_both_chars(self):
        from services.agent.nodes.finalize import _resolve_characters_from_group

        db = self._mock_db([(1, "A"), (2, "B")])
        a, b = _resolve_characters_from_group(1, "Dialogue", db)
        assert a == 1
        assert b == 2

    def test_narrated_dialogue_returns_both_chars(self):
        from services.agent.nodes.finalize import _resolve_characters_from_group

        db = self._mock_db([(1, "A"), (2, "B")])
        a, b = _resolve_characters_from_group(1, "Narrated Dialogue", db)
        assert a == 1
        assert b == 2

    def test_monologue_returns_only_char_a(self):
        from services.agent.nodes.finalize import _resolve_characters_from_group

        db = self._mock_db([(1, "A"), (2, "B")])
        a, b = _resolve_characters_from_group(1, "Monologue", db)
        assert a == 1
        assert b is None

    def test_empty_group_returns_none(self):
        from services.agent.nodes.finalize import _resolve_characters_from_group

        db = self._mock_db([])
        a, b = _resolve_characters_from_group(1, "Dialogue", db)
        assert a is None
        assert b is None

    def test_single_char_dialogue(self):
        """그룹에 1명만 있으면 char_b는 None."""
        from services.agent.nodes.finalize import _resolve_characters_from_group

        db = self._mock_db([(1, "A")])
        a, b = _resolve_characters_from_group(1, "Dialogue", db)
        assert a == 1
        assert b is None


# ── _coerce_str ──────────────────────────────────────────────────────


class TestCoerceStr:
    """Gemini 반환값 → 문자열 정규화."""

    def test_string_passthrough(self):
        assert _coerce_str("hello") == "hello"

    def test_list_takes_first(self):
        assert _coerce_str(["smile", "grin"]) == "smile"

    def test_empty_list_returns_empty(self):
        assert _coerce_str([]) == ""

    def test_none_returns_empty(self):
        assert _coerce_str(None) == ""

    def test_int_to_str(self):
        assert _coerce_str(42) == "42"


# ── _normalize_emotion ───────────────────────────────────────────────


class TestNormalizeEmotion:
    """비표준 emotion 정규화 테스트."""

    def test_exact_match(self):
        assert _normalize_emotion("happy") == "happy"

    def test_korean_alias(self):
        assert _normalize_emotion("슬픔") == "sad"

    def test_partial_match(self):
        """'lonely_expression' → 'lonely' (부분 매칭)."""
        assert _normalize_emotion("lonely_expression") == "lonely"

    def test_unknown_passthrough(self):
        assert _normalize_emotion("zzz_unknown_zzz") == "zzz_unknown_zzz"


# ── derive_expression_from_emotion / derive_mood_from_emotion ────────


class TestDeriveFromEmotion:
    """emotion → expression/mood 파생 테스트."""

    def test_expression_happy(self):
        assert derive_expression_from_emotion("happy") == "smile"

    def test_expression_angry(self):
        assert derive_expression_from_emotion("angry") == "angry"

    def test_expression_none(self):
        assert derive_expression_from_emotion(None) is None

    def test_expression_empty(self):
        assert derive_expression_from_emotion("") is None

    def test_expression_list_input(self):
        """Gemini가 리스트로 반환하는 경우."""
        assert derive_expression_from_emotion(["sad"]) == "sad"

    def test_mood_sad(self):
        assert derive_mood_from_emotion("sad") == "melancholic"

    def test_mood_none(self):
        assert derive_mood_from_emotion(None) is None

    def test_mood_korean(self):
        """한국어 별칭도 매핑 가능."""
        assert derive_mood_from_emotion("분노") == "intense"


# ── _infer_emotion_from_script ───────────────────────────────────────


class TestInferEmotionFromScript:
    """한국어 스크립트 키워드 → emotion 추론 테스트."""

    def test_sad_keyword(self):
        assert _infer_emotion_from_script("너무 슬퍼서 눈물이 나왔어") == "sad"

    def test_angry_keyword(self):
        assert _infer_emotion_from_script("정말 화나는 일이야") == "angry"

    def test_determined_keyword(self):
        assert _infer_emotion_from_script("이번엔 각오하고 해보자") == "determined"

    def test_no_keyword(self):
        assert _infer_emotion_from_script("오늘 날씨가 좋다") is None

    def test_empty_script(self):
        assert _infer_emotion_from_script("") is None

    def test_first_match_wins(self):
        """여러 키워드 매칭 시 첫 번째 규칙 우선."""
        result = _infer_emotion_from_script("걱정되고 슬퍼")
        assert result == "anxious"  # 걱정 → anxious가 먼저


# ── validate_context_tag_categories ──────────────────────────────────


class TestValidateContextTagCategories:
    """expression/gaze/pose 카테고리 재분류 테스트."""

    def test_correct_categories_unchanged(self):
        """올바른 카테고리는 그대로 유지."""
        scenes = [{"context_tags": {"expression": "smile", "gaze": "looking_at_viewer", "pose": "standing"}}]
        validate_context_tag_categories(scenes)
        ctx = scenes[0]["context_tags"]
        assert ctx["expression"] == "smile"
        assert ctx["gaze"] == "looking_at_viewer"
        assert ctx["pose"] == "standing"

    def test_misplaced_gaze_in_expression(self):
        """expression에 gaze 값이 들어간 경우 재분류."""
        scenes = [{"context_tags": {"expression": "looking_down", "gaze": None}}]
        validate_context_tag_categories(scenes)
        ctx = scenes[0]["context_tags"]
        assert ctx.get("gaze") == "looking_down"
        assert "expression" not in ctx  # 삭제됨

    def test_list_value_coerced_to_str(self):
        """Gemini가 리스트로 반환한 값 → str 정규화."""
        scenes = [{"context_tags": {"expression": ["smile"], "pose": "standing"}}]
        validate_context_tag_categories(scenes)
        assert scenes[0]["context_tags"]["expression"] == "smile"

    def test_invalid_mood_dropped(self):
        """비표준 mood 값은 삭제."""
        scenes = [{"context_tags": {"mood": "super_happy_invalid_mood_xyz"}}]
        validate_context_tag_categories(scenes)
        assert "mood" not in scenes[0]["context_tags"]

    def test_no_context_tags_skipped(self):
        """context_tags가 없는 씬은 건너뜀."""
        scenes = [{"speaker": "A"}]
        validate_context_tag_categories(scenes)
        assert "context_tags" not in scenes[0]

    def test_empty_context_tags_skipped(self):
        """빈 context_tags는 건너뜀."""
        scenes = [{"context_tags": {}}]
        validate_context_tag_categories(scenes)
        assert scenes[0]["context_tags"] == {}


# ── diversify_expressions ────────────────────────────────────────────


class TestDiversifyExpressions:
    """Expression 단조로움 보정 테스트."""

    def _make_scenes(self, expressions, emotions=None, scripts=None):
        scenes = []
        for i, expr in enumerate(expressions):
            ctx = {"expression": expr}
            if emotions and emotions[i]:
                ctx["emotion"] = emotions[i]
            scene = {"speaker": "A", "context_tags": ctx}
            if scripts and scripts[i]:
                scene["script"] = scripts[i]
            scenes.append(scene)
        return scenes

    def test_dominant_expression_corrected_by_script(self):
        """>60% 동일 expression + 스크립트 키워드 → 교정."""
        scenes = self._make_scenes(
            expressions=["smile"] * 5,
            emotions=[None, None, None, None, None],
            scripts=["너무 슬퍼", "화나는 일", "걱정돼", "부끄러워", "파이팅"],
        )
        diversify_expressions(scenes)
        exprs = [s["context_tags"]["expression"] for s in scenes]
        smile_count = exprs.count("smile")
        assert smile_count < 4, f"smile이 여전히 {smile_count}/5로 과다"

    def test_sufficient_diversity_skipped(self):
        """이미 다양한 expression은 건너뜀."""
        scenes = self._make_scenes(
            expressions=["smile", "sad", "angry", "nervous", "surprised"],
        )
        original = [s["context_tags"]["expression"] for s in scenes]
        diversify_expressions(scenes)
        current = [s["context_tags"]["expression"] for s in scenes]
        assert original == current

    def test_emotion_present_skipped(self):
        """이미 emotion이 있는 씬은 건너뜀."""
        scenes = self._make_scenes(
            expressions=["smile"] * 4,
            emotions=["happy", "happy", "happy", "happy"],
            scripts=["슬퍼", "화나", "걱정", "부끄러"],
        )
        diversify_expressions(scenes)
        # emotion 이미 있으므로 expression 교체 안 됨
        exprs = [s["context_tags"]["expression"] for s in scenes]
        assert all(e == "smile" for e in exprs)

    def test_few_scenes_skipped(self):
        """3씬 미만이면 건너뜀."""
        scenes = self._make_scenes(
            expressions=["smile", "smile"],
            scripts=["슬퍼", "화나"],
        )
        diversify_expressions(scenes)
        assert scenes[0]["context_tags"]["expression"] == "smile"

    def test_narrator_excluded(self):
        """Narrator 씬은 건너뜀."""
        scenes = [
            {"speaker": "Narrator", "context_tags": {"expression": "smile"}},
            {"speaker": "A", "context_tags": {"expression": "smile"}, "script": "슬퍼"},
            {"speaker": "A", "context_tags": {"expression": "smile"}, "script": "화나"},
            {"speaker": "A", "context_tags": {"expression": "smile"}, "script": "걱정돼"},
        ]
        diversify_expressions(scenes)
        assert scenes[0]["context_tags"]["expression"] == "smile"


# ── diversify_cameras ───────────────────────────────────────────


class TestDiversifyCameras:
    """카메라 다양성 보정 테스트."""

    def test_dominant_camera_corrected(self):
        """50% 초과 동일 카메라 + emotion 있으면 교정."""
        from services.agent.nodes._diversify_utils import diversify_cameras

        scenes = [
            {"context_tags": {"camera": "cowboy_shot", "emotion": "sad"}},
            {"context_tags": {"camera": "cowboy_shot", "emotion": "angry"}},
            {"context_tags": {"camera": "cowboy_shot", "emotion": "hopeful"}},
            {"context_tags": {"camera": "close-up"}},
        ]
        diversify_cameras(scenes)
        cameras = [s["context_tags"]["camera"] for s in scenes]
        # 최소 1개는 교정되어야 함
        assert cameras.count("cowboy_shot") < 3

    def test_diverse_camera_no_change(self):
        """다양한 카메라 → 변경 없음."""
        from services.agent.nodes._diversify_utils import diversify_cameras

        scenes = [
            {"context_tags": {"camera": "cowboy_shot", "emotion": "happy"}},
            {"context_tags": {"camera": "close-up", "emotion": "sad"}},
            {"context_tags": {"camera": "full_body", "emotion": "angry"}},
            {"context_tags": {"camera": "upper_body", "emotion": "calm"}},
        ]
        diversify_cameras(scenes)
        assert scenes[0]["context_tags"]["camera"] == "cowboy_shot"
        assert scenes[1]["context_tags"]["camera"] == "close-up"

    def test_few_scenes_skipped(self):
        """3씬 미만이면 건너뜀."""
        from services.agent.nodes._diversify_utils import diversify_cameras

        scenes = [
            {"context_tags": {"camera": "cowboy_shot", "emotion": "sad"}},
            {"context_tags": {"camera": "cowboy_shot", "emotion": "angry"}},
        ]
        diversify_cameras(scenes)
        assert scenes[0]["context_tags"]["camera"] == "cowboy_shot"

    def test_no_emotion_no_change(self):
        """emotion 없으면 교정하지 않음."""
        from services.agent.nodes._diversify_utils import diversify_cameras

        scenes = [
            {"context_tags": {"camera": "cowboy_shot"}},
            {"context_tags": {"camera": "cowboy_shot"}},
            {"context_tags": {"camera": "cowboy_shot"}},
        ]
        diversify_cameras(scenes)
        cameras = [s["context_tags"]["camera"] for s in scenes]
        assert cameras.count("cowboy_shot") == 3

    def test_camera_angle_alias(self):
        """camera_angle 키도 인식."""
        from services.agent.nodes._diversify_utils import diversify_cameras

        scenes = [
            {"context_tags": {"camera_angle": "close_up", "emotion": "happy"}},
            {"context_tags": {"camera_angle": "close_up", "emotion": "angry"}},
            {"context_tags": {"camera_angle": "close_up", "emotion": "sad"}},
        ]
        diversify_cameras(scenes)
        # camera_angle가 아닌 camera로 교정됨
        corrected = sum(1 for s in scenes if s["context_tags"].get("camera"))
        assert corrected >= 1


# ── diversify_poses ───────────────────────────────────────────


class TestDiversifyPoses:
    """포즈 다양성 보정 테스트."""

    def test_dominant_pose_corrected(self):
        """50% 초과 동일 pose + emotion 있으면 교정."""
        from services.agent.nodes._diversify_utils import diversify_poses

        scenes = [
            {"speaker": "A", "context_tags": {"pose": "standing", "emotion": "sad"}},
            {"speaker": "A", "context_tags": {"pose": "standing", "emotion": "excited"}},
            {"speaker": "A", "context_tags": {"pose": "standing", "emotion": "angry"}},
            {"speaker": "A", "context_tags": {"pose": "sitting"}},
        ]
        diversify_poses(scenes)
        poses = [s["context_tags"]["pose"] for s in scenes]
        assert poses.count("standing") < 3

    def test_narrator_excluded(self):
        """Narrator 씬은 제외."""
        from services.agent.nodes._diversify_utils import diversify_poses

        scenes = [
            {"speaker": "Narrator", "context_tags": {"pose": "standing", "emotion": "sad"}},
            {"speaker": "Narrator", "context_tags": {"pose": "standing", "emotion": "happy"}},
            {"speaker": "Narrator", "context_tags": {"pose": "standing", "emotion": "angry"}},
        ]
        diversify_poses(scenes)
        # Narrator만 있으면 char_scenes < 3이라 스킵
        assert all(s["context_tags"]["pose"] == "standing" for s in scenes)

    def test_diverse_pose_no_change(self):
        """이미 다양한 pose → 변경 없음."""
        from services.agent.nodes._diversify_utils import diversify_poses

        scenes = [
            {"speaker": "A", "context_tags": {"pose": "standing", "emotion": "happy"}},
            {"speaker": "A", "context_tags": {"pose": "sitting", "emotion": "sad"}},
            {"speaker": "A", "context_tags": {"pose": "arms_crossed", "emotion": "angry"}},
            {"speaker": "A", "context_tags": {"pose": "arms_up", "emotion": "excited"}},
        ]
        diversify_poses(scenes)
        assert scenes[0]["context_tags"]["pose"] == "standing"
        assert scenes[1]["context_tags"]["pose"] == "sitting"


# ── finalize.py helper functions ─────────────────────────────────────


class TestSanitizeQualityTags:
    """_sanitize_quality_tags 테스트."""

    def test_replaces_high_quality(self):
        from services.agent.nodes.finalize import _sanitize_quality_tags

        scenes = [{"image_prompt": "1girl, high_quality, smile"}]
        _sanitize_quality_tags(scenes)
        assert scenes[0]["image_prompt"] == "1girl, best_quality, smile"

    def test_preserves_standard_tags(self):
        from services.agent.nodes.finalize import _sanitize_quality_tags

        scenes = [{"image_prompt": "1girl, best_quality, masterpiece"}]
        _sanitize_quality_tags(scenes)
        assert scenes[0]["image_prompt"] == "1girl, best_quality, masterpiece"

    def test_empty_prompt_skipped(self):
        from services.agent.nodes.finalize import _sanitize_quality_tags

        scenes = [{"image_prompt": ""}]
        _sanitize_quality_tags(scenes)
        assert scenes[0]["image_prompt"] == ""

    def test_missing_prompt_skipped(self):
        from services.agent.nodes.finalize import _sanitize_quality_tags

        scenes = [{"speaker": "Narrator"}]
        _sanitize_quality_tags(scenes)
        assert "image_prompt" not in scenes[0]


class TestInjectNegativePrompts:
    """_inject_negative_prompts 테스트."""

    def test_empty_negative_gets_default(self):
        from services.agent.nodes.finalize import _inject_negative_prompts

        scenes = [{"negative_prompt": ""}]
        _inject_negative_prompts(scenes)
        assert scenes[0]["negative_prompt"]  # 기본값이 채워짐

    def test_existing_negative_preserved(self):
        from services.agent.nodes.finalize import _inject_negative_prompts

        scenes = [{"negative_prompt": "custom_bad_tag"}]
        _inject_negative_prompts(scenes)
        assert "custom_bad_tag" in scenes[0]["negative_prompt"]

    def test_extra_merged(self):
        from services.agent.nodes.finalize import _inject_negative_prompts

        scenes = [{"negative_prompt": "base_neg", "negative_prompt_extra": "extra_neg"}]
        _inject_negative_prompts(scenes)
        assert "base_neg" in scenes[0]["negative_prompt"]
        assert "extra_neg" in scenes[0]["negative_prompt"]


class TestInjectDefaultContextTags:
    """_inject_default_context_tags 테스트."""

    def test_narrator_skipped(self):
        from services.agent.nodes.finalize import _inject_default_context_tags

        scenes = [{"speaker": "Narrator"}]
        _inject_default_context_tags(scenes)
        assert "context_tags" not in scenes[0]

    def test_missing_context_tags_created(self):
        from services.agent.nodes.finalize import _inject_default_context_tags

        scenes = [{"speaker": "A"}]
        _inject_default_context_tags(scenes)
        ctx = scenes[0]["context_tags"]
        assert "pose" in ctx
        assert "gaze" in ctx
        assert "expression" in ctx

    def test_emotion_derives_expression(self):
        from services.agent.nodes.finalize import _inject_default_context_tags

        scenes = [{"speaker": "A", "context_tags": {"emotion": "sad"}}]
        _inject_default_context_tags(scenes)
        assert scenes[0]["context_tags"]["expression"] == "sad"

    def test_emotion_derives_mood(self):
        from services.agent.nodes.finalize import _inject_default_context_tags

        scenes = [{"speaker": "A", "context_tags": {"emotion": "happy"}}]
        _inject_default_context_tags(scenes)
        assert scenes[0]["context_tags"]["mood"] == "cheerful"

    def test_existing_expression_preserved_without_emotion(self):
        from services.agent.nodes.finalize import _inject_default_context_tags

        scenes = [{"speaker": "A", "context_tags": {"expression": "grin"}}]
        _inject_default_context_tags(scenes)
        assert scenes[0]["context_tags"]["expression"] == "grin"


class TestNormalizeEnvironmentTags:
    """_normalize_environment_tags 테스트."""

    def test_setting_renamed_to_environment(self):
        from services.agent.nodes.finalize import _normalize_environment_tags

        scenes = [{"context_tags": {"setting": "park"}}]
        _normalize_environment_tags(scenes)
        assert scenes[0]["context_tags"]["environment"] == "park"
        assert "setting" not in scenes[0]["context_tags"]

    def test_existing_environment_not_overwritten(self):
        from services.agent.nodes.finalize import _normalize_environment_tags

        scenes = [{"context_tags": {"setting": "park", "environment": "forest"}}]
        _normalize_environment_tags(scenes)
        assert scenes[0]["context_tags"]["environment"] == "forest"
        assert "setting" in scenes[0]["context_tags"]  # setting 유지

    def test_no_context_tags_skipped(self):
        from services.agent.nodes.finalize import _normalize_environment_tags

        scenes = [{"speaker": "A"}]
        _normalize_environment_tags(scenes)
        assert "context_tags" not in scenes[0]


class TestCopySceneLevelToContextTags:
    """_copy_scene_level_to_context_tags 테스트."""

    def test_camera_copied(self):
        from services.agent.nodes.finalize import _copy_scene_level_to_context_tags

        scenes = [{"camera": "close_up", "context_tags": {}}]
        _copy_scene_level_to_context_tags(scenes)
        assert scenes[0]["context_tags"]["camera"] == "close_up"

    def test_existing_camera_not_overwritten(self):
        from services.agent.nodes.finalize import _copy_scene_level_to_context_tags

        scenes = [{"camera": "close_up", "context_tags": {"camera": "cowboy_shot"}}]
        _copy_scene_level_to_context_tags(scenes)
        assert scenes[0]["context_tags"]["camera"] == "cowboy_shot"

    def test_no_context_tags_created(self):
        from services.agent.nodes.finalize import _copy_scene_level_to_context_tags

        scenes = [{"camera": "close_up"}]
        _copy_scene_level_to_context_tags(scenes)
        assert scenes[0]["context_tags"]["camera"] == "close_up"


class TestInjectWriterPlanEmotions:
    """_inject_writer_plan_emotions 테스트."""

    def test_fills_empty_emotions(self):
        from services.agent.nodes.finalize import _inject_writer_plan_emotions

        scenes = [{"context_tags": {}}, {"context_tags": {"emotion": "happy"}}]
        plan = {"emotional_arc": ["sad", "angry"]}
        _inject_writer_plan_emotions(scenes, plan)
        assert scenes[0]["context_tags"]["emotion"] == "sad"
        assert scenes[1]["context_tags"]["emotion"] == "happy"  # 기존값 보존

    def test_no_plan_skipped(self):
        from services.agent.nodes.finalize import _inject_writer_plan_emotions

        scenes = [{"context_tags": {}}]
        _inject_writer_plan_emotions(scenes, None)
        assert "emotion" not in scenes[0]["context_tags"]

    def test_no_arc_skipped(self):
        from services.agent.nodes.finalize import _inject_writer_plan_emotions

        scenes = [{"context_tags": {}}]
        _inject_writer_plan_emotions(scenes, {"emotional_arc": []})
        assert "emotion" not in scenes[0]["context_tags"]

    def test_creates_context_tags_if_missing(self):
        from services.agent.nodes.finalize import _inject_writer_plan_emotions

        scenes = [{"speaker": "A"}]
        plan = {"emotional_arc": ["calm"]}
        _inject_writer_plan_emotions(scenes, plan)
        assert scenes[0]["context_tags"]["emotion"] == "calm"


# ── _apply_tag_aliases ───────────────────────────────────────────────


class TestApplyTagAliases:
    """TagAliasCache 기반 태그 교정 테스트."""

    @patch("services.agent.nodes.finalize.get_db_session")
    def test_replaces_alias(self, mock_db_session):
        from services.agent.nodes.finalize import _apply_tag_aliases

        with (
            patch("services.keywords.db_cache.TagAliasCache._initialized", True),
            patch(
                "services.keywords.db_cache.TagAliasCache.get_replacement",
                side_effect=lambda t: "brown_hair" if t == "brunette" else ...,
            ),
        ):
            scenes = [{"image_prompt": "1girl, brunette, smile"}]
            _apply_tag_aliases(scenes)
            assert "brown_hair" in scenes[0]["image_prompt"]
            assert "brunette" not in scenes[0]["image_prompt"]

    @patch("services.agent.nodes.finalize.get_db_session")
    def test_removes_tag(self, mock_db_session):
        from services.agent.nodes.finalize import _apply_tag_aliases

        with (
            patch("services.keywords.db_cache.TagAliasCache._initialized", True),
            patch(
                "services.keywords.db_cache.TagAliasCache.get_replacement",
                side_effect=lambda t: None if t == "bad_tag" else ...,
            ),
        ):
            scenes = [{"image_prompt": "1girl, bad_tag, smile"}]
            _apply_tag_aliases(scenes)
            assert "bad_tag" not in scenes[0]["image_prompt"]
            assert "1girl" in scenes[0]["image_prompt"]

    @patch("services.agent.nodes.finalize.get_db_session")
    def test_split_replacement(self, mock_db_session):
        from services.agent.nodes.finalize import _apply_tag_aliases

        with (
            patch("services.keywords.db_cache.TagAliasCache._initialized", True),
            patch(
                "services.keywords.db_cache.TagAliasCache.get_replacement",
                side_effect=lambda t: "tag_a, tag_b" if t == "combo" else ...,
            ),
        ):
            scenes = [{"image_prompt": "1girl, combo"}]
            _apply_tag_aliases(scenes)
            assert "tag_a" in scenes[0]["image_prompt"]
            assert "tag_b" in scenes[0]["image_prompt"]

    @patch("services.agent.nodes.finalize.get_db_session")
    def test_empty_prompt_skipped(self, mock_db_session):
        from services.agent.nodes.finalize import _apply_tag_aliases

        with patch("services.keywords.db_cache.TagAliasCache._initialized", True):
            scenes = [{"image_prompt": ""}]
            _apply_tag_aliases(scenes)
            assert scenes[0]["image_prompt"] == ""


# ── _flatten_tts_designs ─────────────────────────────────────────────


class TestFlattenTtsDesigns:
    """TTS 디자인 분해 테스트."""

    def test_extracts_fields(self):
        from services.agent.nodes.finalize import _flatten_tts_designs

        scenes = [
            {
                "tts_design": {
                    "voice_design_prompt": "soft female",
                    "emotion": "calm",
                    "pacing": {"head_padding": 0.3, "tail_padding": 0.5},
                }
            }
        ]
        _flatten_tts_designs(scenes)
        assert scenes[0]["voice_design_prompt"] == "soft female"
        assert scenes[0]["scene_emotion"] == "calm"
        assert scenes[0]["head_padding"] == 0.3
        assert scenes[0]["tail_padding"] == 0.5
        assert "tts_design" not in scenes[0]

    def test_skip_flag(self):
        from services.agent.nodes.finalize import _flatten_tts_designs

        scenes = [{"tts_design": {"skip": True}}]
        _flatten_tts_designs(scenes)
        assert "voice_design_prompt" not in scenes[0]

    def test_no_tts_design(self):
        from services.agent.nodes.finalize import _flatten_tts_designs

        scenes = [{"speaker": "A"}]
        _flatten_tts_designs(scenes)
        assert "voice_design_prompt" not in scenes[0]

    def test_partial_fields(self):
        from services.agent.nodes.finalize import _flatten_tts_designs

        scenes = [{"tts_design": {"voice_design_prompt": "deep male"}}]
        _flatten_tts_designs(scenes)
        assert scenes[0]["voice_design_prompt"] == "deep male"
        assert "scene_emotion" not in scenes[0]


# ── _merge_production_results ────────────────────────────────────────


class TestMergeProductionResults:
    """Production 결과 병합 테스트."""

    def test_merges_tts_to_scenes(self):
        from services.agent.nodes.finalize import _merge_production_results

        state = {
            "cinematographer_result": {
                "scenes": [{"image_prompt": "a"}, {"image_prompt": "b"}],
            },
            "tts_designer_result": {
                "tts_designs": [{"voice_design_prompt": "v1"}, {"voice_design_prompt": "v2"}],
            },
            "sound_designer_result": {"recommendation": {"bgm": "piano"}},
            "copyright_reviewer_result": {"status": "ok"},
        }
        scenes, sound, copyright_ = _merge_production_results(state)
        assert len(scenes) == 2
        assert scenes[0]["tts_design"]["voice_design_prompt"] == "v1"
        assert sound == {"bgm": "piano"}
        assert copyright_ == {"status": "ok"}

    def test_empty_results(self):
        from services.agent.nodes.finalize import _merge_production_results

        state = {}
        scenes, sound, copyright_ = _merge_production_results(state)
        assert scenes == []
        assert sound is None
        assert copyright_ is None


# ── _ensure_minimum_duration ─────────────────────────────────────────


class TestEnsureMinimumDuration:
    """Duration 최소 보정 테스트."""

    def test_sufficient_duration_skipped(self):
        from services.agent.nodes.finalize import _ensure_minimum_duration

        scenes = [{"duration": 15}, {"duration": 15}, {"duration": 15}]
        _ensure_minimum_duration(scenes, 45, "Korean")
        assert sum(s["duration"] for s in scenes) == 45

    def test_empty_scenes_skipped(self):
        from services.agent.nodes.finalize import _ensure_minimum_duration

        _ensure_minimum_duration([], 30, "Korean")  # 에러 안 남

    def test_zero_duration_skipped(self):
        from services.agent.nodes.finalize import _ensure_minimum_duration

        scenes = [{"duration": 0}, {"duration": 0}]
        _ensure_minimum_duration(scenes, 30, "Korean")
        assert sum(s["duration"] for s in scenes) == 0

    @patch("services.agent.nodes._revise_expand.redistribute_durations")
    def test_deficit_triggers_redistribution(self, mock_redist):
        """85% 미만 → redistribute_durations 호출."""
        from services.agent.nodes.finalize import _ensure_minimum_duration

        scenes = [{"duration": 5}, {"duration": 5}]  # 10s / 45s = 22%
        _ensure_minimum_duration(scenes, 45, "Korean")
        mock_redist.assert_called_once_with(scenes, 45, "Korean")


# ── _build_scene_to_tags_map ─────────────────────────────────────────


class TestBuildSceneToTagsMap:
    """writer_plan.locations → scene_idx→tags 매핑 테스트."""

    def test_basic_mapping(self):
        from services.agent.nodes.finalize import _build_scene_to_tags_map

        plan = {
            "locations": [
                {"scenes": [0, 1], "tags": ["park", "outdoors"]},
                {"scenes": [2], "tags": ["classroom", "indoors"]},
            ]
        }
        result = _build_scene_to_tags_map(plan)
        assert result[0] == ["park", "outdoors"]
        assert result[1] == ["park", "outdoors"]
        assert result[2] == ["classroom", "indoors"]

    def test_empty_locations(self):
        from services.agent.nodes.finalize import _build_scene_to_tags_map

        assert _build_scene_to_tags_map({"locations": []}) == {}

    def test_no_locations_key(self):
        from services.agent.nodes.finalize import _build_scene_to_tags_map

        assert _build_scene_to_tags_map({}) == {}


# ── _inject_location_map_tags ────────────────────────────────────────


class TestInjectLocationMapTags:
    """Location Map 기반 환경 태그 교정 테스트."""

    def test_injects_location_tags(self):
        from services.agent.nodes.finalize import _inject_location_map_tags

        scenes = [{"context_tags": {}}]
        plan = {"locations": [{"scenes": [0], "tags": ["park", "outdoors"]}]}
        _inject_location_map_tags(scenes, plan)
        env = scenes[0]["context_tags"]["environment"]
        assert "park" in env
        assert "outdoors" in env

    def test_drops_hallucinated_tags(self):
        from services.agent.nodes.finalize import _inject_location_map_tags

        scenes = [
            {
                "context_tags": {"environment": ["park", "space_station"]},
                "image_prompt": "1girl, park, space_station",
            }
        ]
        plan = {"locations": [{"scenes": [0], "tags": ["park", "outdoors"]}]}
        _inject_location_map_tags(scenes, plan)
        env = scenes[0]["context_tags"]["environment"]
        assert "space_station" not in env
        assert "park" in env
        # image_prompt에서도 제거됨
        assert "space_station" not in scenes[0]["image_prompt"]

    def test_no_plan_skipped(self):
        from services.agent.nodes.finalize import _inject_location_map_tags

        scenes = [{"context_tags": {"environment": "park"}}]
        _inject_location_map_tags(scenes, None)
        assert scenes[0]["context_tags"]["environment"] == "park"

    def test_no_context_tags_creates_new(self):
        from services.agent.nodes.finalize import _inject_location_map_tags

        scenes = [{}]
        plan = {"locations": [{"scenes": [0], "tags": ["forest"]}]}
        _inject_location_map_tags(scenes, plan)
        assert scenes[0]["context_tags"]["environment"] == ["forest"]

    def test_string_environment_coerced(self):
        from services.agent.nodes.finalize import _inject_location_map_tags

        scenes = [{"context_tags": {"environment": "park"}}]
        plan = {"locations": [{"scenes": [0], "tags": ["park", "outdoors"]}]}
        _inject_location_map_tags(scenes, plan)
        env = scenes[0]["context_tags"]["environment"]
        assert isinstance(env, list)
        assert "park" in env

    def test_unmatched_scene_skipped(self):
        from services.agent.nodes.finalize import _inject_location_map_tags

        scenes = [{"context_tags": {"environment": "beach"}}]
        plan = {"locations": [{"scenes": [5], "tags": ["park"]}]}  # scene 5 only
        _inject_location_map_tags(scenes, plan)
        assert scenes[0]["context_tags"]["environment"] == "beach"


# ── _inject_location_negative_tags ───────────────────────────────────


class TestInjectLocationNegativeTags:
    """indoor/outdoor negative 태그 주입 테스트."""

    def test_indoor_adds_outdoors_negative(self):
        from services.agent.nodes.finalize import _inject_location_negative_tags

        scenes = [{"negative_prompt": "lowres"}]
        plan = {"locations": [{"scenes": [0], "tags": ["classroom", "indoors"]}]}
        _inject_location_negative_tags(scenes, plan)
        assert "outdoors" in scenes[0]["negative_prompt"]

    def test_outdoor_adds_indoors_negative(self):
        from services.agent.nodes.finalize import _inject_location_negative_tags

        scenes = [{"negative_prompt": "lowres"}]
        plan = {"locations": [{"scenes": [0], "tags": ["park", "outdoors"]}]}
        _inject_location_negative_tags(scenes, plan)
        assert "indoors" in scenes[0]["negative_prompt"]

    def test_mixed_indoor_outdoor_skipped(self):
        from services.agent.nodes.finalize import _inject_location_negative_tags

        scenes = [{"negative_prompt": "lowres"}]
        plan = {"locations": [{"scenes": [0], "tags": ["indoors", "outdoors"]}]}
        _inject_location_negative_tags(scenes, plan)
        assert scenes[0]["negative_prompt"] == "lowres"

    def test_no_plan_skipped(self):
        from services.agent.nodes.finalize import _inject_location_negative_tags

        scenes = [{"negative_prompt": "lowres"}]
        _inject_location_negative_tags(scenes, None)
        assert scenes[0]["negative_prompt"] == "lowres"

    def test_empty_negative_prompt(self):
        from services.agent.nodes.finalize import _inject_location_negative_tags

        scenes = [{}]
        plan = {"locations": [{"scenes": [0], "tags": ["classroom", "indoors"]}]}
        _inject_location_negative_tags(scenes, plan)
        assert scenes[0]["negative_prompt"] == "outdoors"

    def test_duplicate_not_added(self):
        from services.agent.nodes.finalize import _inject_location_negative_tags

        scenes = [{"negative_prompt": "lowres, outdoors"}]
        plan = {"locations": [{"scenes": [0], "tags": ["classroom", "indoors"]}]}
        _inject_location_negative_tags(scenes, plan)
        assert scenes[0]["negative_prompt"].count("outdoors") == 1


# ── _auto_populate_scene_flags ───────────────────────────────────────


class TestAutoPopulateSceneFlags:
    """씬별 생성 플래그 자동 할당 테스트."""

    def test_character_scene_gets_all_flags(self):
        from services.agent.nodes.finalize import _auto_populate_scene_flags

        scenes = [{"speaker": "A", "context_tags": {"pose": "standing"}}]
        _auto_populate_scene_flags(scenes, character_id=1)
        s = scenes[0]
        assert s["use_controlnet"] is True
        assert s["use_ip_adapter"] is True
        assert s["multi_gen_enabled"] is not None
        assert s.get("controlnet_pose") is not None

    def test_narrator_no_controlnet(self):
        from services.agent.nodes.finalize import _auto_populate_scene_flags

        scenes = [{"speaker": "Narrator"}]
        _auto_populate_scene_flags(scenes, character_id=1)
        assert scenes[0]["use_controlnet"] is False
        assert scenes[0]["use_ip_adapter"] is False

    def test_no_character_id(self):
        from services.agent.nodes.finalize import _auto_populate_scene_flags

        scenes = [{"speaker": "A"}]
        _auto_populate_scene_flags(scenes, character_id=None)
        assert scenes[0]["use_ip_adapter"] is False

    def test_speaker_b_uses_character_b_id(self):
        from services.agent.nodes.finalize import _auto_populate_scene_flags

        scenes = [
            {"speaker": "A", "context_tags": {"pose": "standing"}},
            {"speaker": "B", "context_tags": {"pose": "standing"}},
        ]
        _auto_populate_scene_flags(scenes, character_id=1, character_b_id=2)
        assert scenes[0]["use_ip_adapter"] is True
        assert scenes[1]["use_ip_adapter"] is True

    def test_existing_flags_preserved(self):
        from services.agent.nodes.finalize import _auto_populate_scene_flags

        scenes = [
            {
                "speaker": "A",
                "use_controlnet": False,
                "use_ip_adapter": False,
                "multi_gen_enabled": False,
            }
        ]
        _auto_populate_scene_flags(scenes, character_id=1)
        assert scenes[0]["use_controlnet"] is False
        assert scenes[0]["use_ip_adapter"] is False
        assert scenes[0]["multi_gen_enabled"] is False


# ── _populate_character_actions ──────────────────────────────────────


class TestPopulateCharacterActions:
    """character_actions 변환 테스트."""

    @patch("services.characters.auto_populate_character_actions")
    def test_calls_auto_populate(self, mock_auto):
        from services.agent.nodes.finalize import _populate_character_actions

        scenes = [{"speaker": "A", "character_actions": {"expression": "smile"}}]
        db = MagicMock()
        _populate_character_actions(scenes, character_id=1, character_b_id=None, db=db)
        mock_auto.assert_called_once_with(scenes, 1, None, db)

    @patch(
        "services.characters.auto_populate_character_actions",
        side_effect=Exception("DB error"),
    )
    def test_exception_non_fatal(self, mock_auto):
        from services.agent.nodes.finalize import _populate_character_actions

        scenes = [{"speaker": "A"}]
        db = MagicMock()
        _populate_character_actions(scenes, character_id=1, character_b_id=None, db=db)
        # 에러 발생해도 예외 전파 안 됨


# ══════════════════════════════════════════════════════════════════════
# _context_tag_utils.py — 잔여 미커버 분기
# ══════════════════════════════════════════════════════════════════════


class TestValidateContextTagCategoriesEdgeCases:
    """카테고리 재분류 — 잔여 분기 커버."""

    def test_tag_no_valid_category_dropped(self):
        """어떤 카테고리에도 매칭되지 않는 misplaced 태그 → drop."""
        scenes = [{"context_tags": {"expression": "totally_invalid_xyz_tag"}}]
        validate_context_tag_categories(scenes)
        ctx = scenes[0]["context_tags"]
        assert "expression" not in ctx  # 삭제됨
        # 다른 카테고리에도 재분류되지 않음
        assert "gaze" not in ctx
        assert "pose" not in ctx


class TestDiversifyExpressionsEdgeCases:
    """Expression 보정 — 세부 분기 커버."""

    def _make_scenes(self, expressions, emotions=None, scripts=None):
        scenes = []
        for i, expr in enumerate(expressions):
            ctx = {"expression": expr}
            if emotions and emotions[i]:
                ctx["emotion"] = emotions[i]
            scene = {"speaker": "A", "context_tags": ctx}
            if scripts and scripts[i]:
                scene["script"] = scripts[i]
            scenes.append(scene)
        return scenes

    def test_no_context_tags_skipped(self):
        """context_tags 없는 씬은 건너뜀."""
        scenes = [
            {"speaker": "A", "context_tags": {"expression": "smile"}},
            {"speaker": "A"},  # no context_tags
            {"speaker": "A", "context_tags": {"expression": "smile"}, "script": "슬퍼"},
            {"speaker": "A", "context_tags": {"expression": "smile"}, "script": "화나"},
        ]
        diversify_expressions(scenes)  # 에러 안 남

    def test_different_expression_preserved(self):
        """이미 dominant가 아닌 expression은 교체 안 됨."""
        scenes = self._make_scenes(
            expressions=["smile", "smile", "smile", "angry"],
            scripts=["슬퍼", "화나", "걱정돼", None],
        )
        diversify_expressions(scenes)
        assert scenes[3]["context_tags"]["expression"] == "angry"  # 유지

    def test_no_script_match_skipped(self):
        """스크립트에 키워드 없으면 교체 안 됨."""
        scenes = self._make_scenes(
            expressions=["smile"] * 4,
            scripts=["좋은 아침", "오늘도 좋은 날", "감사합니다", "괜찮아요"],
        )
        diversify_expressions(scenes)
        # "감사" → happy → smile (dominant과 같음) → 교체 안 됨
        exprs = [s["context_tags"]["expression"] for s in scenes]
        # 매칭 안 되거나 derived가 dominant와 같으면 유지
        assert exprs.count("smile") >= 3


class TestDiversifyGazesEdgeCases:
    """Gaze 교정 — 세부 분기 커버."""

    def _make_scenes(self, gazes, emotions=None):
        scenes = []
        for i, gaze in enumerate(gazes):
            emotion = emotions[i] if emotions else None
            ctx = {"gaze": gaze}
            if emotion:
                ctx["emotion"] = emotion
            scenes.append({"speaker": "A", "context_tags": ctx})
        return scenes

    def test_no_context_tags_skipped(self):
        """context_tags 없는 씬은 건너뜀."""
        scenes = self._make_scenes(
            gazes=["looking_at_viewer"] * 3,
            emotions=["sad", "happy", "calm"],
        )
        scenes.insert(1, {"speaker": "A"})  # no context_tags
        diversify_gazes(scenes)  # 에러 안 남

    def test_non_dominant_gaze_not_changed(self):
        """dominant가 아닌 gaze는 건드리지 않음."""
        scenes = self._make_scenes(
            gazes=["looking_at_viewer", "looking_at_viewer", "looking_at_viewer", "looking_down"],
            emotions=["sad", "happy", "calm", "sad"],
        )
        diversify_gazes(scenes)
        assert scenes[3]["context_tags"]["gaze"] == "looking_down"  # 유지

    def test_all_alternatives_exhausted(self):
        """모든 대안이 prev/dominant와 같으면 continue."""
        # all 5 emotions map to looking_down → consecutive 중복 → 대안 검색
        scenes = self._make_scenes(
            gazes=["looking_down"] * 5,
            emotions=["sad", "sad", "sad", "sad", "sad"],
        )
        diversify_gazes(scenes)
        # 최소한 에러 없이 완료


class TestDiversifyActionsEdgeCases:
    """Action 교정 — 세부 분기 커버."""

    def _make_scenes(self, actions, emotions=None):
        scenes = []
        for i, action in enumerate(actions):
            ctx = {"action": action}
            if emotions and emotions[i]:
                ctx["emotion"] = emotions[i]
            scenes.append({"speaker": "A", "context_tags": ctx})
        return scenes

    def test_no_context_tags_skipped(self):
        """context_tags 없는 씬은 건너뜀."""
        scenes = self._make_scenes(
            actions=["waving"] * 3,
            emotions=["sad", "happy", "calm"],
        )
        scenes.insert(1, {"speaker": "A"})
        diversify_actions(scenes)

    def test_non_dominant_action_not_changed(self):
        """dominant가 아닌 action은 유지."""
        scenes = self._make_scenes(
            actions=["waving", "waving", "waving", "sitting"],
            emotions=["sad", "happy", "calm", "calm"],
        )
        diversify_actions(scenes)
        assert scenes[3]["context_tags"]["action"] == "sitting"

    def test_suggested_equals_dominant_skipped(self):
        """emotion 매핑 결과가 dominant와 같으면 건너뜀."""
        # happy → waving, but dominant is waving → skip
        scenes = self._make_scenes(
            actions=["waving"] * 4,
            emotions=["happy", "happy", "happy", "happy"],
        )
        diversify_actions(scenes)
        # happy → waving == dominant → 교체 불가
        actions = [s["context_tags"]["action"] for s in scenes]
        assert all(a == "waving" for a in actions)

    def test_consecutive_duplicate_fallback(self):
        """연속 중복 방지 → _EMOTION_TO_ACTION.values() 대안 검색."""
        # All same emotion → same suggested → needs fallback
        scenes = self._make_scenes(
            actions=["waving"] * 5,
            emotions=["sad", "sad", "sad", "sad", "sad"],
        )
        diversify_actions(scenes)
        actions = [s["context_tags"]["action"] for s in scenes]
        # 최소한 일부는 교체됨
        assert actions.count("waving") < 5


# ── Fix 1: negative prompt 빈 문자열 strip 방어 ──────────────────────


class TestInjectNegativePromptsStrip:
    """빈 문자열/공백만 있는 negative_prompt에 기본값 주입 테스트."""

    def test_whitespace_only_gets_default(self):
        from config import DEFAULT_SCENE_NEGATIVE_PROMPT
        from services.agent.nodes.finalize import _inject_negative_prompts

        scenes = [{"negative_prompt": "   "}]
        _inject_negative_prompts(scenes)
        assert scenes[0]["negative_prompt"] == DEFAULT_SCENE_NEGATIVE_PROMPT

    def test_newline_only_gets_default(self):
        from config import DEFAULT_SCENE_NEGATIVE_PROMPT
        from services.agent.nodes.finalize import _inject_negative_prompts

        scenes = [{"negative_prompt": "\n\t"}]
        _inject_negative_prompts(scenes)
        assert scenes[0]["negative_prompt"] == DEFAULT_SCENE_NEGATIVE_PROMPT

    def test_none_gets_default(self):
        from config import DEFAULT_SCENE_NEGATIVE_PROMPT
        from services.agent.nodes.finalize import _inject_negative_prompts

        scenes = [{"negative_prompt": None}]
        _inject_negative_prompts(scenes)
        assert scenes[0]["negative_prompt"] == DEFAULT_SCENE_NEGATIVE_PROMPT

    def test_valid_value_preserved(self):
        from services.agent.nodes.finalize import _inject_negative_prompts

        scenes = [{"negative_prompt": "custom_neg"}]
        _inject_negative_prompts(scenes)
        assert scenes[0]["negative_prompt"] == "custom_neg"


# ── Fix 2: mood fallback 테스트 ─────────────────────────────────────


class TestMoodFallback:
    """emotion 없을 때 mood에 DEFAULT_MOOD_TAG 주입 테스트."""

    def test_no_emotion_gets_default_mood(self):
        from config import DEFAULT_MOOD_TAG
        from services.agent.nodes.finalize import _inject_default_context_tags

        scenes = [{"speaker": "A", "context_tags": {}}]
        _inject_default_context_tags(scenes)
        assert scenes[0]["context_tags"]["mood"] == DEFAULT_MOOD_TAG

    def test_unknown_emotion_gets_default_mood(self):
        """derive_mood_from_emotion이 None 반환 시 기본값."""
        from config import DEFAULT_MOOD_TAG
        from services.agent.nodes.finalize import _inject_default_context_tags

        scenes = [{"speaker": "A", "context_tags": {"emotion": "zzz_nonexistent"}}]
        _inject_default_context_tags(scenes)
        assert scenes[0]["context_tags"]["mood"] == DEFAULT_MOOD_TAG

    def test_existing_mood_preserved(self):
        from services.agent.nodes.finalize import _inject_default_context_tags

        scenes = [{"speaker": "A", "context_tags": {"mood": "melancholic"}}]
        _inject_default_context_tags(scenes)
        assert scenes[0]["context_tags"]["mood"] == "melancholic"

    def test_valid_emotion_derives_mood(self):
        from services.agent.nodes.finalize import _inject_default_context_tags

        scenes = [{"speaker": "A", "context_tags": {"emotion": "angry"}}]
        _inject_default_context_tags(scenes)
        # angry → tense (derive_mood_from_emotion)
        assert scenes[0]["context_tags"]["mood"] is not None
        assert scenes[0]["context_tags"]["mood"] != "neutral"


# ── Fix 3: EXCLUSIVE identity 태그 필터링 테스트 ─────────────────────


class TestFilterExclusiveIdentityTags:
    """Cinematographer image_prompt에서 EXCLUSIVE 그룹 충돌 태그 제거 테스트."""

    @staticmethod
    def _make_db(char_tags: list[tuple[str, str]], tag_group_map: dict[str, str | None]):
        """Mock DB that dispatches Character vs Tag queries properly.

        Args:
            char_tags: [(tag_name, group_name), ...] — 캐릭터 소유 태그
            tag_group_map: {bare_tag_name: group_name} — Tag 테이블 룩업
        """
        from models.character import Character

        char = MagicMock()
        mock_tags = []
        for tname, gname in char_tags:
            ct = MagicMock()
            ct.tag = MagicMock()
            ct.tag.name = tname
            ct.tag.group_name = gname
            mock_tags.append(ct)
        char.tags = mock_tags

        db = MagicMock()

        def _query(*models):
            q = MagicMock()
            is_character = any(m is Character for m in models)
            if is_character:
                q.options = MagicMock(return_value=q)  # joinedload chain
                q.filter = MagicMock(return_value=MagicMock(first=MagicMock(return_value=char)))
            else:
                # Tag 쿼리 (IN / 단건 모두 대응)
                def _filter(*_a, **_kw):
                    from types import SimpleNamespace

                    fq = MagicMock()
                    fq.all = MagicMock(
                        return_value=[SimpleNamespace(name=tn, group_name=gn) for tn, gn in tag_group_map.items()],
                    )
                    fq.first = MagicMock(return_value=None)
                    return fq

                q.filter = _filter
            return q

        db.query = MagicMock(side_effect=_query)
        return db

    def test_conflicting_tag_removed(self):
        """dark_hair가 black_hair 캐릭터의 image_prompt에서 제거."""
        from services.agent.nodes.finalize import _filter_exclusive_identity_tags

        scenes = [
            {"speaker": "A", "image_prompt": "1girl, dark_hair, smile, cowboy_shot"},
        ]
        db = self._make_db(
            char_tags=[("black_hair", "hair_color")],
            tag_group_map={
                "dark_hair": "hair_color",
                "1girl": "subject",
                "smile": "expression",
                "cowboy_shot": "camera",
            },
        )

        _filter_exclusive_identity_tags(scenes, 1, None, db)
        assert "dark_hair" not in scenes[0]["image_prompt"]
        assert "1girl" in scenes[0]["image_prompt"]
        assert "smile" in scenes[0]["image_prompt"]
        assert "cowboy_shot" in scenes[0]["image_prompt"]

    def test_matching_tag_preserved(self):
        """캐릭터 DB 태그와 같은 태그는 제거하지 않음."""
        from services.agent.nodes.finalize import _filter_exclusive_identity_tags

        scenes = [
            {"speaker": "A", "image_prompt": "1girl, black_hair, smile"},
        ]
        db = self._make_db(
            char_tags=[("black_hair", "hair_color")],
            tag_group_map={
                "black_hair": "hair_color",
                "1girl": "subject",
                "smile": "expression",
            },
        )

        _filter_exclusive_identity_tags(scenes, 1, None, db)
        assert "black_hair" in scenes[0]["image_prompt"]

    def test_narrator_skipped(self):
        """Narrator 씬은 필터링하지 않음."""
        from services.agent.nodes.finalize import _filter_exclusive_identity_tags

        scenes = [
            {"speaker": "Narrator", "image_prompt": "dark_hair, landscape"},
        ]
        db = self._make_db(
            char_tags=[("black_hair", "hair_color")],
            tag_group_map={"dark_hair": "hair_color"},
        )

        _filter_exclusive_identity_tags(scenes, 1, None, db)
        assert "dark_hair" in scenes[0]["image_prompt"]

    def test_no_character_noop(self):
        """character_id=None이면 아무것도 안 함."""
        from services.agent.nodes.finalize import _filter_exclusive_identity_tags

        scenes = [{"speaker": "A", "image_prompt": "dark_hair, smile"}]
        db = MagicMock()
        _filter_exclusive_identity_tags(scenes, None, None, db)
        assert "dark_hair" in scenes[0]["image_prompt"]

    def test_non_exclusive_group_preserved(self):
        """EXCLUSIVE가 아닌 그룹 태그는 제거하지 않음."""
        from services.agent.nodes.finalize import _filter_exclusive_identity_tags

        scenes = [
            {"speaker": "A", "image_prompt": "1girl, smile, cowboy_shot"},
        ]
        db = self._make_db(
            char_tags=[("black_hair", "hair_color")],
            tag_group_map={
                "1girl": "subject",
                "smile": "expression",
                "cowboy_shot": "camera",
            },
        )

        _filter_exclusive_identity_tags(scenes, 1, None, db)
        assert "smile" in scenes[0]["image_prompt"]
        assert "cowboy_shot" in scenes[0]["image_prompt"]

    def test_unknown_tag_preserved(self):
        """DB에 없는 태그는 제거하지 않음."""
        from services.agent.nodes.finalize import _filter_exclusive_identity_tags

        scenes = [
            {"speaker": "A", "image_prompt": "1girl, some_unknown_tag, dark_hair"},
        ]
        db = self._make_db(
            char_tags=[("black_hair", "hair_color")],
            tag_group_map={"dark_hair": "hair_color", "1girl": "subject"},
        )

        _filter_exclusive_identity_tags(scenes, 1, None, db)
        assert "some_unknown_tag" in scenes[0]["image_prompt"]
        assert "dark_hair" not in scenes[0]["image_prompt"]

    def test_speaker_b_uses_char_b_exclusive(self):
        """Dialogue: Speaker B는 character_b의 EXCLUSIVE 태그 기준으로 필터링."""
        from models.character import Character
        from services.agent.nodes.finalize import _filter_exclusive_identity_tags

        scenes = [
            {"speaker": "A", "image_prompt": "1girl, dark_hair, smile"},
            {"speaker": "B", "image_prompt": "1boy, dark_eyes, smile"},
        ]

        # char_a(id=1): black_hair(hair_color), char_b(id=2): blue_eyes(eye_color)
        char_a = MagicMock()
        ct_a = MagicMock()
        ct_a.tag = MagicMock()
        ct_a.tag.name = "black_hair"
        ct_a.tag.group_name = "hair_color"
        char_a.tags = [ct_a]

        char_b = MagicMock()
        ct_b = MagicMock()
        ct_b.tag = MagicMock()
        ct_b.tag.name = "blue_eyes"
        ct_b.tag.group_name = "eye_color"
        char_b.tags = [ct_b]

        tag_map = {
            "dark_hair": "hair_color",
            "dark_eyes": "eye_color",
            "1girl": "subject",
            "1boy": "subject",
            "smile": "expression",
        }

        db = MagicMock()
        char_call_count = [0]

        def _query(*models):
            q = MagicMock()
            is_character = any(m is Character for m in models)
            if is_character:
                q.options = MagicMock(return_value=q)  # joinedload chain

                def _char_filter(*_a, **_kw):
                    char_call_count[0] += 1
                    fq = MagicMock()
                    fq.first = MagicMock(
                        return_value=char_a if char_call_count[0] <= 1 else char_b,
                    )
                    return fq

                q.filter = _char_filter
            else:

                def _tag_filter(*_a, **_kw):
                    from types import SimpleNamespace

                    fq = MagicMock()
                    fq.all = MagicMock(
                        return_value=[SimpleNamespace(name=tn, group_name=gn) for tn, gn in tag_map.items()],
                    )
                    return fq

                q.filter = _tag_filter
            return q

        db.query = MagicMock(side_effect=_query)

        _filter_exclusive_identity_tags(scenes, 1, 2, db)
        # Speaker A: dark_hair → hair_color, char_a has black_hair → 제거
        assert "dark_hair" not in scenes[0]["image_prompt"]
        assert "smile" in scenes[0]["image_prompt"]
        # Speaker B: dark_eyes → eye_color, char_b has blue_eyes → 제거
        assert "dark_eyes" not in scenes[1]["image_prompt"]
        assert "smile" in scenes[1]["image_prompt"]
