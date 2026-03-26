"""Tests for services/tts_prebuild.py (Phase 32).

Covers:
- Scene with existing tts_asset_id → status="skipped"
- Scene without tts_asset_id → calls _generate_audio → status="prebuilt"
- Scene where generation fails → status="failed", error message set
- Mixed scenes: skip + prebuilt + failed combo
- Response counts (prebuilt/skipped/failed) are correct
"""

from __future__ import annotations

import io
import wave
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from schemas import TtsPrebuildRequest, TtsPrebuildSceneItem

# ── WAV helpers ───────────────────────────────────────────────────────────────


def _make_wav_bytes(duration_sec: float = 1.0, framerate: int = 22050) -> bytes:
    """Build minimal WAV bytes for a given duration."""
    buf = io.BytesIO()
    n_frames = int(framerate * duration_sec)
    with wave.open(buf, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        wf.writeframes(b"\x00\x00" * n_frames)
    return buf.getvalue()


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_db(asset_exists: bool = False) -> MagicMock:
    """Return a minimal mock DB session.

    asset_exists: db.get(MediaAsset, id) returns an asset (or None)
    """
    db = MagicMock()
    db.get.return_value = MagicMock() if asset_exists else None
    db.commit = MagicMock()
    return db


# ── Tests for 'skipped' status ────────────────────────────────────────────────


class TestPrebuildSkipped:
    """Scenes with a valid tts_asset_id are skipped."""

    @pytest.mark.asyncio
    async def test_scene_with_valid_asset_is_skipped(self):
        """Scene with tts_asset_id pointing to an existing live asset → skipped."""
        from services.tts_prebuild import prebuild_tts_for_scenes

        db = _make_db(asset_exists=True)
        request = TtsPrebuildRequest(
            storyboard_id=1,
            scenes=[
                TtsPrebuildSceneItem(
                    scene_db_id=10,
                    script="테스트 스크립트입니다.",
                    speaker="speaker_1",
                    tts_asset_id=99,
                )
            ],
        )

        response = await prebuild_tts_for_scenes(request, db)

        assert response.skipped == 1
        assert response.prebuilt == 0
        assert response.failed == 0
        assert len(response.results) == 1
        result = response.results[0]
        assert result.scene_db_id == 10
        assert result.status == "skipped"
        assert result.tts_asset_id == 99

    @pytest.mark.asyncio
    async def test_scene_without_asset_id_is_not_skipped(self):
        """Scene with tts_asset_id=None is never skipped."""
        from services.tts_prebuild import prebuild_tts_for_scenes

        db = _make_db(asset_exists=False)
        wav_bytes = _make_wav_bytes(2.0)

        request = TtsPrebuildRequest(
            storyboard_id=1,
            scenes=[
                TtsPrebuildSceneItem(
                    scene_db_id=12,
                    script="오디오 생성 씬입니다.",
                    speaker="speaker_2",
                    tts_asset_id=None,
                )
            ],
        )

        with (
            patch(
                "services.tts_prebuild._generate_audio",
                new_callable=AsyncMock,
                return_value=(wav_bytes, 2.0),
            ),
            patch("services.tts_prebuild._save_tts_asset", return_value=88),
            patch("services.tts_prebuild._update_scene_tts_asset"),
        ):
            response = await prebuild_tts_for_scenes(request, db)

        assert response.skipped == 0
        assert response.prebuilt == 1


# ── Tests for 'prebuilt' status ───────────────────────────────────────────────


class TestPrebuildPrebuilt:
    """Scenes that successfully generate audio get status='prebuilt'."""

    @pytest.mark.asyncio
    async def test_successful_generation_returns_prebuilt(self):
        """Happy-path: _generate_audio succeeds → status='prebuilt', asset_id set."""
        from services.tts_prebuild import prebuild_tts_for_scenes

        db = _make_db(asset_exists=False)
        wav_bytes = _make_wav_bytes(3.0)

        request = TtsPrebuildRequest(
            storyboard_id=5,
            scenes=[
                TtsPrebuildSceneItem(
                    scene_db_id=20,
                    script="성공 케이스 스크립트입니다.",
                    speaker="narrator",
                    voice_design_prompt="warm and calm",
                    tts_asset_id=None,
                )
            ],
        )

        mock_save = MagicMock(return_value=111)
        mock_update = MagicMock()

        with (
            patch(
                "services.tts_prebuild._generate_audio",
                new_callable=AsyncMock,
                return_value=(wav_bytes, 3.0),
            ),
            patch("services.tts_prebuild._save_tts_asset", mock_save),
            patch("services.tts_prebuild._update_scene_tts_asset", mock_update),
        ):
            response = await prebuild_tts_for_scenes(request, db)

        assert response.prebuilt == 1
        assert response.skipped == 0
        assert response.failed == 0

        result = response.results[0]
        assert result.status == "prebuilt"
        assert result.scene_db_id == 20
        assert result.tts_asset_id == 111
        assert result.duration == 3.0
        assert result.error is None

    @pytest.mark.asyncio
    async def test_generate_audio_called_with_correct_args(self):
        """_generate_audio is called with storyboard_id, script, speaker, voice_design."""
        from services.tts_prebuild import prebuild_tts_for_scenes

        db = _make_db(asset_exists=False)
        wav_bytes = _make_wav_bytes(1.0)

        request = TtsPrebuildRequest(
            storyboard_id=7,
            scenes=[
                TtsPrebuildSceneItem(
                    scene_db_id=30,
                    script="특정 인자 확인 스크립트",
                    speaker="SpeakerX",
                    voice_design_prompt="deep and authoritative",
                    tts_asset_id=None,
                )
            ],
        )

        mock_generate = AsyncMock(return_value=(wav_bytes, 1.0))

        with (
            patch("services.tts_prebuild._generate_audio", mock_generate),
            patch("services.tts_prebuild._save_tts_asset", return_value=200),
            patch("services.tts_prebuild._update_scene_tts_asset"),
        ):
            await prebuild_tts_for_scenes(request, db)

        mock_generate.assert_called_once_with(
            "특정 인자 확인 스크립트",
            "SpeakerX",
            "deep and authoritative",
            7,  # storyboard_id
            scene_emotion=None,
            image_prompt_ko=None,
            scene_db_id=30,
            language=None,
        )

    @pytest.mark.asyncio
    async def test_update_scene_tts_asset_called_on_success(self):
        """After successful generation, _update_scene_tts_asset is called."""
        from services.tts_prebuild import prebuild_tts_for_scenes

        db = _make_db(asset_exists=False)
        wav_bytes = _make_wav_bytes(1.0)

        request = TtsPrebuildRequest(
            storyboard_id=1,
            scenes=[
                TtsPrebuildSceneItem(scene_db_id=40, script="업데이트 테스트", speaker="speaker_1", tts_asset_id=None)
            ],
        )

        mock_update = MagicMock()

        with (
            patch(
                "services.tts_prebuild._generate_audio",
                new_callable=AsyncMock,
                return_value=(wav_bytes, 1.0),
            ),
            patch("services.tts_prebuild._save_tts_asset", return_value=300),
            patch("services.tts_prebuild._update_scene_tts_asset", mock_update),
        ):
            await prebuild_tts_for_scenes(request, db)

        mock_update.assert_called_once_with(db, 40, 300)


# ── Tests for 'failed' status ─────────────────────────────────────────────────


class TestPrebuildFailed:
    """Generation failures are captured without propagating the exception."""

    @pytest.mark.asyncio
    async def test_generate_audio_exception_returns_failed(self):
        """When _generate_audio raises, status='failed' with error message."""
        from services.tts_prebuild import prebuild_tts_for_scenes

        db = _make_db(asset_exists=False)

        request = TtsPrebuildRequest(
            storyboard_id=1,
            scenes=[
                TtsPrebuildSceneItem(
                    scene_db_id=50,
                    script="실패 케이스 스크립트입니다.",
                    speaker="speaker_1",
                    tts_asset_id=None,
                )
            ],
        )

        with patch(
            "services.tts_prebuild._generate_audio",
            new_callable=AsyncMock,
            side_effect=RuntimeError("TTS server unavailable"),
        ):
            response = await prebuild_tts_for_scenes(request, db)

        assert response.failed == 1
        assert response.prebuilt == 0
        assert response.skipped == 0

        result = response.results[0]
        assert result.status == "failed"
        assert result.scene_db_id == 50
        assert result.tts_asset_id is None
        assert "TTS server unavailable" in result.error

    @pytest.mark.asyncio
    async def test_db_write_failure_returns_failed(self):
        """When _save_tts_asset raises, status='failed' (DB write failure)."""
        from services.tts_prebuild import prebuild_tts_for_scenes

        db = _make_db(asset_exists=False)
        wav_bytes = _make_wav_bytes(1.0)

        request = TtsPrebuildRequest(
            storyboard_id=1,
            scenes=[
                TtsPrebuildSceneItem(
                    scene_db_id=60,
                    script="DB 쓰기 실패 시나리오입니다.",
                    speaker="speaker_1",
                    tts_asset_id=None,
                )
            ],
        )

        with (
            patch(
                "services.tts_prebuild._generate_audio",
                new_callable=AsyncMock,
                return_value=(wav_bytes, 1.0),
            ),
            patch(
                "services.tts_prebuild._save_tts_asset",
                side_effect=Exception("DB connection lost"),
            ),
        ):
            response = await prebuild_tts_for_scenes(request, db)

        assert response.failed == 1
        result = response.results[0]
        assert result.status == "failed"
        assert "DB connection lost" in result.error

    @pytest.mark.asyncio
    async def test_failed_result_has_no_asset_id(self):
        """Failed result always has tts_asset_id=None."""
        from services.tts_prebuild import prebuild_tts_for_scenes

        db = _make_db(asset_exists=False)

        request = TtsPrebuildRequest(
            storyboard_id=1,
            scenes=[
                TtsPrebuildSceneItem(scene_db_id=70, script="실패 결과 확인", speaker="speaker_1", tts_asset_id=None)
            ],
        )

        with patch(
            "services.tts_prebuild._generate_audio",
            new_callable=AsyncMock,
            side_effect=ValueError("스크립트에 TTS로 변환할 내용이 없습니다."),
        ):
            response = await prebuild_tts_for_scenes(request, db)

        assert response.results[0].tts_asset_id is None


# ── Tests for mixed scenarios ─────────────────────────────────────────────────


class TestPrebuildMixed:
    """Mixed scenes: combination of skipped, prebuilt, failed."""

    @pytest.mark.asyncio
    async def test_mixed_skip_prebuilt_failed(self):
        """Three scenes: one skipped, one prebuilt, one failed — counts are accurate."""
        from services.tts_prebuild import prebuild_tts_for_scenes

        wav_bytes = _make_wav_bytes(2.5)

        # Scene 1 (scene_db_id=1): has a valid tts_asset_id → skipped
        # Scene 2 (scene_db_id=2): no asset → prebuilt
        # Scene 3 (scene_db_id=3): no asset → generation fails
        def _db_get_side_effect(model_class, asset_id):
            if asset_id == 10:
                return MagicMock()
            return None

        db = MagicMock()
        db.get.side_effect = _db_get_side_effect
        db.commit = MagicMock()

        request = TtsPrebuildRequest(
            storyboard_id=42,
            scenes=[
                TtsPrebuildSceneItem(scene_db_id=1, script="씬 1 스크립트", speaker="speaker_1", tts_asset_id=10),
                TtsPrebuildSceneItem(scene_db_id=2, script="씬 2 스크립트", speaker="speaker_2", tts_asset_id=None),
                TtsPrebuildSceneItem(scene_db_id=3, script="씬 3 스크립트", speaker="C", tts_asset_id=None),
            ],
        )

        call_count = 0

        async def _generate_side_effect(
            script,
            speaker,
            voice_design,
            storyboard_id,
            scene_emotion=None,
            image_prompt_ko=None,
            scene_db_id=None,
            language=None,
        ):
            nonlocal call_count
            call_count += 1
            if speaker == "C":
                raise RuntimeError("TTS failed for scene 3")
            return wav_bytes, 2.5

        with (
            patch("services.tts_prebuild._generate_audio", side_effect=_generate_side_effect),
            patch("services.tts_prebuild._save_tts_asset", return_value=999),
            patch("services.tts_prebuild._update_scene_tts_asset"),
        ):
            response = await prebuild_tts_for_scenes(request, db)

        assert response.skipped == 1
        assert response.prebuilt == 1
        assert response.failed == 1
        assert len(response.results) == 3

        statuses = {r.scene_db_id: r.status for r in response.results}
        assert statuses[1] == "skipped"
        assert statuses[2] == "prebuilt"
        assert statuses[3] == "failed"

    @pytest.mark.asyncio
    async def test_all_skipped_zero_generation_calls(self):
        """All scenes with valid assets → _generate_audio never called."""
        from services.tts_prebuild import prebuild_tts_for_scenes

        def _always_valid(model_class, asset_id):
            return MagicMock()

        db = MagicMock()
        db.get.side_effect = _always_valid
        db.commit = MagicMock()

        request = TtsPrebuildRequest(
            storyboard_id=1,
            scenes=[
                TtsPrebuildSceneItem(scene_db_id=i, script="씬", speaker="speaker_1", tts_asset_id=100 + i)
                for i in range(3)
            ],
        )

        mock_generate = AsyncMock()

        with patch("services.tts_prebuild._generate_audio", mock_generate):
            response = await prebuild_tts_for_scenes(request, db)

        mock_generate.assert_not_called()
        assert response.skipped == 3
        assert response.prebuilt == 0
        assert response.failed == 0

    @pytest.mark.asyncio
    async def test_counts_match_results_list(self):
        """prebuilt/skipped/failed counters equal the number of results with each status."""
        from services.tts_prebuild import prebuild_tts_for_scenes

        wav_bytes = _make_wav_bytes(1.0)

        db = MagicMock()
        db.get.return_value = None
        db.commit = MagicMock()

        request = TtsPrebuildRequest(
            storyboard_id=1,
            scenes=[
                TtsPrebuildSceneItem(scene_db_id=i, script="씬 스크립트입니다.", speaker="speaker_1", tts_asset_id=None)
                for i in range(4)
            ],
        )

        call_count = 0

        async def _alternating(script, speaker, voice_design, storyboard_id):
            nonlocal call_count
            call_count += 1
            # Fail even-indexed calls (0, 2), succeed odd-indexed calls (1, 3)
            if call_count % 2 == 1:
                raise RuntimeError("simulated failure")
            return wav_bytes, 1.0

        with (
            patch("services.tts_prebuild._generate_audio", side_effect=_alternating),
            patch("services.tts_prebuild._save_tts_asset", return_value=42),
            patch("services.tts_prebuild._update_scene_tts_asset"),
        ):
            response = await prebuild_tts_for_scenes(request, db)

        # Verify counts match actual result statuses
        actual_prebuilt = sum(1 for r in response.results if r.status == "prebuilt")
        actual_skipped = sum(1 for r in response.results if r.status == "skipped")
        actual_failed = sum(1 for r in response.results if r.status == "failed")

        assert response.prebuilt == actual_prebuilt
        assert response.skipped == actual_skipped
        assert response.failed == actual_failed
        assert response.prebuilt + response.skipped + response.failed == len(response.results)

    @pytest.mark.asyncio
    async def test_empty_scenes_returns_zero_counts(self):
        """Empty scenes list → all counts are zero."""
        from services.tts_prebuild import prebuild_tts_for_scenes

        db = _make_db(asset_exists=False)
        request = TtsPrebuildRequest(storyboard_id=1, scenes=[])

        response = await prebuild_tts_for_scenes(request, db)

        assert response.prebuilt == 0
        assert response.skipped == 0
        assert response.failed == 0
        assert response.results == []
