"""Tests for generation logs API endpoints."""

from fastapi.testclient import TestClient
import pytest
import uuid


def _unique_project() -> str:
    """Generate a unique project name for test isolation."""
    return f"test_{uuid.uuid4().hex[:8]}"


def test_create_generation_log_minimal(client: TestClient):
    """Test creating a generation log with minimal data."""
    project_name = _unique_project()
    response = client.post(
        "/generation-logs",
        json={
            "project_name": project_name,
            "scene_index": 0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == project_name
    assert data["scene_index"] == 0
    assert data["status"] == "pending"
    assert "id" in data


def test_create_generation_log_full(client: TestClient):
    """Test creating a generation log with full data."""
    project_name = _unique_project()
    response = client.post(
        "/generation-logs",
        json={
            "project_name": project_name,
            "scene_index": 1,
            "prompt": "1girl, smiling, classroom, sitting",
            "tags": ["1girl", "smiling", "classroom", "sitting"],
            "sd_params": {"steps": 20, "cfg_scale": 7, "seed": 12345},
            "match_rate": 0.85,
            "seed": 12345,
            "status": "success",
            "image_url": "/outputs/images/scene_1.png",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == project_name
    assert data["scene_index"] == 1
    assert data["status"] == "success"
    assert data["match_rate"] == 0.85
    assert "id" in data


def test_get_project_logs_empty(client: TestClient):
    """Test getting logs for a project with no logs."""
    project_name = _unique_project()
    response = client.get(f"/generation-logs/project/{project_name}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["logs"] == []


def test_get_project_logs_with_data(client: TestClient):
    """Test getting logs for a project after creating some."""
    project_name = _unique_project()
    # Create logs
    for i in range(3):
        client.post(
            "/generation-logs",
            json={
                "project_name": project_name,
                "scene_index": i,
                "status": "success" if i % 2 == 0 else "fail",
            },
        )

    # Get all logs
    response = client.get(f"/generation-logs/project/{project_name}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["logs"]) == 3


def test_get_project_logs_filter_by_status(client: TestClient):
    """Test filtering logs by status."""
    project_name = _unique_project()
    # Create logs with different statuses
    for i in range(4):
        client.post(
            "/generation-logs",
            json={
                "project_name": project_name,
                "scene_index": i,
                "status": "success" if i < 2 else "fail",
            },
        )

    # Filter success only
    response = client.get(f"/generation-logs/project/{project_name}?status=success")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(log["status"] == "success" for log in data["logs"])

    # Filter fail only
    response = client.get(f"/generation-logs/project/{project_name}?status=fail")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(log["status"] == "fail" for log in data["logs"])


def test_get_project_logs_with_limit(client: TestClient):
    """Test limiting the number of returned logs."""
    project_name = _unique_project()
    # Create 10 logs
    for i in range(10):
        client.post(
            "/generation-logs",
            json={
                "project_name": project_name,
                "scene_index": i,
            },
        )

    # Get with limit=5
    response = client.get(f"/generation-logs/project/{project_name}?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["logs"]) == 5


def test_update_log_status(client: TestClient):
    """Test updating a log's status."""
    project_name = _unique_project()
    # Create log
    create_response = client.post(
        "/generation-logs",
        json={
            "project_name": project_name,
            "scene_index": 0,
            "status": "pending",
        },
    )
    log_id = create_response.json()["id"]

    # Update status to success
    response = client.patch(
        f"/generation-logs/{log_id}/status",
        json={"status": "success"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == log_id
    assert data["status"] == "success"

    # Update status to fail
    response = client.patch(
        f"/generation-logs/{log_id}/status",
        json={"status": "fail"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "fail"


def test_update_nonexistent_log_status(client: TestClient):
    """Test updating status of non-existent log."""
    response = client.patch(
        "/generation-logs/99999/status",
        json={"status": "success"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_delete_log(client: TestClient):
    """Test deleting a log."""
    project_name = _unique_project()
    # Create log
    create_response = client.post(
        "/generation-logs",
        json={
            "project_name": project_name,
            "scene_index": 0,
        },
    )
    log_id = create_response.json()["id"]

    # Delete log
    response = client.delete(f"/generation-logs/{log_id}")
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Verify deletion
    get_response = client.get(f"/generation-logs/project/{project_name}")
    assert get_response.json()["total"] == 0


def test_delete_nonexistent_log(client: TestClient):
    """Test deleting non-existent log."""
    response = client.delete("/generation-logs/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_log_data_integrity(client: TestClient):
    """Test that log data is stored and retrieved correctly."""
    project_name = _unique_project()
    # Create log with full data
    test_data = {
        "project_name": project_name,
        "scene_index": 5,
        "prompt": "complex prompt with multiple tags",
        "tags": ["tag1", "tag2", "tag3", "tag4"],
        "sd_params": {
            "steps": 25,
            "cfg_scale": 7.5,
            "seed": 999999,
            "sampler": "DPM++ 2M Karras",
        },
        "match_rate": 0.923,
        "seed": 999999,
        "status": "success",
        "image_url": "/outputs/images/test_scene_5.png",
    }

    create_response = client.post("/generation-logs", json=test_data)
    assert create_response.status_code == 200
    log_id = create_response.json()["id"]

    # Retrieve and verify
    get_response = client.get(f"/generation-logs/project/{project_name}")
    assert get_response.status_code == 200
    logs = get_response.json()["logs"]
    assert len(logs) == 1

    log = logs[0]
    assert log["project_name"] == test_data["project_name"]
    assert log["scene_index"] == test_data["scene_index"]
    assert log["prompt"] == test_data["prompt"]
    assert log["tags"] == test_data["tags"]
    assert log["sd_params"] == test_data["sd_params"]
    assert log["match_rate"] == test_data["match_rate"]
    assert log["seed"] == test_data["seed"]
    assert log["status"] == test_data["status"]
    assert log["image_url"] == test_data["image_url"]


def test_multiple_projects_isolation(client: TestClient):
    """Test that logs from different projects are isolated."""
    project_a = _unique_project()
    project_b = _unique_project()

    # Create logs for project A
    for i in range(3):
        client.post(
            "/generation-logs",
            json={"project_name": project_a, "scene_index": i},
        )

    # Create logs for project B
    for i in range(2):
        client.post(
            "/generation-logs",
            json={"project_name": project_b, "scene_index": i},
        )

    # Verify project A
    response_a = client.get(f"/generation-logs/project/{project_a}")
    assert response_a.json()["total"] == 3

    # Verify project B
    response_b = client.get(f"/generation-logs/project/{project_b}")
    assert response_b.json()["total"] == 2
