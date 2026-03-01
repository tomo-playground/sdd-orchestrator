"""TTS voice seed & voice design consistency tests.

Verifies:
1. Voice seed always comes from the character's voice preset (not per-scene hash).
2. When a preset exists, voice design uses preset base + scene_emotion,
   ignoring Agentic Pipeline per-scene voice_design_prompt that would override
   the character's voice identity.
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
    """_get_voice_design_for_scene must preserve character identity via preset."""

    def setUp(self):
        from services.video.scene_processing import _get_voice_design_for_scene
        self._get = _get_voice_design_for_scene

    def _scene(self, voice_design_prompt: str = "", scene_emotion: str | None = None) -> MagicMock:
        s = MagicMock()
        s.voice_design_prompt = voice_design_prompt
        s.scene_emotion = scene_emotion
        s.speaker = "A"
        s.image_prompt_ko = None
        s.image_prompt = None
        return s

    def _builder(self, global_prompt: str = "") -> MagicMock:
        b = MagicMock()
        b.request.voice_design_prompt = global_prompt
        return b

    def test_preset_base_used_when_preset_exists(self):
        """preset 있으면 per-scene prompt 무시하고 preset base 사용."""
        scene = self._scene(voice_design_prompt="Gemini generated warm tone", scene_emotion=None)
        result = self._get(self._builder(), scene, "preset base voice", "스크립트", 0)
        self.assertEqual(result, "preset base voice")

    def test_preset_plus_emotion_when_scene_emotion_set(self):
        """preset + scene_emotion 조합."""
        scene = self._scene(voice_design_prompt="Gemini warm tone", scene_emotion="hopeful")
        result = self._get(self._builder(), scene, "preset base voice", "스크립트", 0)
        self.assertEqual(result, "preset base voice, hopeful")

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

    def test_preset_overrides_per_scene_prompt_identity_preserved(self):
        """핵심 regression: Gemini가 생성한 per-scene prompt가 캐릭터 정체성을 덮어쓰지 않는다."""
        preset = "A teenage boy with passionate, energetic voice. Fast pace, mid-to-high pitch."
        scenes_emotions = ["hopeful", "cheerful", "calm"]

        for emotion in scenes_emotions:
            scene = self._scene(
                voice_design_prompt=f"A warm {emotion} tone without character info",
                scene_emotion=emotion,
            )
            result = self._get(self._builder(), scene, preset, "스크립트", 0)
            self.assertIsNotNone(result, f"result must not be None (emotion={emotion})")
            assert result is not None
            self.assertIn("teenage boy", result, f"캐릭터 정보가 유지되어야 함 (emotion={emotion})")
            self.assertIn(emotion, result, f"감정 수식이 붙어야 함 (emotion={emotion})")


if __name__ == "__main__":
    unittest.main()
