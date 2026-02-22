"""Tests for scene per-scene generation flag storage (ControlNet, IP-Adapter, MultiGen)."""

from models.group import Group
from models.project import Project
from models.scene import Scene
from models.storyboard import Storyboard


def _create_storyboard(db_session) -> Storyboard:
    """Create a valid storyboard with Project → Group chain."""
    project = Project(name="test_project")
    db_session.add(project)
    db_session.flush()
    group = Group(project_id=project.id, name="test_group")
    db_session.add(group)
    db_session.flush()
    sb = Storyboard(title="test", group_id=group.id)
    db_session.add(sb)
    db_session.flush()
    return sb


class TestSceneFlagStorage:
    """Scene flags (use_controlnet, use_ip_adapter, etc.) DB save/load."""

    def _create_scene(self, db_session, **overrides) -> Scene:
        sb = _create_storyboard(db_session)
        scene_data = {
            "storyboard_id": sb.id,
            "order": 0,
            "script": "test scene",
        }
        scene_data.update(overrides)
        scene = Scene(**scene_data)
        db_session.add(scene)
        db_session.flush()
        return scene

    def test_controlnet_flags_save_and_load(self, db_session):
        scene = self._create_scene(
            db_session,
            use_controlnet=True,
            controlnet_weight=0.8,
        )
        db_session.commit()

        loaded = db_session.query(Scene).filter(Scene.id == scene.id).one()
        assert loaded.use_controlnet is True
        assert loaded.controlnet_weight == 0.8

    def test_ip_adapter_flags_save_and_load(self, db_session):
        scene = self._create_scene(
            db_session,
            use_ip_adapter=True,
            ip_adapter_weight=0.6,
            ip_adapter_reference="char_key",
        )
        db_session.commit()

        loaded = db_session.query(Scene).filter(Scene.id == scene.id).one()
        assert loaded.use_ip_adapter is True
        assert loaded.ip_adapter_weight == 0.6
        assert loaded.ip_adapter_reference == "char_key"

    def test_multi_gen_flag_save_and_load(self, db_session):
        scene = self._create_scene(
            db_session,
            multi_gen_enabled=True,
        )
        db_session.commit()

        loaded = db_session.query(Scene).filter(Scene.id == scene.id).one()
        assert loaded.multi_gen_enabled is True

    def test_null_flags_default(self, db_session):
        """Flags default to NULL (inherit global settings)."""
        scene = self._create_scene(db_session)
        db_session.commit()

        loaded = db_session.query(Scene).filter(Scene.id == scene.id).one()
        assert loaded.use_controlnet is None
        assert loaded.controlnet_weight is None
        assert loaded.use_ip_adapter is None
        assert loaded.ip_adapter_weight is None
        assert loaded.ip_adapter_reference is None
        assert loaded.multi_gen_enabled is None

    def test_update_flags(self, db_session):
        """Flags can be updated after creation."""
        scene = self._create_scene(db_session)
        db_session.commit()

        scene.use_controlnet = True
        scene.controlnet_weight = 0.9
        db_session.commit()

        loaded = db_session.query(Scene).filter(Scene.id == scene.id).one()
        assert loaded.use_controlnet is True
        assert loaded.controlnet_weight == 0.9

    def test_false_flags_stored_correctly(self, db_session):
        """Explicit False is different from NULL."""
        scene = self._create_scene(
            db_session,
            use_controlnet=False,
            use_ip_adapter=False,
            multi_gen_enabled=False,
        )
        db_session.commit()

        loaded = db_session.query(Scene).filter(Scene.id == scene.id).one()
        assert loaded.use_controlnet is False
        assert loaded.use_ip_adapter is False
        assert loaded.multi_gen_enabled is False
