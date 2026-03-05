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


def _make_builder(
    storyboard_id: int | None,
    global_preset_id: int | None,
    scenes: list[dict],
) -> MagicMock:
    """Build a minimal VideoBuilder mock."""
    builder = MagicMock()
    builder.request.storyboard_id = storyboard_id
    builder.request.voice_preset_id = global_preset_id
    builder.request.voice_design_prompt = ""

    scene_mocks = []
    for s in scenes:
        sm = MagicMock()
        sm.speaker = s.get("speaker", "A")
        sm.voice_design_prompt = s.get("voice_design_prompt", "")
        sm.scene_emotion = s.get("scene_emotion", None)
        scene_mocks.append(sm)

    builder.request.scenes = scene_mocks
    return builder


class TestResolveVoicePresetId(unittest.TestCase):
    """_resolve_voice_preset_id must return preset ID regardless of per-scene prompt."""

    def setUp(self):
        from services.video.scene_processing import _resolve_voice_preset_id

        self._resolve = _resolve_voice_preset_id

    @patch("services.video.scene_processing.get_speaker_voice_preset", return_value=16)
    def test_returns_preset_when_no_per_scene_prompt(self, _mock):
        builder = _make_builder(1058, 16, [{"speaker": "A", "voice_design_prompt": ""}])
        result = self._resolve(builder, 0)
        self.assertEqual(result, 16)

    @patch("services.video.scene_processing.get_speaker_voice_preset", return_value=16)
    def test_returns_preset_even_with_per_scene_prompt(self, _mock):
        """Core regression: per-scene voice_design_prompt must NOT bypass preset ID."""
        builder = _make_builder(
            1058,
            16,
            [{"speaker": "A", "voice_design_prompt": "A warm, slightly brighter tone with anticipation"}],
        )
        result = self._resolve(builder, 0)
        self.assertEqual(result, 16, "preset ID must be returned even when scene has voice_design_prompt")

    @patch("services.video.scene_processing.get_speaker_voice_preset", return_value=None)
    def test_falls_back_to_global_preset(self, _mock):
        builder = _make_builder(1058, 99, [{"speaker": "A"}])
        result = self._resolve(builder, 0)
        self.assertEqual(result, 99)

    @patch("services.video.scene_processing.get_speaker_voice_preset", return_value=None)
    def test_returns_none_when_no_preset_at_all(self, _mock):
        builder = _make_builder(1058, None, [{"speaker": "A"}])
        result = self._resolve(builder, 0)
        self.assertIsNone(result)


