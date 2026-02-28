"""Tests for Render Preset CRUD API."""

from fastapi.testclient import TestClient


def _seed_system_preset(client: TestClient) -> dict:
    """Create a system preset via DB (simulates migration seed)."""
    # Use the API to create, then we test against it
    res = client.post(
        "/api/admin/render-presets",
        json={
            "name": "Test System",
            "layout_style": "post",
            "bgm_volume": 0.4,
        },
    )
    assert res.status_code == 201
    return res.json()


# --- List ---


def test_list_render_presets_empty(client: TestClient):
    res = client.get("/api/v1/render-presets")
    assert res.status_code == 200
    assert res.json() == []


def test_list_render_presets_returns_created(client: TestClient):
    _seed_system_preset(client)
    res = client.get("/api/v1/render-presets")
    assert res.status_code == 200
    assert len(res.json()) == 1


# --- Get ---


def test_get_render_preset(client: TestClient):
    created = _seed_system_preset(client)
    res = client.get(f"/api/v1/render-presets/{created['id']}")
    assert res.status_code == 200
    assert res.json()["name"] == "Test System"
    assert res.json()["layout_style"] == "post"


def test_get_render_preset_not_found(client: TestClient):
    res = client.get("/api/v1/render-presets/9999")
    assert res.status_code == 404


# --- Create ---


def test_create_render_preset(client: TestClient):
    res = client.post(
        "/api/admin/render-presets",
        json={
            "name": "My Custom",
            "layout_style": "full",
            "bgm_volume": 0.15,
            "transition_type": "fade",
            "speed_multiplier": 1.0,
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "My Custom"
    assert data["is_system"] is False
    assert data["layout_style"] == "full"
    assert data["bgm_volume"] == 0.15
    assert data["speed_multiplier"] == 1.0


def test_create_render_preset_minimal(client: TestClient):
    res = client.post("/api/admin/render-presets", json={"name": "Bare Minimum"})
    assert res.status_code == 201
    assert res.json()["name"] == "Bare Minimum"
    assert res.json()["is_system"] is False


# --- Update ---


def test_update_render_preset(client: TestClient):
    created = client.post("/api/admin/render-presets", json={"name": "Editable"}).json()
    res = client.put(
        f"/api/admin/render-presets/{created['id']}",
        json={
            "name": "Edited",
            "bgm_volume": 0.5,
        },
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Edited"
    assert res.json()["bgm_volume"] == 0.5


def test_update_render_preset_not_found(client: TestClient):
    res = client.put("/api/admin/render-presets/9999", json={"name": "X"})
    assert res.status_code == 404


def test_update_system_preset_allowed(client: TestClient, db_session):
    """System presets (is_system=True) can be modified via API."""
    from models.render_preset import RenderPreset

    preset = RenderPreset(name="System One", is_system=True, layout_style="post")
    db_session.add(preset)
    db_session.commit()
    db_session.refresh(preset)

    res = client.put(f"/api/admin/render-presets/{preset.id}", json={"name": "Updated System"})
    assert res.status_code == 200
    assert res.json()["name"] == "Updated System"


# --- Delete ---


def test_delete_render_preset(client: TestClient):
    created = client.post("/api/admin/render-presets", json={"name": "Deletable"}).json()
    res = client.delete(f"/api/admin/render-presets/{created['id']}")
    assert res.status_code == 200
    assert res.json()["status"] == "deleted"

    # Confirm gone
    res = client.get(f"/api/v1/render-presets/{created['id']}")
    assert res.status_code == 404


def test_delete_render_preset_not_found(client: TestClient):
    res = client.delete("/api/admin/render-presets/9999")
    assert res.status_code == 404


def test_delete_system_preset_allowed(client: TestClient, db_session):
    """System presets can be deleted."""
    from models.render_preset import RenderPreset

    preset = RenderPreset(name="Deletable System", is_system=True)
    db_session.add(preset)
    db_session.commit()
    db_session.refresh(preset)

    res = client.delete(f"/api/admin/render-presets/{preset.id}")
    assert res.status_code == 200
    assert res.json()["status"] == "deleted"


# --- Group + Preset Integration ---


def test_create_group_with_preset(client: TestClient):
    preset = client.post(
        "/api/admin/render-presets",
        json={
            "name": "For Group",
            "layout_style": "post",
            "bgm_volume": 0.4,
        },
    ).json()

    group = client.post(
        "/api/v1/groups",
        json={
            "project_id": 1,
            "name": "Test Series",
            "render_preset_id": preset["id"],
            "style_profile_id": 1,
        },
    )
    assert group.status_code == 201

    # Verify render_preset_id is stored on group
    gid = group.json()["id"]
    group_data = client.get(f"/api/v1/groups/{gid}").json()
    assert group_data["render_preset_id"] == preset["id"]


def test_get_group_includes_preset(client: TestClient):
    preset = client.post(
        "/api/admin/render-presets",
        json={
            "name": "Nested Test",
            "transition_type": "fade",
        },
    ).json()

    created = client.post(
        "/api/v1/groups",
        json={
            "project_id": 1,
            "name": "Nested Group",
            "render_preset_id": preset["id"],
            "style_profile_id": 1,
        },
    ).json()

    resp = client.get(f"/api/v1/groups/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["render_preset_id"] == preset["id"]


def test_group_without_preset(client: TestClient):
    group = client.post(
        "/api/v1/groups",
        json={
            "project_id": 1,
            "name": "No Preset Group",
            "style_profile_id": 1,
        },
    )
    assert group.status_code == 201

    # Verify group has no preset
    gid = group.json()["id"]
    group_data = client.get(f"/api/v1/groups/{gid}").json()
    assert group_data["render_preset_id"] is None
