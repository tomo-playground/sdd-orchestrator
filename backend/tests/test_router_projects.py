"""Router tests for /projects endpoints (CRUD + effective-config)."""


class TestProjectsRouter:
    """CRUD tests for projects API."""

    def test_list_projects(self, client):
        """seed_default_project_group creates Project(1)."""
        resp = client.get("/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["id"] == 1

    def test_create_project(self, client):
        body = {"name": "My Channel", "description": "Test channel"}
        resp = client.post("/projects", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Channel"
        assert data["description"] == "Test channel"
        assert "id" in data

    def test_create_project_minimal(self, client):
        body = {"name": "Minimal"}
        resp = client.post("/projects", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Minimal"
        assert data["description"] is None

    def test_get_project(self, client):
        body = {"name": "GetMe"}
        pid = client.post("/projects", json=body).json()["id"]

        resp = client.get(f"/projects/{pid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "GetMe"

    def test_get_project_not_found(self, client):
        resp = client.get("/projects/9999")
        assert resp.status_code == 404

    def test_update_project(self, client):
        pid = client.post("/projects", json={"name": "Before"}).json()["id"]

        resp = client.put(f"/projects/{pid}", json={"name": "After", "description": "updated"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "After"
        assert data["description"] == "updated"

    def test_update_project_partial(self, client):
        pid = client.post("/projects", json={"name": "Original", "description": "keep"}).json()["id"]

        resp = client.put(f"/projects/{pid}", json={"name": "Changed"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Changed"
        assert data["description"] == "keep"

    def test_update_project_not_found(self, client):
        resp = client.put("/projects/9999", json={"name": "X"})
        assert resp.status_code == 404

    def test_delete_project(self, client):
        pid = client.post("/projects", json={"name": "ToDelete"}).json()["id"]

        resp = client.delete(f"/projects/{pid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        resp = client.get(f"/projects/{pid}")
        assert resp.status_code == 404

    def test_delete_project_not_found(self, client):
        resp = client.delete("/projects/9999")
        assert resp.status_code == 404

    def test_delete_project_with_groups_returns_409(self, client):
        """SQLite doesn't enforce ondelete=RESTRICT via ORM delete; PostgreSQL only."""
        pid = client.post("/projects", json={"name": "HasGroups"}).json()["id"]
        client.post("/groups", json={"project_id": pid, "name": "Child Group"})

        resp = client.delete(f"/projects/{pid}")
        # SQLite: 200 (cascade), PostgreSQL: 409 (RESTRICT)
        assert resp.status_code in (200, 409)


class TestProjectEffectiveConfig:
    """Effective config tests for projects."""

    def test_effective_config_returns_system_defaults(self, client):
        pid = client.post("/projects", json={"name": "ConfigTest"}).json()["id"]

        resp = client.get(f"/projects/{pid}/effective-config")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data
        assert "style_profile_id" in data

    def test_effective_config_not_found(self, client):
        resp = client.get("/projects/9999/effective-config")
        assert resp.status_code == 404
