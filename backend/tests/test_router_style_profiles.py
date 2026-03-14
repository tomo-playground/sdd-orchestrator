"""Tests for style_profiles router endpoints."""

from fastapi.testclient import TestClient

from models import StyleProfile


class TestStyleProfilesRouter:
    """Test style profile CRUD operations."""

    def test_list_style_profiles_empty(self, client: TestClient, db_session):
        """List style profiles when database is empty."""
        response = client.get("/api/v1/style-profiles")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_create_style_profile_minimal(self, client: TestClient, db_session):
        """Create style profile with minimal required fields."""
        request_data = {"name": "test_profile", "display_name": "Test Profile"}

        response = client.post("/api/admin/style-profiles", json=request_data)
        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "test_profile"
        assert data["display_name"] == "Test Profile"
        assert "id" in data

    def test_create_style_profile_duplicate_name(self, client: TestClient, db_session):
        """Creating style profile with duplicate name fails."""
        request_data = {"name": "duplicate_profile", "display_name": "Duplicate Profile"}

        # Create first
        response = client.post("/api/admin/style-profiles", json=request_data)
        assert response.status_code == 201

        # Try duplicate
        response = client.post("/api/admin/style-profiles", json=request_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_create_style_profile_as_default(self, client: TestClient, db_session):
        """Creating profile as default unsets other defaults."""
        # Create first default
        profile1 = StyleProfile(name="profile1", display_name="Profile 1", is_default=True)
        db_session.add(profile1)
        db_session.commit()

        # Create new default via API
        request_data = {"name": "profile2", "display_name": "Profile 2", "is_default": True}

        response = client.post("/api/admin/style-profiles", json=request_data)
        assert response.status_code == 201

        # Verify first is no longer default
        db_session.refresh(profile1)
        assert profile1.is_default is False

    def test_get_style_profile_not_found(self, client: TestClient):
        """Get non-existent style profile returns 404."""
        response = client.get("/api/v1/style-profiles/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_style_profile_success(self, client: TestClient, db_session):
        """Get existing style profile."""
        profile = StyleProfile(name="get_test", display_name="Get Test")
        db_session.add(profile)
        db_session.commit()

        response = client.get(f"/api/v1/style-profiles/{profile.id}")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == profile.id
        assert data["name"] == "get_test"
        assert data["display_name"] == "Get Test"

    def test_get_default_profile_success(self, client: TestClient, db_session):
        """Get default style profile."""
        profile = StyleProfile(name="default_profile", display_name="Default Profile", is_default=True)
        db_session.add(profile)
        db_session.commit()

        response = client.get("/api/v1/style-profiles/default")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == profile.id
        assert data["is_default"] is True

    def test_get_default_profile_not_found(self, client: TestClient, db_session):
        """Get default profile when none exists returns 404."""
        response = client.get("/api/v1/style-profiles/default")
        assert response.status_code == 404
        assert "no default" in response.json()["detail"].lower()

    def test_get_style_profile_full(self, client: TestClient, db_session):
        """Get style profile with full details."""
        profile = StyleProfile(
            name="full_test",
            display_name="Full Test",
            default_positive="positive tags",
            default_negative="negative tags",
        )
        db_session.add(profile)
        db_session.commit()

        response = client.get(f"/api/v1/style-profiles/{profile.id}/full")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == profile.id
        assert data["default_positive"] == "positive tags"
        assert data["default_negative"] == "negative tags"
        assert "sd_model" in data
        assert "loras" in data
        assert "negative_embeddings" in data
        assert "positive_embeddings" in data

    def test_update_style_profile_success(self, client: TestClient, db_session):
        """Update existing style profile."""
        profile = StyleProfile(name="update_test", display_name="Original Name")
        db_session.add(profile)
        db_session.commit()
        profile_id = profile.id

        update_data = {"display_name": "Updated Name", "description": "Updated description"}

        response = client.put(f"/api/admin/style-profiles/{profile_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()

        assert data["display_name"] == "Updated Name"
        assert data["description"] == "Updated description"

    def test_update_style_profile_not_found(self, client: TestClient):
        """Update non-existent style profile returns 404."""
        update_data = {"display_name": "Updated"}

        response = client.put("/api/admin/style-profiles/99999", json=update_data)
        assert response.status_code == 404

    def test_update_style_profile_set_default(self, client: TestClient, db_session):
        """Setting profile as default unsets others."""
        # Create two profiles
        profile1 = StyleProfile(name="profile1", display_name="Profile 1", is_default=True)
        profile2 = StyleProfile(name="profile2", display_name="Profile 2", is_default=False)
        db_session.add_all([profile1, profile2])
        db_session.commit()

        # Set profile2 as default
        update_data = {"is_default": True}

        response = client.put(f"/api/admin/style-profiles/{profile2.id}", json=update_data)
        assert response.status_code == 200

        # Verify profile1 is no longer default
        db_session.refresh(profile1)
        assert profile1.is_default is False

    def test_delete_style_profile_success(self, client: TestClient, db_session):
        """Delete existing style profile."""
        profile = StyleProfile(name="delete_test", display_name="Delete Test")
        db_session.add(profile)
        db_session.commit()
        profile_id = profile.id

        response = client.delete(f"/api/admin/style-profiles/{profile_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["deleted"] == "delete_test"

        # Verify deleted
        deleted = db_session.query(StyleProfile).filter(StyleProfile.id == profile_id).first()
        assert deleted is None

    def test_delete_style_profile_not_found(self, client: TestClient):
        """Delete non-existent style profile returns 404."""
        response = client.delete("/api/admin/style-profiles/99999")
        assert response.status_code == 404

    def test_list_style_profiles_with_data(self, client: TestClient, db_session):
        """List style profiles returns all active profiles."""
        profile1 = StyleProfile(name="profile1", display_name="Profile 1", is_active=True)
        profile2 = StyleProfile(name="profile2", display_name="Profile 2", is_active=False)
        db_session.add_all([profile1, profile2])
        db_session.commit()

        # Default: active_only=True
        response = client.get("/api/v1/style-profiles")
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["name"] == "profile1"

    def test_list_style_profiles_include_inactive(self, client: TestClient, db_session):
        """List style profiles with active_only=False."""
        profile1 = StyleProfile(name="profile1", display_name="Profile 1", is_active=True)
        profile2 = StyleProfile(name="profile2", display_name="Profile 2", is_active=False)
        db_session.add_all([profile1, profile2])
        db_session.commit()

        response = client.get("/api/v1/style-profiles?active_only=false")
        assert response.status_code == 200
        data = response.json()

        names = [item["name"] for item in data]
        assert "profile1" in names
        assert "profile2" in names

    def test_create_style_profile_with_loras(self, client: TestClient, db_session):
        """Create style profile with LoRA configuration."""
        request_data = {
            "name": "lora_profile",
            "display_name": "LoRA Profile",
            "loras": [{"lora_id": 1, "weight": 0.8}],
        }

        response = client.post("/api/admin/style-profiles", json=request_data)
        assert response.status_code == 201
        data = response.json()

        assert "loras" in data
        # LoRAs stored as JSONB
        assert isinstance(data["loras"], list)


class TestStyleProfileFullResponse:
    """Phase 1.5-A: /full 응답에 생성 파라미터 필드 포함 확인."""

    def test_full_includes_generation_params(self, client: TestClient, db_session):
        """Realistic profile: default_enable_hr=True 등 파라미터 포함."""
        profile = StyleProfile(
            name="realistic_full",
            display_name="Realistic Full",
            default_steps=6,
            default_cfg_scale=1.5,
            default_sampler_name="DPM++ SDE Karras",
            default_clip_skip=1,
            default_enable_hr=True,
        )
        db_session.add(profile)
        db_session.commit()

        response = client.get(f"/api/v1/style-profiles/{profile.id}/full")
        assert response.status_code == 200
        data = response.json()

        assert data["default_steps"] == 6
        assert data["default_cfg_scale"] == 1.5
        assert data["default_sampler_name"] == "DPM++ SDE Karras"
        assert data["default_clip_skip"] == 1
        assert data["default_enable_hr"] is True

    def test_full_anime_profile_hr_false(self, client: TestClient, db_session):
        """Anime profile: default_enable_hr=False."""
        profile = StyleProfile(
            name="anime_full",
            display_name="Anime Full",
            default_steps=28,
            default_cfg_scale=7.0,
            default_sampler_name="DPM++ 2M Karras",
            default_clip_skip=2,
            default_enable_hr=False,
        )
        db_session.add(profile)
        db_session.commit()

        response = client.get(f"/api/v1/style-profiles/{profile.id}/full")
        assert response.status_code == 200
        data = response.json()

        assert data["default_enable_hr"] is False
        assert data["default_steps"] == 28

    def test_full_null_params_when_unset(self, client: TestClient, db_session):
        """생성 파라미터 미설정 시 null 반환."""
        profile = StyleProfile(
            name="minimal_full",
            display_name="Minimal",
        )
        db_session.add(profile)
        db_session.commit()

        response = client.get(f"/api/v1/style-profiles/{profile.id}/full")
        assert response.status_code == 200
        data = response.json()

        assert data["default_steps"] is None
        assert data["default_cfg_scale"] is None
        assert data["default_sampler_name"] is None
        assert data["default_clip_skip"] is None
        assert data["default_enable_hr"] is None

    def test_full_includes_ip_adapter_model(self, client: TestClient, db_session):
        """default_ip_adapter_model 필드 포함 확인."""
        profile = StyleProfile(
            name="ip_adapter_full",
            display_name="IP Adapter Full",
            default_ip_adapter_model="ip-adapter-plus-face_sdxl_vit-h",
        )
        db_session.add(profile)
        db_session.commit()

        response = client.get(f"/api/v1/style-profiles/{profile.id}/full")
        assert response.status_code == 200
        data = response.json()

        assert data["default_ip_adapter_model"] == "ip-adapter-plus-face_sdxl_vit-h"
