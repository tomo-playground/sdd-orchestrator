"""Router tests for /groups endpoints (CRUD + effective-config)."""

from models.storyboard import Storyboard


class TestGroupsRouter:
    """CRUD tests for groups API."""

    def _create_project(self, client) -> int:
        return client.post("/api/v1/projects", json={"name": "TestProject"}).json()["id"]

    def test_list_groups(self, client):
        """seed_default_project_group creates Group(1)."""
        resp = client.get("/api/v1/groups")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_list_groups_filter_by_project(self, client):
        pid = self._create_project(client)
        client.post("/api/v1/groups", json={"project_id": pid, "name": "G1"})
        client.post("/api/v1/groups", json={"project_id": pid, "name": "G2"})

        resp = client.get(f"/api/v1/groups?project_id={pid}")
        assert resp.status_code == 200
        names = [g["name"] for g in resp.json()]
        assert "G1" in names
        assert "G2" in names

    def test_create_group(self, client):
        pid = self._create_project(client)
        body = {"project_id": pid, "name": "My Series", "description": "desc"}
        resp = client.post("/api/v1/groups", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Series"
        assert data["project_id"] == pid

    def test_create_group_invalid_project(self, client):
        body = {"project_id": 9999, "name": "Orphan"}
        resp = client.post("/api/v1/groups", json=body)
        assert resp.status_code == 404

    def test_create_group_includes_config_fields(self, client):
        pid = self._create_project(client)
        gid = client.post("/api/v1/groups", json={"project_id": pid, "name": "WithConfig"}).json()["id"]

        resp = client.get(f"/api/v1/groups/{gid}")
        assert resp.status_code == 200
        data = resp.json()
        # Config fields are part of group response
        assert "render_preset_id" in data
        assert "style_profile_id" in data
        assert "narrator_voice_preset_id" in data
        assert "channel_dna" in data

    def test_get_group(self, client):
        pid = self._create_project(client)
        gid = client.post("/api/v1/groups", json={"project_id": pid, "name": "GetMe"}).json()["id"]

        resp = client.get(f"/api/v1/groups/{gid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "GetMe"

    def test_get_group_not_found(self, client):
        resp = client.get("/api/v1/groups/9999")
        assert resp.status_code == 404

    def test_update_group(self, client):
        pid = self._create_project(client)
        gid = client.post("/api/v1/groups", json={"project_id": pid, "name": "Before"}).json()["id"]

        resp = client.put(f"/api/v1/groups/{gid}", json={"name": "After"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "After"

    def test_update_group_config_fields(self, client):
        """PUT /groups/{id} can update config fields (render_preset_id, etc.)."""
        pid = self._create_project(client)
        gid = client.post("/api/v1/groups", json={"project_id": pid, "name": "G"}).json()["id"]

        resp = client.put(f"/api/v1/groups/{gid}", json={"narrator_voice_preset_id": None})
        assert resp.status_code == 200
        assert resp.json()["narrator_voice_preset_id"] is None

    def test_update_group_partial(self, client):
        """Partial update preserves other fields."""
        pid = self._create_project(client)
        gid = client.post("/api/v1/groups", json={"project_id": pid, "name": "Original"}).json()["id"]

        resp = client.put(f"/api/v1/groups/{gid}", json={"description": "new desc"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == "new desc"
        assert data["name"] == "Original"

    def test_update_group_not_found(self, client):
        resp = client.put("/api/v1/groups/9999", json={"name": "X"})
        assert resp.status_code == 404

    def test_delete_group(self, client):
        pid = self._create_project(client)
        gid = client.post("/api/v1/groups", json={"project_id": pid, "name": "ToDelete"}).json()["id"]

        resp = client.delete(f"/api/v1/groups/{gid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        resp = client.get(f"/api/v1/groups/{gid}")
        assert resp.status_code == 404

    def test_delete_group_not_found(self, client):
        resp = client.delete("/api/v1/groups/9999")
        assert resp.status_code == 404

    def test_delete_group_with_active_storyboards_returns_409(self, client, db_session):
        pid = self._create_project(client)
        gid = client.post("/api/v1/groups", json={"project_id": pid, "name": "HasSB"}).json()["id"]

        sb = Storyboard(group_id=gid, title="Active SB")
        db_session.add(sb)
        db_session.commit()

        resp = client.delete(f"/api/v1/groups/{gid}")
        assert resp.status_code == 409
        assert "existing storyboards" in resp.json()["detail"].lower()


class TestGroupEffectiveConfig:
    """Effective config (cascading) tests."""

    def _create_group(self, client) -> int:
        pid = client.post("/api/v1/projects", json={"name": "P"}).json()["id"]
        return client.post("/api/v1/groups", json={"project_id": pid, "name": "G"}).json()["id"]

    def test_effective_config(self, client):
        gid = self._create_group(client)
        resp = client.get(f"/api/v1/groups/{gid}/effective-config")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data

    def test_effective_config_not_found(self, client):
        resp = client.get("/api/v1/groups/9999/effective-config")
        assert resp.status_code == 404

    def test_effective_config_reflects_group_fields(self, client):
        """Group fields are reflected in effective config."""
        gid = self._create_group(client)

        resp = client.get(f"/api/v1/groups/{gid}/effective-config")
        assert resp.status_code == 200
        data = resp.json()
        # style_profile_id from system default
        assert "style_profile_id" in data
