"""Router tests for /groups endpoints (CRUD + config + effective-config)."""

from models.storyboard import Storyboard


class TestGroupsRouter:
    """CRUD tests for groups API."""

    def _create_project(self, client) -> int:
        return client.post("/projects", json={"name": "TestProject"}).json()["id"]

    def test_list_groups(self, client):
        """seed_default_project_group creates Group(1)."""
        resp = client.get("/groups")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_list_groups_filter_by_project(self, client):
        pid = self._create_project(client)
        client.post("/groups", json={"project_id": pid, "name": "G1"})
        client.post("/groups", json={"project_id": pid, "name": "G2"})

        resp = client.get(f"/groups?project_id={pid}")
        assert resp.status_code == 200
        names = [g["name"] for g in resp.json()]
        assert "G1" in names
        assert "G2" in names

    def test_create_group(self, client):
        pid = self._create_project(client)
        body = {"project_id": pid, "name": "My Series", "description": "desc"}
        resp = client.post("/groups", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Series"
        assert data["project_id"] == pid

    def test_create_group_invalid_project(self, client):
        body = {"project_id": 9999, "name": "Orphan"}
        resp = client.post("/groups", json=body)
        assert resp.status_code == 404

    def test_create_group_auto_creates_config(self, client):
        pid = self._create_project(client)
        gid = client.post("/groups", json={"project_id": pid, "name": "WithConfig"}).json()["id"]

        resp = client.get(f"/groups/{gid}/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["group_id"] == gid
        # SD system defaults should be populated
        assert data["sd_steps"] is not None

    def test_get_group(self, client):
        pid = self._create_project(client)
        gid = client.post("/groups", json={"project_id": pid, "name": "GetMe"}).json()["id"]

        resp = client.get(f"/groups/{gid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "GetMe"

    def test_get_group_not_found(self, client):
        resp = client.get("/groups/9999")
        assert resp.status_code == 404

    def test_update_group(self, client):
        pid = self._create_project(client)
        gid = client.post("/groups", json={"project_id": pid, "name": "Before"}).json()["id"]

        resp = client.put(f"/groups/{gid}", json={"name": "After"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "After"

    def test_update_group_not_found(self, client):
        resp = client.put("/groups/9999", json={"name": "X"})
        assert resp.status_code == 404

    def test_delete_group(self, client):
        pid = self._create_project(client)
        gid = client.post("/groups", json={"project_id": pid, "name": "ToDelete"}).json()["id"]

        resp = client.delete(f"/groups/{gid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        resp = client.get(f"/groups/{gid}")
        assert resp.status_code == 404

    def test_delete_group_not_found(self, client):
        resp = client.delete("/groups/9999")
        assert resp.status_code == 404

    def test_delete_group_with_active_storyboards_returns_409(self, client, db_session):
        pid = self._create_project(client)
        gid = client.post("/groups", json={"project_id": pid, "name": "HasSB"}).json()["id"]

        sb = Storyboard(group_id=gid, title="Active SB")
        db_session.add(sb)
        db_session.commit()

        resp = client.delete(f"/groups/{gid}")
        assert resp.status_code == 409
        assert "existing storyboards" in resp.json()["detail"].lower()


class TestGroupConfig:
    """Group config CRUD tests."""

    def _create_group(self, client) -> int:
        pid = client.post("/projects", json={"name": "P"}).json()["id"]
        return client.post("/groups", json={"project_id": pid, "name": "G"}).json()["id"]

    def test_get_config(self, client):
        gid = self._create_group(client)
        resp = client.get(f"/groups/{gid}/config")
        assert resp.status_code == 200
        assert resp.json()["group_id"] == gid

    def test_get_config_group_not_found(self, client):
        resp = client.get("/groups/9999/config")
        assert resp.status_code == 404

    def test_update_config(self, client):
        gid = self._create_group(client)
        resp = client.put(f"/groups/{gid}/config", json={"language": "english", "sd_steps": 30})
        assert resp.status_code == 200
        data = resp.json()
        assert data["language"] == "english"
        assert data["sd_steps"] == 30

    def test_update_config_partial(self, client):
        gid = self._create_group(client)
        client.put(f"/groups/{gid}/config", json={"language": "korean", "sd_steps": 20})

        resp = client.put(f"/groups/{gid}/config", json={"sd_steps": 40})
        assert resp.status_code == 200
        data = resp.json()
        assert data["sd_steps"] == 40
        assert data["language"] == "korean"

    def test_update_config_group_not_found(self, client):
        resp = client.put("/groups/9999/config", json={"language": "en"})
        assert resp.status_code == 404


class TestGroupEffectiveConfig:
    """Effective config (cascading) tests."""

    def _create_group(self, client) -> int:
        pid = client.post("/projects", json={"name": "P"}).json()["id"]
        return client.post("/groups", json={"project_id": pid, "name": "G"}).json()["id"]

    def test_effective_config(self, client):
        gid = self._create_group(client)
        resp = client.get(f"/groups/{gid}/effective-config")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data
        assert "sd_steps" in data

    def test_effective_config_not_found(self, client):
        resp = client.get("/groups/9999/effective-config")
        assert resp.status_code == 404

    def test_effective_config_reflects_group_override(self, client):
        gid = self._create_group(client)
        client.put(f"/groups/{gid}/config", json={"sd_steps": 50})

        resp = client.get(f"/groups/{gid}/effective-config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["sd_steps"] == 50
        assert data["sources"]["sd_steps"] == "group"
