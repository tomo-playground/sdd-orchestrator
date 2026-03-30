"""Tests for cascading config resolver."""

from schemas import RenderPresetResponse
from services.config_resolver import resolve_effective_config


# ---------------------------------------------------------------------------
# Helper: simple namespace to simulate ORM objects
# ---------------------------------------------------------------------------
class _Obj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# ===========================================================================
# Unit tests — RenderPresetResponse schema
# ===========================================================================


class TestRenderPresetResponseSchema:
    """bgm_mode NULL 처리 — Sentry #369 회귀 방지."""

    def test_bgm_mode_none_coerced_to_manual(self):
        """bgm_mode=None (DB NULL) 시 'manual'로 복구되어 ValidationError 없음."""
        obj = _Obj(id=1, name="Test", bgm_mode=None)
        resp = RenderPresetResponse.model_validate(obj)
        assert resp.bgm_mode == "manual"

    def test_bgm_mode_manual_preserved(self):
        obj = _Obj(id=1, name="Test", bgm_mode="manual")
        resp = RenderPresetResponse.model_validate(obj)
        assert resp.bgm_mode == "manual"

    def test_bgm_mode_auto_preserved(self):
        obj = _Obj(id=1, name="Test", bgm_mode="auto")
        resp = RenderPresetResponse.model_validate(obj)
        assert resp.bgm_mode == "auto"


class TestRenderPresetUpdateSchema:
    """RenderPresetUpdate bgm_mode 쓰기 경로 방어 — Sentry #369 근본 원인."""

    def test_bgm_mode_null_rejected(self):
        """bgm_mode=null → ValidationError (NOT NULL 컬럼 보호)."""
        import pytest
        from pydantic import ValidationError

        from schemas import RenderPresetUpdate

        with pytest.raises(ValidationError):
            RenderPresetUpdate(bgm_mode=None)

    def test_bgm_mode_unset_excluded(self):
        """bgm_mode 미전송 시 exclude_unset에서 제외."""
        from schemas import RenderPresetUpdate

        update = RenderPresetUpdate(name="test")
        dump = update.model_dump(exclude_unset=True)
        assert "bgm_mode" not in dump

    def test_bgm_mode_valid_values_accepted(self):
        """manual/auto 정상 수락."""
        from schemas import RenderPresetUpdate

        for mode in ("manual", "auto"):
            update = RenderPresetUpdate(bgm_mode=mode)
            dump = update.model_dump(exclude_unset=True)
            assert dump["bgm_mode"] == mode


# ===========================================================================
# Unit tests — resolve_effective_config pure function
# ===========================================================================


class TestResolveEffectiveConfig:
    def test_project_only_returns_empty(self):
        """Project model has no config fields; project-only returns empty."""
        project = _Obj()
        result = resolve_effective_config(project)
        assert result["values"] == {}
        assert result["sources"] == {}

    def test_group_provides_values(self):
        """Group directly provides config values."""
        project = _Obj()
        group = _Obj(render_preset_id=20, style_profile_id=3, narrator_voice_preset_id=None)
        result = resolve_effective_config(project, group)
        assert result["values"]["render_preset_id"] == 20
        assert result["sources"]["render_preset_id"] == "group"
        assert result["values"]["style_profile_id"] == 3
        assert result["sources"]["style_profile_id"] == "group"

    def test_all_none_returns_empty(self):
        project = _Obj()
        result = resolve_effective_config(project)
        assert result["values"] == {}
        assert result["sources"] == {}

    def test_no_group(self):
        """Without a group, no config is resolved."""
        project = _Obj()
        result = resolve_effective_config(project, None)
        assert result["values"] == {}
        assert result["sources"] == {}

    def test_group_with_all_none_fields(self):
        """Group with all None fields resolves nothing."""
        project = _Obj()
        group = _Obj(render_preset_id=None, style_profile_id=None, narrator_voice_preset_id=None)
        result = resolve_effective_config(project, group)
        assert result["values"] == {}
        assert result["sources"] == {}


# ===========================================================================
# API integration tests
# ===========================================================================


class TestEffectiveConfigAPI:
    def test_project_effective_config(self, client, db_session):
        from models.project import Project

        project = db_session.query(Project).first()
        resp = client.get(f"/api/v1/projects/{project.id}/effective-config")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data

    def test_group_effective_config(self, client, db_session):
        from models.group import Group

        group = db_session.query(Group).first()
        resp = client.get(f"/api/v1/groups/{group.id}/effective-config")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data

    def test_group_sets_preset(self, client, db_session):
        """Group is the SSOT for cascading config."""
        from models.group import Group
        from models.render_preset import RenderPreset

        preset = RenderPreset(name="Test Preset", is_system=False, layout_style="post")
        db_session.add(preset)
        db_session.flush()

        group = db_session.query(Group).first()
        group.render_preset_id = preset.id
        db_session.commit()

        resp = client.get(f"/api/v1/groups/{group.id}/effective-config")
        data = resp.json()
        assert data["render_preset_id"] == preset.id
        assert data["sources"]["render_preset_id"] == "group"

    def test_render_preset_object_included(self, client, db_session):
        """EffectiveConfig includes full render_preset object for frontend."""
        from models.group import Group
        from models.render_preset import RenderPreset

        preset = RenderPreset(
            name="Full Preset Test",
            is_system=False,
            bgm_file="test.mp3",
            bgm_volume=0.5,
            audio_ducking=True,
            scene_text_font="NotoSans",
            layout_style="full",
            frame_style="clean",
            transition_type="crossfade",
            ken_burns_preset="zoom_in",
            ken_burns_intensity=1.2,
            speed_multiplier=1.1,
        )
        db_session.add(preset)
        db_session.flush()

        group = db_session.query(Group).first()
        group.render_preset_id = preset.id
        db_session.commit()

        resp = client.get(f"/api/v1/groups/{group.id}/effective-config")
        data = resp.json()

        assert data["render_preset_id"] == preset.id
        assert data["render_preset"] is not None
        rp = data["render_preset"]
        assert rp["name"] == "Full Preset Test"
        assert rp["bgm_file"] == "test.mp3"
        assert rp["bgm_volume"] == 0.5
        assert rp["audio_ducking"] is True
        assert rp["scene_text_font"] == "NotoSans"
        assert rp["layout_style"] == "full"
        assert rp["frame_style"] == "clean"
        assert rp["transition_type"] == "crossfade"
        assert rp["ken_burns_preset"] == "zoom_in"
        assert rp["ken_burns_intensity"] == 1.2
        assert rp["speed_multiplier"] == 1.1

    def test_render_preset_null_when_no_preset(self, client, db_session):
        """render_preset is null when no preset configured."""
        from models.group import Group

        group = db_session.query(Group).first()
        group.render_preset_id = None
        db_session.commit()

        resp = client.get(f"/api/v1/groups/{group.id}/effective-config")
        data = resp.json()
        assert data["render_preset"] is None

    def test_404_on_missing_project(self, client):
        resp = client.get("/api/v1/projects/9999/effective-config")
        assert resp.status_code == 404

    def test_404_on_missing_group(self, client):
        resp = client.get("/api/v1/groups/9999/effective-config")
        assert resp.status_code == 404
