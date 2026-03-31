"""Unit tests for persist_pipeline_scenes() — SP-131.

파이프라인 finalize 결과를 DB에 직접 저장하는 로직 검증.
"""

from __future__ import annotations

from unittest.mock import patch

from models.scene import Scene
from models.storyboard import Storyboard


def _create_storyboard(
    db,
    group_id: int = 1,
    structure: str = "monologue",
    stage_status: str | None = None,
    **kwargs,
) -> Storyboard:
    """Create a test storyboard with defaults."""
    sb = Storyboard(
        title="Test",
        group_id=group_id,
        structure=structure,
        tone="calm",
        version=1,
        stage_status=stage_status,
        **kwargs,
    )
    db.add(sb)
    db.commit()
    db.refresh(sb)
    return sb


def _create_scene(db, storyboard_id: int, order: int = 0, **kwargs) -> Scene:
    """Create a test scene."""
    from uuid import uuid4

    scene = Scene(
        storyboard_id=storyboard_id,
        order=order,
        client_id=str(uuid4()),
        script="Old scene",
        speaker="speaker_1",
        **kwargs,
    )
    db.add(scene)
    db.commit()
    db.refresh(scene)
    return scene


def _make_pipeline_scenes(count: int = 3) -> list[dict]:
    """Create minimal pipeline scene dicts."""
    return [
        {
            "script": f"Scene {i} script",
            "speaker": "speaker_1",
            "duration": 3.0,
            "image_prompt": f"scene_{i}_prompt",
        }
        for i in range(count)
    ]


class TestPersistPipelineScenes:
    """Tests for persist_pipeline_scenes()."""

    @patch("services.storyboard.crud.create_scenes")
    @patch("services.characters.assign_speakers")
    def test_saves_scenes_and_increments_version(self, mock_assign, mock_create_scenes, db_session):
        from services.storyboard.crud import persist_pipeline_scenes

        sb = _create_storyboard(db_session)
        scenes = _make_pipeline_scenes(3)

        result = persist_pipeline_scenes(
            db_session,
            sb.id,
            scenes,
            structure="monologue",
        )

        assert result is True
        db_session.refresh(sb)
        assert sb.version == 2
        assert sb.stage_status is None
        mock_create_scenes.assert_called_once()

    @patch("services.storyboard.crud.create_scenes")
    @patch("services.characters.assign_speakers")
    def test_soft_deletes_existing_scenes(self, mock_assign, mock_create_scenes, db_session):
        from services.storyboard.crud import persist_pipeline_scenes

        sb = _create_storyboard(db_session)
        old_scene = _create_scene(db_session, sb.id, order=0)

        result = persist_pipeline_scenes(
            db_session,
            sb.id,
            _make_pipeline_scenes(2),
        )

        assert result is True
        db_session.refresh(old_scene)
        assert old_scene.deleted_at is not None

    @patch("services.storyboard.crud.create_scenes")
    @patch("services.characters.assign_speakers")
    def test_updates_structure(self, mock_assign, mock_create_scenes, db_session):
        from services.storyboard.crud import persist_pipeline_scenes

        sb = _create_storyboard(db_session, structure="monologue")

        persist_pipeline_scenes(
            db_session,
            sb.id,
            _make_pipeline_scenes(1),
            structure="dialogue",
        )

        db_session.refresh(sb)
        assert sb.structure == "dialogue"

    @patch("services.storyboard.crud.create_scenes")
    @patch("services.characters.assign_speakers")
    def test_resets_stage_status(self, mock_assign, mock_create_scenes, db_session):
        from services.storyboard.crud import persist_pipeline_scenes

        sb = _create_storyboard(db_session, stage_status="stage_done")

        persist_pipeline_scenes(db_session, sb.id, _make_pipeline_scenes(1))

        db_session.refresh(sb)
        assert sb.stage_status is None

    def test_returns_false_for_missing_storyboard(self, db_session):
        from services.storyboard.crud import persist_pipeline_scenes

        result = persist_pipeline_scenes(db_session, 99999, _make_pipeline_scenes(1))

        assert result is False

    def test_returns_false_for_soft_deleted_storyboard(self, db_session):
        from datetime import UTC, datetime

        from services.storyboard.crud import persist_pipeline_scenes

        sb = _create_storyboard(db_session)
        sb.deleted_at = datetime.now(UTC)
        db_session.commit()

        result = persist_pipeline_scenes(db_session, sb.id, _make_pipeline_scenes(1))

        assert result is False

    @patch("services.storyboard.crud.create_scenes")
    @patch("services.characters.assign_speakers")
    def test_syncs_speaker_mappings(self, mock_assign, mock_create_scenes, db_session):
        from services.storyboard.crud import persist_pipeline_scenes

        sb = _create_storyboard(db_session)

        persist_pipeline_scenes(
            db_session,
            sb.id,
            _make_pipeline_scenes(1),
            character_id=10,
            character_b_id=20,
            structure="dialogue",
        )

        mock_assign.assert_called_once()

    @patch("services.storyboard.crud.create_scenes")
    @patch("services.characters.assign_speakers")
    def test_returns_false_for_empty_scenes(self, mock_assign, mock_create_scenes, db_session):
        from services.storyboard.crud import persist_pipeline_scenes

        sb = _create_storyboard(db_session)
        result = persist_pipeline_scenes(db_session, sb.id, [])

        assert result is False
        mock_create_scenes.assert_not_called()

    @patch("services.storyboard.crud.create_scenes")
    @patch("services.characters.assign_speakers")
    def test_preserves_structure_when_none(self, mock_assign, mock_create_scenes, db_session):
        from services.storyboard.crud import persist_pipeline_scenes

        sb = _create_storyboard(db_session, structure="monologue")

        persist_pipeline_scenes(
            db_session,
            sb.id,
            _make_pipeline_scenes(1),
            structure=None,
        )

        db_session.refresh(sb)
        assert sb.structure == "monologue"
