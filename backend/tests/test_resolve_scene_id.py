"""Tests for resolve_scene_id_by_client_id helper."""

from models.scene import Scene
from models.storyboard import Storyboard
from services.storyboard.helpers import resolve_scene_id_by_client_id


class TestResolveSceneIdByClientId:
    """resolve_scene_id_by_client_id: scene_id 유효 → 그대로, stale → client_id 폴백."""

    def test_valid_scene_id_returns_as_is(self, db_session):
        sb = Storyboard(title="test", group_id=1)
        db_session.add(sb)
        db_session.flush()
        scene = Scene(storyboard_id=sb.id, order=0, client_id="uuid-aaa")
        db_session.add(scene)
        db_session.commit()

        result = resolve_scene_id_by_client_id(db_session, scene.id, "uuid-aaa", sb.id)
        assert result == scene.id

    def test_stale_scene_id_falls_back_to_client_id(self, db_session):
        sb = Storyboard(title="test", group_id=1)
        db_session.add(sb)
        db_session.flush()
        scene = Scene(storyboard_id=sb.id, order=0, client_id="uuid-bbb")
        db_session.add(scene)
        db_session.commit()

        stale_id = scene.id + 9999
        result = resolve_scene_id_by_client_id(db_session, stale_id, "uuid-bbb", sb.id)
        assert result == scene.id

    def test_both_miss_returns_none(self, db_session):
        result = resolve_scene_id_by_client_id(db_session, 99999, "no-such-uuid", 1)
        assert result is None

    def test_no_client_id_returns_none(self, db_session):
        result = resolve_scene_id_by_client_id(db_session, 99999, None, 1)
        assert result is None

    def test_soft_deleted_scene_not_resolved(self, db_session):
        """soft-deleted scene은 조회되지 않는다."""
        from datetime import UTC, datetime

        sb = Storyboard(title="test", group_id=1)
        db_session.add(sb)
        db_session.flush()
        scene = Scene(
            storyboard_id=sb.id,
            order=0,
            client_id="uuid-del",
            deleted_at=datetime.now(UTC),
        )
        db_session.add(scene)
        db_session.commit()

        result = resolve_scene_id_by_client_id(db_session, scene.id, "uuid-del", sb.id)
        assert result is None
