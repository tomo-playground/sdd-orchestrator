"""Tests for storyboard management API endpoints."""

import uuid

from fastapi.testclient import TestClient


def test_create_storyboard(client: TestClient):
    """Test creating a storyboard."""
    title = f"Story {uuid.uuid4().hex[:4]}"
    response = client.post(
        "/storyboards",
        json={
            "title": title,
            "description": "test description",
            "scenes": [],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "storyboard_id" in data


def test_list_storyboards(client: TestClient):
    """Test listing storyboards."""
    response = client.get("/storyboards")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
