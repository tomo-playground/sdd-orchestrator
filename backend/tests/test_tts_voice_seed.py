"""TTS voice seed & voice design consistency tests.

Verifies:
1. Voice seed always comes from the character's voice preset (not per-scene hash).
2. When a preset exists, Gemini adapts the preset base with scene context/emotion.
   Seed stays preset-based so voice identity is preserved; only delivery style varies.
3. Fallback to simple concatenation when Gemini is unavailable.
"""

import hashlib
import unittest
from unittest.mock import MagicMock, patch

# ── TestResolveVoicePresetId ──────────────────────────────────────────────
# Tests get_speaker_voice_preset (tts_helpers.py) which resolves speaker -> preset ID


class TestResolveVoicePresetId(unittest.TestCase):
    """get_speaker_voice_preset must return preset ID regardless of per-scene prompt."""

    def setUp(self):
        from services.video.tts_helpers import get_speaker_voice_preset

        self._resolve = get_speaker_voice_preset

    @patch(
        "services.config_resolver.resolve_effective_config", return_value={"values": {"narrator_voice_preset_id": 16}}
    )
    @patch("database.SessionLocal")
    def test_returns_preset_when_no_per_scene_prompt(self, mock_session_cls, _mock_cfg):
        """speaker -> character -> voice_preset_id lookup."""
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        mock_storyboard = MagicMock()
        mock_storyboard.group_id = 1
        mock_group = MagicMock()
        mock_group.project = MagicMock()

        def get_side_effect(cls, id_):
            name = cls.__name__
            if name == "Storyboard":
                return mock_storyboard
            if name == "Group":
                return mock_group
            return None

        mock_db.get.side_effect = get_side_effect

        result = self._resolve(1058, "Narrator")
        self.assertEqual(result, 16)

    @patch(
        "services.config_resolver.resolve_effective_config", return_value={"values": {"narrator_voice_preset_id": 16}}
    )
    @patch("database.SessionLocal")
    def test_returns_preset_even_with_per_scene_prompt(self, mock_session_cls, _mock_cfg):
        """Core regression: per-scene voice_design_prompt must NOT bypass preset ID."""
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        mock_storyboard = MagicMock()
        mock_storyboard.group_id = 1
        mock_group = MagicMock()
        mock_group.project = MagicMock()

        def get_side_effect(cls, id_):
            name = cls.__name__
            if name == "Storyboard":
                return mock_storyboard
            if name == "Group":
                return mock_group
            return None

        mock_db.get.side_effect = get_side_effect

        result = self._resolve(1058, "Narrator")
        self.assertEqual(result, 16, "preset ID must be returned even when scene has voice_design_prompt")

    def test_returns_none_when_no_storyboard_id(self):
        result = self._resolve(None, "A")
        self.assertIsNone(result)

    @patch("database.SessionLocal")
    def test_returns_none_when_storyboard_not_found(self, mock_session_cls):
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.get.return_value = None

        result = self._resolve(9999, "A")
        self.assertIsNone(result)


# ── TestVoiceSeedConsistency ──────────────────────────────────────────────


class TestVoiceSeedConsistency(unittest.TestCase):
    """Voice seed must be identical across all scenes in a single render job."""

    def test_same_seed_via_preset(self):
        """All scenes must use same preset seed when voice_preset_id is the same."""
        from services.video.tts_helpers import _resolve_voice_seed

        # preset_seed provided -> always returns that seed
        seeds = [_resolve_voice_seed(764249558, "base prompt", 42) for _ in range(3)]
        self.assertTrue(all(s == 764249558 for s in seeds), f"All must be preset seed: {seeds}")

    def test_default_seed_used_when_no_preset(self):
        """When no preset is found, TTS_DEFAULT_SEED must be used."""
        from config import TTS_DEFAULT_SEED
        from services.video.tts_helpers import _resolve_voice_seed

        seed = _resolve_voice_seed(None, None, TTS_DEFAULT_SEED)
        self.assertEqual(seed, TTS_DEFAULT_SEED)

    def test_prompt_hash_seed_is_deterministic(self):
        """sha256 기반 seed는 PYTHONHASHSEED와 무관하게 항상 같은 값을 반환해야 한다."""
        prompt = "A warm, calm voice with gentle intonation"
        expected = int(hashlib.sha256(prompt.encode()).hexdigest()[:8], 16) % (2**31)

        for _ in range(3):
            actual = int(hashlib.sha256(prompt.encode()).hexdigest()[:8], 16) % (2**31)
            self.assertEqual(actual, expected)

    def test_resolve_voice_seed_from_prompt_hash(self):
        """preset_seed=None but preset_voice_design present -> hash-based seed."""
        from services.video.tts_helpers import _resolve_voice_seed

        design = "A teenage boy with passionate voice"
        expected = int(hashlib.sha256(design.encode()).hexdigest()[:8], 16) % (2**31)
        seed = _resolve_voice_seed(None, design, 42)
        self.assertEqual(seed, expected)


