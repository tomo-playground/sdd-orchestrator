"""Tests for cascading config resolver."""

from services.config_resolver import resolve_effective_config


# ---------------------------------------------------------------------------
# Helper: simple namespace to simulate ORM objects
# ---------------------------------------------------------------------------
class _Obj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# ===========================================================================
# Unit tests — resolve_effective_config pure function
# ===========================================================================


class TestResolveEffectiveConfig:
    def test_project_only(self):
        """Project layer can provide values (generic resolver test)."""
        project = _Obj(render_preset_id=10, character_id=1, style_profile_id=2)
        result = resolve_effective_config(project)
        assert result["values"] == {
            "render_preset_id": 10,
            "character_id": 1,
            "style_profile_id": 2,
        }
        assert all(v == "project" for v in result["sources"].values())

    def test_group_config_overrides_project(self):
        project = _Obj(render_preset_id=10, character_id=1, style_profile_id=2)
        group_config = _Obj(render_preset_id=20, character_id=None, style_profile_id=3)
        group = _Obj(config=group_config)
        result = resolve_effective_config(project, group)
        assert result["values"]["render_preset_id"] == 20
        assert result["sources"]["render_preset_id"] == "group"
        assert result["values"]["character_id"] == 1
        assert result["sources"]["character_id"] == "project"
        assert result["values"]["style_profile_id"] == 3
        assert result["sources"]["style_profile_id"] == "group"

    def test_group_config_with_character(self):
        project = _Obj(render_preset_id=10, character_id=1, style_profile_id=2)
        group_config = _Obj(character_id=99, render_preset_id=None, style_profile_id=None)
        group = _Obj(config=group_config)
        result = resolve_effective_config(project, group)
        assert result["values"]["character_id"] == 99
        assert result["sources"]["character_id"] == "group"
        assert result["values"]["render_preset_id"] == 10

    def test_all_none_returns_empty(self):
        project = _Obj(render_preset_id=None, character_id=None, style_profile_id=None)
        result = resolve_effective_config(project)
        assert result["values"] == {}
        assert result["sources"] == {}

    def test_no_group(self):
        project = _Obj(render_preset_id=5, character_id=None, style_profile_id=None)
        result = resolve_effective_config(project, None)
        assert result["values"] == {"render_preset_id": 5}
        assert result["sources"] == {"render_preset_id": "project"}

    def test_group_without_config(self):
        project = _Obj(render_preset_id=5, character_id=None, style_profile_id=None)
        group = _Obj(config=None)
        result = resolve_effective_config(project, group)
        assert result["values"] == {"render_preset_id": 5}
        assert result["sources"] == {"render_preset_id": "project"}


# ===========================================================================
# API integration tests
# ===========================================================================


class TestEffectiveConfigAPI:
    def test_project_effective_config(self, client, db_session):
        from models.project import Project

        project = db_session.query(Project).first()
        resp = client.get(f"/projects/{project.id}/effective-config")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data

    def test_group_effective_config(self, client, db_session):
        from models.group import Group

        group = db_session.query(Group).first()
        resp = client.get(f"/groups/{group.id}/effective-config")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data

    def test_group_config_sets_preset(self, client, db_session):
        """GroupConfig is the SSOT for cascading config."""
        from models.group import Group
        from models.group_config import GroupConfig
        from models.render_preset import RenderPreset

        preset = RenderPreset(name="Test Preset", is_system=False, layout_style="post")
        db_session.add(preset)
        db_session.flush()

        group = db_session.query(Group).first()
        config = db_session.query(GroupConfig).filter(GroupConfig.group_id == group.id).first()
        if not config:
            config = GroupConfig(group_id=group.id, render_preset_id=preset.id)
            db_session.add(config)
        else:
            config.render_preset_id = preset.id
        db_session.commit()

        resp = client.get(f"/groups/{group.id}/effective-config")
        data = resp.json()
        assert data["render_preset_id"] == preset.id
        assert data["sources"]["render_preset_id"] == "group"

    def test_404_on_missing_project(self, client):
        resp = client.get("/projects/9999/effective-config")
        assert resp.status_code == 404

    def test_404_on_missing_group(self, client):
        resp = client.get("/groups/9999/effective-config")
        assert resp.status_code == 404