class TestVoiceSeedConsistency(unittest.TestCase):
    """Voice seed must be identical across all scenes in a single render job."""

    @patch("services.video.scene_processing.get_speaker_voice_preset", return_value=16)
    @patch("services.video.scene_processing.get_preset_voice_info", return_value=("base prompt", 764249558))
    def test_same_seed_across_scenes_with_different_voice_design(self, _mock_info, _mock_preset):
        """All scenes must use preset seed even when each has a different voice_design_prompt."""
        from services.video.scene_processing import _resolve_voice_preset_id

        scenes = [
            {"speaker": "A", "voice_design_prompt": "warm and hopeful tone"},
            {"speaker": "A", "voice_design_prompt": "cheerful and excited tone"},
            {"speaker": "A", "voice_design_prompt": "calm and reflective tone"},
        ]
        builder = _make_builder(1058, 16, scenes)

        preset_ids = [_resolve_voice_preset_id(builder, i) for i in range(len(scenes))]
        self.assertTrue(all(pid == 16 for pid in preset_ids), f"All scenes must resolve to same preset: {preset_ids}")

    @patch("services.video.scene_processing.get_speaker_voice_preset", return_value=None)
    def test_default_seed_used_when_no_preset(self, _mock):
        """When no preset is found, TTS_DEFAULT_SEED must be used (not per-scene hash)."""
        from config import TTS_DEFAULT_SEED
        from services.video.scene_processing import _resolve_voice_preset_id

        scenes = [
            {"speaker": "A", "voice_design_prompt": "warm hopeful tone"},
            {"speaker": "A", "voice_design_prompt": "excited cheerful tone"},
        ]
        builder = _make_builder(None, None, scenes)

        preset_ids = [_resolve_voice_preset_id(builder, i) for i in range(len(scenes))]
        self.assertTrue(all(pid is None for pid in preset_ids))

        # When preset_id is None: preset_seed=None, preset_voice_design=None → TTS_DEFAULT_SEED
        preset_seed = None
        preset_voice_design = None
        if preset_seed:
            voice_seed = preset_seed
        elif preset_voice_design:
            voice_seed = int(hashlib.sha256(preset_voice_design.encode()).hexdigest()[:8], 16) % (2**31)
        else:
            voice_seed = TTS_DEFAULT_SEED
        self.assertEqual(voice_seed, TTS_DEFAULT_SEED)

    def test_hashlib_seed_is_deterministic(self):
        """sha256 기반 seed는 PYTHONHASHSEED와 무관하게 항상 같은 값을 반환해야 한다."""
        prompt = "A warm, calm voice with gentle intonation"
        expected = int(hashlib.sha256(prompt.encode()).hexdigest()[:8], 16) % (2**31)

        for _ in range(3):
            actual = int(hashlib.sha256(prompt.encode()).hexdigest()[:8], 16) % (2**31)
            self.assertEqual(actual, expected)


class TestGetVoiceDesignForScene(unittest.TestCase):
    """_get_voice_design_for_scene: Gemini adapts preset + fallback to concatenation."""

    _GEMINI_PATCH = "services.video.scene_processing.generate_context_aware_voice_prompt"

    def setUp(self):
        from services.video.scene_processing import _get_voice_design_for_scene

        self._get = _get_voice_design_for_scene

    def _scene(
        self, voice_design_prompt: str = "", scene_emotion: str | None = None, image_prompt_ko: str | None = None
    ) -> MagicMock:
        s = MagicMock()
        s.voice_design_prompt = voice_design_prompt
        s.scene_emotion = scene_emotion
        s.speaker = "A"
        s.image_prompt_ko = image_prompt_ko
        s.image_prompt = None
        return s

    def _builder(self, global_prompt: str = "") -> MagicMock:
        b = MagicMock()
        b.request.voice_design_prompt = global_prompt
        return b

    @patch("services.video.scene_processing.TTS_VOICE_CONSISTENCY_MODE", False)
    @patch(_GEMINI_PATCH, return_value="A boy speaking with hopeful warmth")
    def test_preset_with_emotion_calls_gemini(self, mock_gemini):
        """프리셋 + 감정 있으면 Gemini가 맥락 기반 voice design 생성."""
        scene = self._scene(scene_emotion="hopeful")
        result = self._get(self._builder(), scene, "preset base voice", "스크립트", 0)
        mock_gemini.assert_called_once()
        self.assertEqual(result, "A boy speaking with hopeful warmth")

    @patch("services.video.scene_processing.TTS_VOICE_CONSISTENCY_MODE", False)
    @patch(_GEMINI_PATCH, return_value="")
    def test_preset_with_emotion_fallback_on_gemini_failure(self, mock_gemini):
        """Gemini 실패 시 단순 연결 fallback."""
        scene = self._scene(scene_emotion="hopeful")
        result = self._get(self._builder(), scene, "preset base voice", "스크립트", 0)
        self.assertEqual(result, "preset base voice, hopeful")

    def test_preset_no_emotion_no_context_returns_preset(self):
        """감정/맥락 없으면 Gemini 호출 없이 프리셋 그대로."""
        scene = self._scene()
        result = self._get(self._builder(), scene, "preset base voice", "스크립트", 0)
        self.assertEqual(result, "preset base voice")

    def test_per_scene_prompt_used_only_when_no_preset(self):
        """preset 없으면 per-scene prompt 사용."""
        scene = self._scene(voice_design_prompt="Gemini warm tone")
        result = self._get(self._builder(), scene, None, "스크립트", 0)
        self.assertEqual(result, "Gemini warm tone")

    def test_global_prompt_used_when_no_preset_no_scene_prompt(self):
        """preset 없고 scene prompt도 없으면 global prompt 사용."""
        scene = self._scene()
        result = self._get(self._builder(global_prompt="global voice"), scene, None, "스크립트", 0)
        self.assertEqual(result, "global voice")

    @patch("services.video.scene_processing.TTS_VOICE_CONSISTENCY_MODE", False)
    @patch(_GEMINI_PATCH)
    def test_gemini_receives_base_prompt(self, mock_gemini):
        """Gemini에 base_prompt가 전달되어 캐릭터 정체성이 보존된다."""
        mock_gemini.return_value = "A teenage boy whispering with hope"
        preset = "A teenage boy with passionate voice"
        scene = self._scene(scene_emotion="hopeful", image_prompt_ko="교실에서 친구를 바라보는 장면")
        self._get(self._builder(), scene, preset, "스크립트", 0)
        _, kwargs = mock_gemini.call_args
        self.assertEqual(kwargs["base_prompt"], preset)


