"""Tests for loras router endpoints."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from models import LoRA


class TestLoRAsRouter:
    """Test LoRA CRUD operations."""

    def test_list_loras_empty(self, client: TestClient, db_session):
        """List LoRAs when database is empty."""
        response = client.get("/api/v1/loras")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_create_lora_minimal(self, client: TestClient, db_session):
        """Create LoRA with minimal required fields."""
        request_data = {"name": "test_lora", "display_name": "Test LoRA"}

        response = client.post("/api/admin/loras", json=request_data)
        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "test_lora"
        assert data["display_name"] == "Test LoRA"
        assert "id" in data

    def test_create_lora_duplicate_name(self, client: TestClient, db_session):
        """Creating LoRA with duplicate name fails."""
        request_data = {"name": "duplicate_lora", "display_name": "Duplicate LoRA"}

        # Create first
        response = client.post("/api/admin/loras", json=request_data)
        assert response.status_code == 201

        # Try duplicate
        response = client.post("/api/admin/loras", json=request_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_create_lora_with_trigger_words(self, client: TestClient, db_session):
        """Create LoRA with trigger words."""
        request_data = {
            "name": "trigger_lora",
            "display_name": "Trigger LoRA",
            "trigger_words": ["word1", "word2"],
            "default_weight": 0.8,
        }

        response = client.post("/api/admin/loras", json=request_data)
        assert response.status_code == 201
        data = response.json()

        assert data["trigger_words"] == ["word1", "word2"]
        assert data["default_weight"] == 0.8

    def test_get_lora_not_found(self, client: TestClient):
        """Get non-existent LoRA returns 404."""
        response = client.get("/api/v1/loras/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_lora_success(self, client: TestClient, db_session):
        """Get existing LoRA."""
        lora = LoRA(name="get_test_lora", display_name="Get Test LoRA")
        db_session.add(lora)
        db_session.commit()

        response = client.get(f"/api/v1/loras/{lora.id}")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == lora.id
        assert data["name"] == "get_test_lora"
        assert data["display_name"] == "Get Test LoRA"

    def test_update_lora_success(self, client: TestClient, db_session):
        """Update existing LoRA."""
        lora = LoRA(name="update_test_lora", display_name="Original Name")
        db_session.add(lora)
        db_session.commit()
        lora_id = lora.id

        update_data = {"display_name": "Updated Name", "default_weight": 0.9}

        response = client.put(f"/api/admin/loras/{lora_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()

        assert data["display_name"] == "Updated Name"
        assert data["default_weight"] == 0.9

    def test_update_lora_not_found(self, client: TestClient):
        """Update non-existent LoRA returns 404."""
        update_data = {"display_name": "Updated"}

        response = client.put("/api/admin/loras/99999", json=update_data)
        assert response.status_code == 404

    def test_delete_lora_success(self, client: TestClient, db_session):
        """Delete existing LoRA."""
        lora = LoRA(name="delete_test_lora", display_name="Delete Test LoRA")
        db_session.add(lora)
        db_session.commit()
        lora_id = lora.id

        response = client.delete(f"/api/admin/loras/{lora_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["deleted"] == "delete_test_lora"

        # Verify deleted
        deleted = db_session.query(LoRA).filter(LoRA.id == lora_id).first()
        assert deleted is None

    def test_delete_lora_not_found(self, client: TestClient):
        """Delete non-existent LoRA returns 404."""
        response = client.delete("/api/admin/loras/99999")
        assert response.status_code == 404

    def test_list_loras_with_data(self, client: TestClient, db_session):
        """List LoRAs returns all LoRAs."""
        lora1 = LoRA(name="lora1", display_name="LoRA 1")
        lora2 = LoRA(name="lora2", display_name="LoRA 2")
        db_session.add_all([lora1, lora2])
        db_session.commit()

        response = client.get("/api/v1/loras")
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        names = [item["name"] for item in data]
        assert "lora1" in names
        assert "lora2" in names

    def test_search_civitai_requires_query(self, client: TestClient):
        """Search Civitai requires query parameter."""
        response = client.get("/api/admin/loras/search-civitai")
        assert response.status_code == 422  # Validation error

    def test_import_civitai_duplicate(self, client: TestClient, db_session):
        """Importing duplicate Civitai LoRA fails."""
        # Create existing LoRA with civitai_id
        lora = LoRA(name="existing_lora", display_name="Existing LoRA", civitai_id=12345)
        db_session.add(lora)
        db_session.commit()

        # Try to import same civitai_id
        with patch("httpx.AsyncClient.get"):
            response = client.post("/api/admin/loras/import-civitai/12345")
            assert response.status_code == 400
            assert "already imported" in response.json()["detail"].lower()

    def test_update_lora_trigger_words(self, client: TestClient, db_session):
        """Update LoRA trigger words."""
        lora = LoRA(name="trigger_update_lora", display_name="Trigger Update LoRA", trigger_words=["old_word"])
        db_session.add(lora)
        db_session.commit()
        lora_id = lora.id

        update_data = {"trigger_words": ["new_word1", "new_word2"]}

        response = client.put(f"/api/admin/loras/{lora_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()

        assert data["trigger_words"] == ["new_word1", "new_word2"]

    def test_create_lora_with_weight_range(self, client: TestClient, db_session):
        """Create LoRA with weight range."""
        request_data = {
            "name": "weight_range_lora",
            "display_name": "Weight Range LoRA",
            "default_weight": 0.7,
            "weight_min": 0.5,
            "weight_max": 1.5,
        }

        response = client.post("/api/admin/loras", json=request_data)
        assert response.status_code == 201
        data = response.json()

        assert data["default_weight"] == 0.7
        assert data["weight_min"] == 0.5
        assert data["weight_max"] == 1.5

    def test_create_lora_with_lora_type(self, client: TestClient, db_session):
        """Create LoRA with lora_type."""
        request_data = {"name": "typed_lora", "display_name": "Typed LoRA", "lora_type": "character"}

        response = client.post("/api/admin/loras", json=request_data)
        assert response.status_code == 201
        data = response.json()

        assert data["lora_type"] == "character"
