"""Router tests for /render-presets endpoints (CRUD)."""


class TestRenderPresetsRouter:
    """CRUD tests for render presets API."""

    def test_list_render_presets(self, client):
        resp = client.get("/render-presets")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_preset(self, client):
        body = {
            "name": "Cinematic",
            "layout_style": "full",
            "ken_burns_preset": "slow_zoom",
            "transition_type": "crossfade",
        }
        resp = client.post("/render-presets", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Cinematic"
        assert data["layout_style"] == "full"
        assert data["ken_burns_preset"] == "slow_zoom"
        assert data["transition_type"] == "crossfade"
        assert data["is_system"] is False

    def test_create_preset_minimal(self, client):
        body = {"name": "Minimal"}
        resp = client.post("/render-presets", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Minimal"
        assert data["layout_style"] is None

    def test_get_preset(self, client):
        pid = client.post("/render-presets", json={"name": "GetMe"}).json()["id"]

        resp = client.get(f"/render-presets/{pid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "GetMe"

    def test_get_preset_not_found(self, client):
        resp = client.get("/render-presets/9999")
        assert resp.status_code == 404

    def test_update_preset(self, client):
        pid = client.post("/render-presets", json={"name": "Before"}).json()["id"]

        resp = client.put(
            f"/render-presets/{pid}",
            json={"name": "After", "layout_style": "post", "bgm_volume": 0.5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "After"
        assert data["layout_style"] == "post"
        assert data["bgm_volume"] == 0.5

    def test_update_preset_partial(self, client):
        pid = client.post(
            "/render-presets",
            json={"name": "Keep", "description": "original", "layout_style": "full"},
        ).json()["id"]

        resp = client.put(f"/render-presets/{pid}", json={"name": "Changed"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Changed"
        assert data["description"] == "original"
        assert data["layout_style"] == "full"

    def test_update_preset_not_found(self, client):
        resp = client.put("/render-presets/9999", json={"name": "X"})
        assert resp.status_code == 404

    def test_delete_preset(self, client):
        pid = client.post("/render-presets", json={"name": "ToDelete"}).json()["id"]

        resp = client.delete(f"/render-presets/{pid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        resp = client.get(f"/render-presets/{pid}")
        assert resp.status_code == 404

    def test_delete_preset_not_found(self, client):
        resp = client.delete("/render-presets/9999")
        assert resp.status_code == 404

    def test_list_after_create(self, client):
        client.post("/render-presets", json={"name": "R1"})
        client.post("/render-presets", json={"name": "R2"})

        resp = client.get("/render-presets")
        assert resp.status_code == 200
        names = [p["name"] for p in resp.json()]
        assert "R1" in names
        assert "R2" in names

    def test_all_fields_roundtrip(self, client):
        body = {
            "name": "Full Preset",
            "description": "All fields",
            "bgm_file": "bgm.mp3",
            "bgm_volume": 0.3,
            "bgm_mode": "manual",
            "audio_ducking": True,
            "scene_text_font": "NotoSans",
            "layout_style": "post",
            "frame_style": "instagram",
            "transition_type": "fade",
            "ken_burns_preset": "gentle",
            "ken_burns_intensity": 0.8,
            "speed_multiplier": 1.2,
        }
        pid = client.post("/render-presets", json=body).json()["id"]

        resp = client.get(f"/render-presets/{pid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["bgm_file"] == "bgm.mp3"
        assert data["bgm_volume"] == 0.3
        assert data["bgm_mode"] == "manual"
        assert data["audio_ducking"] is True
        assert data["scene_text_font"] == "NotoSans"
        assert data["layout_style"] == "post"
        assert data["frame_style"] == "instagram"
        assert data["transition_type"] == "fade"
        assert data["ken_burns_preset"] == "gentle"
        assert data["ken_burns_intensity"] == 0.8
        assert data["speed_multiplier"] == 1.2

    def test_music_preset_id_roundtrip(self, client):
        """music_preset_id FK 포함 생성/수정/해제 라운드트립."""
        # 1) MusicPreset 생성
        mp = client.post("/music-presets", json={"name": "Test BGM", "prompt": "calm piano"})
        mp_id = mp.json()["id"]

        # 2) music_preset_id 포함 RenderPreset 생성
        body = {"name": "With Music", "bgm_mode": "manual", "music_preset_id": mp_id}
        pid = client.post("/render-presets", json=body).json()["id"]

        resp = client.get(f"/render-presets/{pid}")
        assert resp.status_code == 200
        assert resp.json()["music_preset_id"] == mp_id
        assert resp.json()["bgm_mode"] == "manual"

        # 3) music_preset_id 해제 (null로 업데이트)
        resp = client.put(f"/render-presets/{pid}", json={"music_preset_id": None})
        assert resp.status_code == 200
        assert resp.json()["music_preset_id"] is None

    def test_music_preset_id_null_by_default(self, client):
        """music_preset_id 미지정 시 null."""
        pid = client.post("/render-presets", json={"name": "No Music"}).json()["id"]
        resp = client.get(f"/render-presets/{pid}")
        assert resp.json()["music_preset_id"] is None
