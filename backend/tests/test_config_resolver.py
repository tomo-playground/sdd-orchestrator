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
        project = _Obj(render_preset_id=10, default_character_id=1, default_style_profile_id=2)
        result = resolve_effective_config(project)
        assert result["values"] == {
            "render_preset_id": 10,
            "default_character_id": 1,
            "default_style_profile_id": 2,
        }
        assert all(v == "project" for v in result["sources"].values())

    def test_group_overrides_project(self):
        project = _Obj(render_preset_id=10, default_character_id=1, default_style_profile_id=2)
        group = _Obj(render_preset_id=20, default_character_id=None, default_style_profile_id=3)
        result = resolve_effective_config(project, group)
        assert result["values"]["render_preset_id"] == 20
        assert result["sources"]["render_preset_id"] == "group"
        # character inherits from project
        assert result["values"]["default_character_id"] == 1
        assert result["sources"]["default_character_id"] == "project"
        # style overridden by group
        assert result["values"]["default_style_profile_id"] == 3
        assert result["sources"]["default_style_profile_id"] == "group"

    def test_storyboard_overrides_all(self):
        project = _Obj(render_preset_id=10, default_character_id=1, default_style_profile_id=2)
        group = _Obj(render_preset_id=20, default_character_id=None, default_style_profile_id=3)
        storyboard = _Obj(render_preset_id=None, default_character_id=99, default_style_profile_id=None)
        result = resolve_effective_config(project, group, storyboard)
        # render_preset: group wins (storyboard is None)
        assert result["values"]["render_preset_id"] == 20
        # character: storyboard wins
        assert result["values"]["default_character_id"] == 99
        assert result["sources"]["default_character_id"] == "storyboard"
        # style: group wins (storyboard is None)
        assert result["values"]["default_style_profile_id"] == 3

    def test_all_none_returns_empty(self):
        project = _Obj(render_preset_id=None, default_character_id=None, default_style_profile_id=None)
        result = resolve_effective_config(project)
        assert result["values"] == {}
        assert result["sources"] == {}

    def test_no_group_no_storyboard(self):
        project = _Obj(render_preset_id=5, default_character_id=None, default_style_profile_id=None)
        result = resolve_effective_config(project, None, None)
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
        assert "render_preset_id" in data

    def test_group_effective_config(self, client, db_session):
        from models.group import Group
        group = db_session.query(Group).first()
        resp = client.get(f"/groups/{group.id}/effective-config")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data

    def test_group_inherits_project_preset(self, client, db_session):
        from models.project import Project
        from models.render_preset import RenderPreset

        # Create a preset
        preset = RenderPreset(name="Test Preset", is_system=False, layout_style="post")
        db_session.add(preset)
        db_session.flush()

        # Set on project
        project = db_session.query(Project).first()
        project.render_preset_id = preset.id
        db_session.commit()

        from models.group import Group
        group = db_session.query(Group).first()
        resp = client.get(f"/groups/{group.id}/effective-config")
        data = resp.json()
        assert data["render_preset_id"] == preset.id
        assert data["sources"]["render_preset_id"] == "project"

    def test_group_overrides_project_preset(self, client, db_session):
        from models.group import Group
        from models.project import Project
        from models.render_preset import RenderPreset

        preset_a = RenderPreset(name="Preset A", is_system=False, layout_style="post")
        preset_b = RenderPreset(name="Preset B", is_system=False, layout_style="full")
        db_session.add_all([preset_a, preset_b])
        db_session.flush()

        project = db_session.query(Project).first()
        project.render_preset_id = preset_a.id

        group = db_session.query(Group).first()
        group.render_preset_id = preset_b.id
        db_session.commit()

        resp = client.get(f"/groups/{group.id}/effective-config")
        data = resp.json()
        assert data["render_preset_id"] == preset_b.id
        assert data["sources"]["render_preset_id"] == "group"
        assert data["render_preset"]["layout_style"] == "full"

    def test_404_on_missing_project(self, client):
        resp = client.get("/projects/9999/effective-config")
        assert resp.status_code == 404

    def test_404_on_missing_group(self, client):
        resp = client.get("/groups/9999/effective-config")
        assert resp.status_code == 404
