"""Tests for extracted video modules: encoding, upload, tts_helpers."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Shared decorator stack for encoding config constants
_ENC_CFG = [
    patch("services.video.encoding.VIDEO_FPS", 30),
    patch("services.video.encoding.VIDEO_CODEC", "libx264"),
    patch("services.video.encoding.VIDEO_PIX_FMT", "yuv420p"),
    patch("services.video.encoding.VIDEO_PRESET", "medium"),
    patch("services.video.encoding.VIDEO_CRF", 20),
    patch("services.video.encoding.AUDIO_CODEC", "aac"),
    patch("services.video.encoding.AUDIO_BITRATE", "192k"),
]


def _enc_cfg(fn):
    """Apply all encoding config patches to a test function."""
    for p in reversed(_ENC_CFG):
        fn = p(fn)
    return fn


def _make_builder(**overrides) -> MagicMock:
    b = MagicMock()
    b.filters = ["[0:v]scale=1080:1920[v0]", "[v0][1:a]concat=n=1[outv][outa]"]
    b.input_args = ["-i", "scene0.mp4"]
    b._map_v, b._map_a = "[outv]", "[outa]"
    b.out_w, b.out_h = 1080, 1920
    b.video_path = Path("/tmp/test_video.mp4")
    b.request = MagicMock()
    b.request.include_scene_text = True
    b.request.storyboard_id = 1
    b.project_id_int, b.group_id_int = 10, 20
    b.video_filename = "test_video.mp4"
    b._total_dur, b._progress = 10.0, None
    for k, v in overrides.items():
        setattr(b, k, v)
    return b


class TestBuildFfmpegCmd:
    @_enc_cfg
    def test_produces_correct_command_list(self):
        from services.video.encoding import build_ffmpeg_cmd
        cmd = build_ffmpeg_cmd(_make_builder())
        assert cmd[0] == "ffmpeg" and "-y" in cmd
        fc_idx = cmd.index("-filter_complex")
        assert ";" in cmd[fc_idx + 1]
        for flag, val in [
            ("-s", "1080x1920"), ("-r", "30"), ("-c:v", "libx264"),
            ("-pix_fmt", "yuv420p"), ("-preset", "medium"), ("-crf", "20"),
            ("-movflags", "+faststart"), ("-c:a", "aac"), ("-b:a", "192k"),
        ]:
            idx = cmd.index(flag)
            assert cmd[idx + 1] == val
        assert cmd[-1] == "/tmp/test_video.mp4"

    @_enc_cfg
    def test_input_args_forwarded(self):
        from services.video.encoding import build_ffmpeg_cmd
        cmd = build_ffmpeg_cmd(_make_builder(input_args=["-i", "a.mp4", "-i", "b.mp4"]))
        between = cmd[cmd.index("-y") + 1 : cmd.index("-filter_complex")]
        assert between == ["-i", "a.mp4", "-i", "b.mp4"]


class TestUploadResult:
    @patch("services.video.upload.VIDEO_DIR", Path("/output/videos"))
    @patch("services.video.upload.SessionLocal")
    @patch("services.video.upload.AssetService")
    def test_fallback_uses_video_dir(self, _ac, _sc):
        from services.video.upload import upload_result
        result = upload_result(_make_builder(project_id_int=None, group_id_int=None))
        assert result["video_url"] == "/output/videos/test_video.mp4"

    @patch("services.video.upload.VIDEO_DIR", Path("/output/videos"))
    @patch("services.video.upload.SessionLocal")
    @patch("services.video.upload.AssetService")
    def test_asset_upload_path(self, mock_asset_cls, mock_session_cls):
        from services.video.upload import upload_result
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_svc = MagicMock()
        mock_asset_cls.return_value = mock_svc
        mock_asset = MagicMock(id=42, storage_key="videos/test.mp4")
        mock_svc.save_rendered_video.return_value = mock_asset
        mock_svc.get_asset_url.return_value = "https://cdn.example.com/test.mp4"
        result = upload_result(_make_builder())
        mock_svc.save_rendered_video.assert_called_once_with(
            video_path=Path("/tmp/test_video.mp4"),
            project_id=10, group_id=20, storyboard_id=1, file_name="test_video.mp4",
        )
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()
        assert result == {"video_url": "https://cdn.example.com/test.mp4", "media_asset_id": 42}


@pytest.fixture(autouse=True)
def _mock_tts_deps():
    """Mock torch and qwen_tts at import level."""
    import sys
    mt = MagicMock()
    mt.backends.mps.is_available.return_value = False
    sys.modules.setdefault("torch", mt)
    sys.modules.setdefault("qwen_tts", MagicMock())
    yield


class TestTtsCacheKey:
    def test_deterministic(self):
        from services.video.tts_helpers import tts_cache_key
        k1 = tts_cache_key("hello", 1, "female", "ko")
        assert k1 == tts_cache_key("hello", 1, "female", "ko")
        assert len(k1) == 16

    def test_different_text_different_key(self):
        from services.video.tts_helpers import tts_cache_key
        assert tts_cache_key("hello", 1, "f", "ko") != tts_cache_key("world", 1, "f", "ko")

    def test_none_prompt_handled(self):
        from services.video.tts_helpers import tts_cache_key
        k = tts_cache_key("text", None, None, "en")
        assert isinstance(k, str) and len(k) == 16


class TestTranslateVoicePrompt:
    @patch("services.video.tts_helpers.gemini_client", None)
    def test_no_gemini_returns_original(self):
        from services.video.tts_helpers import translate_voice_prompt
        assert translate_voice_prompt("english text") == "english text"

    @patch("services.video.tts_helpers.gemini_client")
    def test_korean_text_calls_gemini(self, mock_client):
        from services.video.tts_helpers import _VOICE_PROMPT_CACHE, translate_voice_prompt
        korean = "\ubd80\ub4dc\ub7ec\uc6b4 \uc5ec\uc131"
        _VOICE_PROMPT_CACHE.pop(korean, None)
        mock_res = MagicMock()
        mock_res.text = " Soft female voice "
        mock_client.models.generate_content.return_value = mock_res
        assert translate_voice_prompt(korean) == "Soft female voice"
        mock_client.models.generate_content.assert_called_once()
        _VOICE_PROMPT_CACHE.pop(korean, None)

    def test_empty_returns_empty(self):
        from services.video.tts_helpers import translate_voice_prompt
        assert translate_voice_prompt("") == ""


class TestResolveNarratorPreset:
    def test_returns_preset_id_from_effective(self):
        from services.video.tts_helpers import _resolve_narrator_preset
        assert _resolve_narrator_preset({"values": {"narrator_voice_preset_id": 7}}) == 7

    def test_returns_none_when_missing(self):
        from services.video.tts_helpers import _resolve_narrator_preset
        assert _resolve_narrator_preset({"values": {}}) is None


class TestGetSpeakerVoicePreset:
    @patch("database.get_db")
    def test_no_storyboard_id_returns_none(self, _mock_db):
        from services.video.tts_helpers import get_speaker_voice_preset
        assert get_speaker_voice_preset(None, "Narrator") is None
        _mock_db.assert_not_called()

    @patch("services.config_resolver.resolve_effective_config")
    @patch("database.get_db")
    def test_narrator_branch(self, mock_get_db, mock_resolve):
        from services.video.tts_helpers import get_speaker_voice_preset
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_db.get.side_effect = lambda cls, id_: {
            1: MagicMock(group_id=5), 5: MagicMock(),
        }.get(id_)
        mock_resolve.return_value = {"values": {"narrator_voice_preset_id": 99}}
        assert get_speaker_voice_preset(1, "Narrator") == 99

    @patch("services.speaker_resolver.resolve_speaker_to_character")
    @patch("services.config_resolver.resolve_effective_config")
    @patch("database.get_db")
    def test_character_branch(self, mock_get_db, mock_resolve, mock_spkr):
        from services.video.tts_helpers import get_speaker_voice_preset
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_char = MagicMock(name="Alice", voice_preset_id=55)

        def _db_get(cls, id_):
            from models.character import Character
            from models.group import Group
            from models.storyboard import Storyboard
            mapping = {Storyboard: MagicMock(group_id=5), Group: MagicMock(), Character: mock_char}
            return mapping.get(cls)

        mock_db.get.side_effect = _db_get
        mock_resolve.return_value = {"values": {}}
        mock_spkr.return_value = 100
        assert get_speaker_voice_preset(1, "Alice") == 55