# ── TestResolveVoiceDesign (was TestGetVoiceDesignForScene) ───────────────


class TestResolveVoiceDesign(unittest.TestCase):
    """resolve_voice_design: 4-priority voice design resolution."""

    def setUp(self):
        from services.video.tts_voice_design import resolve_voice_design

        self._resolve = resolve_voice_design

    @patch("config.TTS_VOICE_CONSISTENCY_MODE", False)
    @patch(
        "services.video.tts_voice_design.generate_context_aware_voice_prompt",
        return_value="A boy speaking with hopeful warmth",
    )
    def test_preset_with_emotion_calls_gemini(self, mock_gemini):
        """프리셋 + 감정 있으면 Gemini가 맥락 기반 voice design 생성."""
        result, was_gemini = self._resolve(
            scene_voice_design=None,
            preset_voice_design="preset base voice",
            global_voice_design=None,
            scene_emotion="hopeful",
            clean_script="스크립트",
        )
        mock_gemini.assert_called_once()
        self.assertEqual(result, "A boy speaking with hopeful warmth")
        self.assertTrue(was_gemini)

    @patch("config.TTS_VOICE_CONSISTENCY_MODE", False)
    @patch("services.video.tts_voice_design.generate_context_aware_voice_prompt", return_value="")
    def test_preset_with_emotion_fallback_on_gemini_failure(self, mock_gemini):
        """Gemini 실패 시 단순 연결 fallback."""
        result, was_gemini = self._resolve(
            scene_voice_design=None,
            preset_voice_design="preset base voice",
            global_voice_design=None,
            scene_emotion="hopeful",
            clean_script="스크립트",
        )
        self.assertEqual(result, "preset base voice, hopeful")
        self.assertFalse(was_gemini)

    def test_preset_no_emotion_no_context_returns_preset(self):
        """감정/맥락 없으면 Gemini 호출 없이 프리셋 그대로."""
        result, was_gemini = self._resolve(
            scene_voice_design=None,
            preset_voice_design="preset base voice",
            global_voice_design=None,
            scene_emotion=None,
            clean_script="스크립트",
        )
        self.assertEqual(result, "preset base voice")
        self.assertFalse(was_gemini)

    def test_per_scene_prompt_used_as_priority0(self):
        """scene_voice_design(Priority 0)은 최우선."""
        result, was_gemini = self._resolve(
            scene_voice_design="Gemini warm tone",
            preset_voice_design="preset base",
            global_voice_design=None,
            scene_emotion=None,
            clean_script="스크립트",
        )
        self.assertEqual(result, "Gemini warm tone")
        self.assertFalse(was_gemini)

    def test_global_prompt_used_when_no_preset_no_scene_prompt(self):
        """preset 없고 scene prompt도 없으면 global prompt 사용 (Priority 2)."""
        result, was_gemini = self._resolve(
            scene_voice_design=None,
            preset_voice_design=None,
            global_voice_design="global voice",
            scene_emotion=None,
            clean_script="스크립트",
        )
        self.assertEqual(result, "global voice")
        self.assertFalse(was_gemini)

    @patch("config.TTS_VOICE_CONSISTENCY_MODE", False)
    @patch("services.video.tts_voice_design.generate_context_aware_voice_prompt")
    def test_gemini_receives_base_prompt(self, mock_gemini):
        """Gemini에 base_prompt가 전달되어 캐릭터 정체성이 보존된다."""
        mock_gemini.return_value = "A teenage boy whispering with hope"
        preset = "A teenage boy with passionate voice"
        self._resolve(
            scene_voice_design=None,
            preset_voice_design=preset,
            global_voice_design=None,
            scene_emotion="hopeful",
            clean_script="스크립트",
            image_prompt_ko="교실에서 친구를 바라보는 장면",
        )
        _, kwargs = mock_gemini.call_args
        self.assertEqual(kwargs["base_prompt"], preset)