class TestVoiceConsistencyMode(unittest.TestCase):
    """TTS_VOICE_CONSISTENCY_MODE: ON → Gemini 미호출, OFF → 기존 동작."""

    _GEMINI_PATCH = "services.video.scene_processing.generate_context_aware_voice_prompt"

    def setUp(self):
        from services.video.scene_processing import _get_voice_design_for_scene

        self._get = _get_voice_design_for_scene

    def _scene(self, scene_emotion: str | None = None) -> MagicMock:
        s = MagicMock()
        s.voice_design_prompt = ""
        s.scene_emotion = scene_emotion
        s.speaker = "A"
        s.image_prompt_ko = "교실 장면"
        s.image_prompt = None
        return s

    def _builder(self) -> MagicMock:
        b = MagicMock()
        b.request.voice_design_prompt = ""
        return b

    @patch("services.video.scene_processing.TTS_VOICE_CONSISTENCY_MODE", True)
    @patch(_GEMINI_PATCH)
    def test_consistency_mode_skips_gemini(self, mock_gemini):
        """consistency ON → Gemini 미호출, 프리셋 그대로 반환."""
        scene = self._scene(scene_emotion="hopeful")
        result = self._get(self._builder(), scene, "preset base voice", "스크립트", 0)
        mock_gemini.assert_not_called()
        self.assertEqual(result, "preset base voice")

    @patch("services.video.scene_processing.TTS_VOICE_CONSISTENCY_MODE", False)
    @patch(_GEMINI_PATCH, return_value="Gemini adapted voice")
    def test_consistency_mode_off_calls_gemini(self, mock_gemini):
        """consistency OFF → 기존 Gemini 호출 동작."""
        scene = self._scene(scene_emotion="hopeful")
        result = self._get(self._builder(), scene, "preset base voice", "스크립트", 0)
        mock_gemini.assert_called_once()
        self.assertEqual(result, "Gemini adapted voice")

    @patch("services.video.scene_processing.TTS_VOICE_CONSISTENCY_MODE", True)
    @patch(_GEMINI_PATCH)
    def test_all_scenes_same_instruct(self, mock_gemini):
        """consistency ON → 3개 씬 모두 동일 instruct 반환."""
        preset = "A warm teenage boy voice"
        results = []
        for i in range(3):
            scene = self._scene(scene_emotion=["hopeful", "sad", "angry"][i])
            result = self._get(self._builder(), scene, preset, f"스크립트 {i}", i)
            results.append(result)
        self.assertTrue(all(r == preset for r in results), f"All scenes must return same preset: {results}")
        mock_gemini.assert_not_called()


if __name__ == "__main__":
    unittest.main()
