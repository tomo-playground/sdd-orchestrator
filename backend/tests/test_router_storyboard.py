"""Tests for storyboard router endpoints."""

import pytest
from fastapi.testclient import TestClient

from models import Storyboard


class TestStoryboardRouter:
    """Test storyboard CRUD operations."""

    def test_list_storyboards_empty(self, client: TestClient, db_session):
        """List storyboards when database is empty."""
        response = client.get("/storyboards")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_create_storyboard_minimal(self, client: TestClient, db_session):
        """Create storyboard with minimal required fields."""
        request_data = {
            "title": "Test Storyboard",
            "description": "Test description",
            "scenes": []
        }

        response = client.post("/storyboards", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "storyboard_id" in data
        assert "scene_ids" in data
        assert isinstance(data["scene_ids"], list)

        # Verify in DB
        storyboard = db_session.query(Storyboard).filter(
            Storyboard.id == data["storyboard_id"]
        ).first()
        assert storyboard is not None
        assert storyboard.title == "Test Storyboard"
        assert storyboard.description == "Test description"

    def test_create_storyboard_with_scenes(self, client: TestClient, db_session):
        """Create storyboard with scenes."""
        request_data = {
            "title": "Storyboard with Scenes",
            "description": "Test",
            "scenes": [
                {
                    "scene_id": 0,
                    "script": "Scene 1 script",
                    "speaker": "Narrator",
                    "duration": 3.0,
                    "description": "First scene",
                    "image_prompt": "test prompt",
                    "image_prompt_ko": "테스트 프롬프트",
                    "negative_prompt": "bad quality",
                    "width": 512,
                    "height": 768,
                    "steps": 20,
                    "cfg_scale": 7.0,
                    "sampler_name": "DPM++ 2M Karras",
                    "seed": -1,
                    "clip_skip": 2,
                    "context_tags": {},
                    "tags": [],
                    "character_actions": [],
                    "use_reference_only": True,
                    "reference_only_weight": 0.5,
                    "candidates": None
                }
            ]
        }

        response = client.post("/storyboards", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert len(data["scene_ids"]) == 1

    def test_get_storyboard_not_found(self, client: TestClient):
        """Get non-existent storyboard returns 404."""
        response = client.get("/storyboards/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_storyboard_success(self, client: TestClient, db_session):
        """Get existing storyboard."""
        # Create test storyboard
        storyboard = Storyboard(
            title="Get Test",
            description="Test description"
        )
        db_session.add(storyboard)
        db_session.commit()

        response = client.get(f"/storyboards/{storyboard.id}")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == storyboard.id
        assert data["title"] == "Get Test"
        assert data["description"] == "Test description"
        assert "scenes" in data
        assert isinstance(data["scenes"], list)

    def test_update_storyboard_success(self, client: TestClient, db_session):
        """Update existing storyboard."""
        # Create test storyboard
        storyboard = Storyboard(
            title="Original Title",
            description="Original description"
        )
        db_session.add(storyboard)
        db_session.commit()
        storyboard_id = storyboard.id

        # Update
        update_data = {
            "title": "Updated Title",
            "description": "Updated description",
            "scenes": []
        }

        response = client.put(f"/storyboards/{storyboard_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["storyboard_id"] == storyboard_id

        # Verify in DB
        db_session.refresh(storyboard)
        assert storyboard.title == "Updated Title"
        assert storyboard.description == "Updated description"

    def test_update_storyboard_not_found(self, client: TestClient):
        """Update non-existent storyboard returns 404."""
        update_data = {
            "title": "Updated",
            "description": "Test",
            "scenes": []
        }

        response = client.put("/storyboards/99999", json=update_data)
        assert response.status_code == 404

    def test_delete_storyboard_success(self, client: TestClient, db_session):
        """Delete existing storyboard."""
        # Create test storyboard
        storyboard = Storyboard(
            title="To Delete",
            description="Test"
        )
        db_session.add(storyboard)
        db_session.commit()
        storyboard_id = storyboard.id

        response = client.delete(f"/storyboards/{storyboard_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Verify deleted
        deleted = db_session.query(Storyboard).filter(
            Storyboard.id == storyboard_id
        ).first()
        assert deleted is None

    def test_delete_storyboard_not_found(self, client: TestClient):
        """Delete non-existent storyboard returns 404."""
        response = client.delete("/storyboards/99999")
        assert response.status_code == 404

    def test_list_storyboards_with_data(self, client: TestClient, db_session):
        """List storyboards shows correct counts."""
        # Create test storyboards
        sb1 = Storyboard(title="Storyboard 1", description="Test 1")
        sb2 = Storyboard(title="Storyboard 2", description="Test 2")
        db_session.add_all([sb1, sb2])
        db_session.commit()

        response = client.get("/storyboards")
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        titles = [item["title"] for item in data]
        assert "Storyboard 1" in titles
        assert "Storyboard 2" in titles

        # Check structure
        for item in data:
            assert "id" in item
            assert "title" in item
            assert "description" in item
            assert "scene_count" in item
            assert "image_count" in item
            assert "created_at" in item
            assert "updated_at" in item

    def test_title_truncation(self, client: TestClient, db_session):
        """Very long titles are truncated."""
        long_title = "A" * 250  # Exceeds 190 char limit
        request_data = {
            "title": long_title,
            "description": "Test",
            "scenes": []
        }

        response = client.post("/storyboards", json=request_data)
        assert response.status_code == 200
        data = response.json()

        # Verify title was truncated
        storyboard = db_session.query(Storyboard).filter(
            Storyboard.id == data["storyboard_id"]
        ).first()
        assert len(storyboard.title) <= 193  # 190 + "..."
        assert storyboard.title.endswith("...")