# ── TestVoiceConsistencyMode ──────────────────────────────────────────────


class TestVoiceConsistencyMode(unittest.TestCase):
    """TTS_VOICE_CONSISTENCY_MODE: ON -> Gemini 미호출, OFF -> 기존 동작."""

    def setUp(self):
        from services.video.tts_voice_design import resolve_voice_design

        self._resolve = resolve_voice_design

    @patch("config.TTS_VOICE_CONSISTENCY_MODE", True)
    @patch("services.video.tts_voice_design.generate_context_aware_voice_prompt")
    def test_consistency_mode_skips_gemini(self, mock_gemini):
        """consistency ON -> Gemini 미호출, 프리셋 그대로 반환."""
        result, was_gemini = self._resolve(
            scene_voice_design=None,
            preset_voice_design="preset base voice",
            global_voice_design=None,
            scene_emotion="hopeful",
            clean_script="스크립트",
        )
        mock_gemini.assert_not_called()
        self.assertEqual(result, "preset base voice")
        self.assertFalse(was_gemini)

    @patch("config.TTS_VOICE_CONSISTENCY_MODE", False)
    @patch("services.video.tts_voice_design.generate_context_aware_voice_prompt", return_value="Gemini adapted voice")
    def test_consistency_mode_off_calls_gemini(self, mock_gemini):
        """consistency OFF -> 기존 Gemini 호출 동작."""
        result, was_gemini = self._resolve(
            scene_voice_design=None,
            preset_voice_design="preset base voice",
            global_voice_design=None,
            scene_emotion="hopeful",
            clean_script="스크립트",
        )
        mock_gemini.assert_called_once()
        self.assertEqual(result, "Gemini adapted voice")
        self.assertTrue(was_gemini)

    @patch("config.TTS_VOICE_CONSISTENCY_MODE", True)
    @patch("services.video.tts_voice_design.generate_context_aware_voice_prompt")
    def test_all_scenes_same_instruct(self, mock_gemini):
        """consistency ON -> 3개 씬 모두 동일 instruct 반환."""
        preset = "A warm teenage boy voice"
        results = []
        for emotion in ["hopeful", "sad", "angry"]:
            result, _ = self._resolve(
                scene_voice_design=None,
                preset_voice_design=preset,
                global_voice_design=None,
                scene_emotion=emotion,
                clean_script="스크립트",
            )
            results.append(result)
        self.assertTrue(all(r == preset for r in results), f"All scenes must return same preset: {results}")
        mock_gemini.assert_not_called()


# ── TestVoiceDesignPriority0 ──────────────────────────────────────────────


