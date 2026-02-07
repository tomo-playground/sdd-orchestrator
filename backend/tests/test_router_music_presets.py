"""Router tests for /music-presets endpoints (CRUD)."""


class TestMusicPresetsRouter:
    """CRUD tests for music presets API."""

    def test_list_empty(self, client):
        resp = client.get("/music-presets")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_preset(self, client):
        body = {"name": "Lo-fi Chill", "prompt": "ambient lo-fi", "duration": 30.0}
        resp = client.post("/music-presets", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Lo-fi Chill"
        assert data["prompt"] == "ambient lo-fi"
        assert data["duration"] == 30.0
        assert data["is_system"] is False

    def test_get_preset(self, client):
        body = {"name": "Test BGM"}
        resp = client.post("/music-presets", json=body)
        pid = resp.json()["id"]

        resp = client.get(f"/music-presets/{pid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test BGM"

    def test_get_preset_not_found(self, client):
        resp = client.get("/music-presets/9999")
        assert resp.status_code == 404

    def test_update_preset(self, client):
        body = {"name": "Before"}
        resp = client.post("/music-presets", json=body)
        pid = resp.json()["id"]

        resp = client.put(f"/music-presets/{pid}", json={"name": "After", "prompt": "new prompt"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "After"
        assert data["prompt"] == "new prompt"

    def test_update_preset_not_found(self, client):
        resp = client.put("/music-presets/9999", json={"name": "X"})
        assert resp.status_code == 404

    def test_delete_preset(self, client):
        body = {"name": "ToDelete"}
        resp = client.post("/music-presets", json=body)
        pid = resp.json()["id"]

        resp = client.delete(f"/music-presets/{pid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        resp = client.get(f"/music-presets/{pid}")
        assert resp.status_code == 404

    def test_delete_preset_not_found(self, client):
        resp = client.delete("/music-presets/9999")
        assert resp.status_code == 404

    def test_list_after_create(self, client):
        client.post("/music-presets", json={"name": "A"})
        client.post("/music-presets", json={"name": "B"})

        resp = client.get("/music-presets")
        assert resp.status_code == 200
        names = [p["name"] for p in resp.json()]
        assert "A" in names
        assert "B" in names
