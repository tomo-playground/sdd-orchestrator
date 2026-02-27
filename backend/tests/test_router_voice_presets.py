"""Router tests for /voice-presets endpoints (CRUD)."""


class TestVoicePresetsRouter:
    """CRUD tests for voice presets API."""

    def test_list_empty(self, client):
        resp = client.get("/api/v1/voice-presets")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_preset(self, client):
        body = {
            "name": "Narrator Voice",
            "voice_design_prompt": "calm male narrator",
            "language": "korean",
        }
        resp = client.post("/api/admin/voice-presets", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Narrator Voice"
        assert data["voice_design_prompt"] == "calm male narrator"
        assert data["language"] == "korean"
        assert data["source_type"] == "generated"
        assert data["is_system"] is False

    def test_create_preset_minimal(self, client):
        body = {"name": "Minimal Voice"}
        resp = client.post("/api/admin/voice-presets", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Minimal Voice"
        assert data["language"] == "korean"  # default

    def test_get_preset(self, client):
        pid = client.post("/api/admin/voice-presets", json={"name": "GetMe"}).json()["id"]

        resp = client.get(f"/api/v1/voice-presets/{pid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "GetMe"

    def test_get_preset_not_found(self, client):
        resp = client.get("/api/v1/voice-presets/9999")
        assert resp.status_code == 404

    def test_update_preset(self, client):
        pid = client.post("/api/admin/voice-presets", json={"name": "Before"}).json()["id"]

        resp = client.put(
            f"/api/admin/voice-presets/{pid}",
            json={"name": "After", "voice_design_prompt": "new prompt"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "After"
        assert data["voice_design_prompt"] == "new prompt"

    def test_update_preset_partial(self, client):
        pid = client.post(
            "/api/admin/voice-presets",
            json={"name": "Keep", "description": "original"},
        ).json()["id"]

        resp = client.put(f"/api/admin/voice-presets/{pid}", json={"name": "Changed"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Changed"
        assert data["description"] == "original"

    def test_update_preset_not_found(self, client):
        resp = client.put("/api/admin/voice-presets/9999", json={"name": "X"})
        assert resp.status_code == 404

    def test_delete_preset(self, client):
        pid = client.post("/api/admin/voice-presets", json={"name": "ToDelete"}).json()["id"]

        resp = client.delete(f"/api/admin/voice-presets/{pid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        resp = client.get(f"/api/v1/voice-presets/{pid}")
        assert resp.status_code == 404

    def test_delete_preset_not_found(self, client):
        resp = client.delete("/api/admin/voice-presets/9999")
        assert resp.status_code == 404

    def test_list_after_create(self, client):
        client.post("/api/admin/voice-presets", json={"name": "V1"})
        client.post("/api/admin/voice-presets", json={"name": "V2"})

        resp = client.get("/api/v1/voice-presets")
        assert resp.status_code == 200
        names = [p["name"] for p in resp.json()]
        assert "V1" in names
        assert "V2" in names

    def test_response_includes_audio_url_field(self, client):
        pid = client.post("/api/admin/voice-presets", json={"name": "AudioTest"}).json()["id"]
        resp = client.get(f"/api/v1/voice-presets/{pid}")
        data = resp.json()
        assert "audio_url" in data
        assert data["audio_url"] is None  # no audio attached