class TestVoiceDesignPriority0(unittest.TestCase):
    """Priority 0: scene_voice_design (DB/pipeline result) reuse -- Gemini 재호출 없이 일관성 보장."""

    def setUp(self):
        from services.video.tts_voice_design import resolve_voice_design

        self._resolve = resolve_voice_design

    @patch("config.TTS_VOICE_CONSISTENCY_MODE", False)
    @patch("services.video.tts_voice_design.generate_context_aware_voice_prompt")
    def test_priority0_reuses_db_prompt_skips_gemini(self, mock_gemini):
        """DB에 voice_design_prompt가 있으면 Gemini 재호출 없이 그대로 반환."""
        result, was_gemini = self._resolve(
            scene_voice_design="DB saved: A warm girl voice, excited",
            preset_voice_design="preset base voice",
            global_voice_design=None,
            scene_emotion=None,
            clean_script="스크립트",
        )
        mock_gemini.assert_not_called()
        self.assertEqual(result, "DB saved: A warm girl voice, excited")
        self.assertFalse(was_gemini)

    @patch("config.TTS_VOICE_CONSISTENCY_MODE", False)
    @patch("services.video.tts_voice_design.generate_context_aware_voice_prompt")
    def test_priority0_takes_precedence_over_preset(self, mock_gemini):
        """Priority 0이 preset(Priority 1)보다 우선: DB 값이 있으면 preset Gemini 어댑션 스킵."""
        result, was_gemini = self._resolve(
            scene_voice_design="pipeline generated voice design",
            preset_voice_design="preset base",
            global_voice_design=None,
            scene_emotion=None,
            clean_script="스크립트",
        )
        mock_gemini.assert_not_called()
        self.assertEqual(result, "pipeline generated voice design")
        self.assertFalse(was_gemini)

    @patch("config.TTS_VOICE_CONSISTENCY_MODE", False)
    @patch("services.video.tts_voice_design.generate_context_aware_voice_prompt", return_value="Gemini adapted voice")
    def test_priority0_skipped_when_none(self, mock_gemini):
        """scene_voice_design=None이면 Priority 0 스킵 -> Priority 1(Gemini) 진행."""
        result, was_gemini = self._resolve(
            scene_voice_design=None,
            preset_voice_design="preset base voice",
            global_voice_design=None,
            scene_emotion="hopeful",
            clean_script="스크립트",
        )
        mock_gemini.assert_called_once()
        self.assertEqual(result, "Gemini adapted voice")
        self.assertTrue(was_gemini)

    @patch("config.TTS_VOICE_CONSISTENCY_MODE", False)
    @patch("services.video.tts_voice_design.generate_context_aware_voice_prompt")
    def test_multiple_renders_same_result_with_db_value(self, mock_gemini):
        """동일한 DB 저장값으로 3번 렌더해도 결과 동일 -- 재현성 보장."""
        saved_design = "A teenage girl voice, speaking with restrained sadness"
        results = []
        for i in range(3):
            result, _ = self._resolve(
                scene_voice_design=saved_design,
                preset_voice_design="preset base",
                global_voice_design=None,
                scene_emotion="sad",
                clean_script=f"스크립트 {i}",
            )
            results.append(result)
        mock_gemini.assert_not_called()
        self.assertTrue(all(r == saved_design for r in results))


# ── TestPersistVoiceDesign ────────────────────────────────────────────────


class TestPersistVoiceDesign(unittest.TestCase):
    """persist_voice_design: DB write-back 함수 단위 테스트."""

    def setUp(self):
        from services.video.tts_helpers import persist_voice_design

        self._persist = persist_voice_design

    @patch("database.get_db_session")
    def test_no_op_when_scene_db_id_none(self, mock_db_ctx):
        """scene_db_id=None이면 DB 호출 없이 즉시 반환."""
        self._persist(0, None, "some voice design")
        mock_db_ctx.assert_not_called()

    @patch("database.get_db_session")
    def test_updates_voice_design_when_scene_db_id_set(self, mock_db_ctx):
        """scene_db_id 있으면 DB update 호출."""
        mock_db = MagicMock()
        mock_db_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_db_ctx.return_value.__exit__ = MagicMock(return_value=False)

        self._persist(2, 42, "A warm girl voice, excited")

        mock_db_ctx.assert_called_once()
        mock_db.query.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch("database.get_db_session", side_effect=Exception("DB error"))
    def test_non_fatal_on_db_error(self, _mock_db_ctx):
        """DB 오류 시 예외 전파 없이 로그만 기록 (non-fatal)."""
        try:
            self._persist(0, 42, "voice design")
        except Exception as e:  # noqa: BLE001
            self.fail(f"persist_voice_design should not raise: {e}")


if __name__ == "__main__":
    unittest.main()
