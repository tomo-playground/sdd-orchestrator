"""Tests for generation logs API endpoints."""

import uuid

from fastapi.testclient import TestClient


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
            "scene_id": 0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == project_name
    assert data["scene_id"] == 0
    assert data["status"] == "pending"
    assert "id" in data


def test_create_generation_log_full(client: TestClient):
    """Test creating a generation log with full data."""
    project_name = _unique_project()
    response = client.post(
        "/generation-logs",
        json={
            "project_name": project_name,
            "scene_id": 1,
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
    assert data["scene_id"] == 1
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
                "scene_id": i,
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
                "scene_id": i,
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
                "scene_id": i,
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
            "scene_id": 0,
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
            "scene_id": 0,
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
        "scene_id": 5,
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
    assert log["scene_id"] == test_data["scene_id"]
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
            json={"project_name": project_a, "scene_id": i},
        )

    # Create logs for project B
    for i in range(2):
        client.post(
            "/generation-logs",
            json={"project_name": project_b, "scene_id": i},
        )

    # Verify project A
    response_a = client.get(f"/generation-logs/project/{project_a}")
    assert response_a.json()["total"] == 3

    # Verify project B
    response_b = client.get(f"/generation-logs/project/{project_b}")
    assert response_b.json()["total"] == 2


def test_success_combinations_empty_project(client: TestClient):
    """Test success combinations with no data."""
    project_name = _unique_project()
    response = client.get(
        f"/generation-logs/success-combinations?project_name={project_name}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_success"] == 0
    assert data["summary"]["analyzed_tags"] == 0
    assert len(data["combinations_by_category"]) == 0
    assert len(data["suggested_combinations"]) == 0


def test_success_combinations_with_success_logs(client: TestClient):
    """Test success combinations generation with real data."""
    project_name = _unique_project()

    # Create success logs with tags
    success_logs = [
        {
            "project_name": project_name,
            "scene_id": 0,
            "tags": ["smile", "standing", "cowboy shot", "classroom"],
            "match_rate": 0.85,
            "status": "success",
        },
        {
            "project_name": project_name,
            "scene_id": 1,
            "tags": ["smile", "standing", "cowboy shot", "outdoors"],
            "match_rate": 0.90,
            "status": "success",
        },
        {
            "project_name": project_name,
            "scene_id": 2,
            "tags": ["smile", "sitting", "close-up", "classroom"],
            "match_rate": 0.80,
            "status": "success",
        },
    ]

    for log_data in success_logs:
        client.post("/generation-logs", json=log_data)

    # Test success combinations
    response = client.get(
        f"/generation-logs/success-combinations?project_name={project_name}&min_occurrences=2"
    )

    assert response.status_code == 200
    data = response.json()

    # Check summary
    assert data["summary"]["total_success"] == 3
    assert data["summary"]["analyzed_tags"] > 0

    # Check combinations by category
    assert "combinations_by_category" in data
    categories = data["combinations_by_category"]

    # Should have at least some categories
    assert len(categories) > 0

    # Check that each category has tags with expected structure
    for category, tags in categories.items():
        assert isinstance(tags, list)
        if len(tags) > 0:
            tag_data = tags[0]
            assert "tag" in tag_data
            assert "success_rate" in tag_data
            assert "occurrences" in tag_data
            assert "avg_match_rate" in tag_data


def test_success_combinations_filtering(client: TestClient):
    """Test success combinations with different match rate thresholds."""
    project_name = _unique_project()

    # Create logs with different match rates
    logs = [
        {
            "project_name": project_name,
            "scene_id": 0,
            "tags": ["smile"],
            "match_rate": 0.95,
            "status": "success",
        },
        {
            "project_name": project_name,
            "scene_id": 1,
            "tags": ["frown"],
            "match_rate": 0.60,
            "status": "fail",
        },
        {
            "project_name": project_name,
            "scene_id": 2,
            "tags": ["neutral"],
            "match_rate": 0.75,
            "status": "success",
        },
    ]

    for log_data in logs:
        client.post("/generation-logs", json=log_data)

    # Test with default threshold (0.7)
    response = client.get(
        f"/generation-logs/success-combinations?project_name={project_name}&min_occurrences=1"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_success"] >= 2  # smile (0.95) and neutral (0.75)

    # Test with higher threshold (0.8)
    response = client.get(
        f"/generation-logs/success-combinations?project_name={project_name}&match_rate_threshold=0.8&min_occurrences=1"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_success"] >= 1  # only smile (0.95)


def test_analyze_patterns_basic(client: TestClient):
    """Test basic pattern analysis."""
    project_name = _unique_project()

    # Create mix of success and fail logs
    logs = [
        {"project_name": project_name, "scene_id": 0, "tags": ["smile", "standing"], "status": "success"},
        {"project_name": project_name, "scene_id": 1, "tags": ["smile", "sitting"], "status": "success"},
        {"project_name": project_name, "scene_id": 2, "tags": ["frown", "standing"], "status": "fail"},
    ]

    for log_data in logs:
        client.post("/generation-logs", json=log_data)

    response = client.get(
        f"/generation-logs/analyze/patterns?project_name={project_name}&min_occurrences=1"
    )

    assert response.status_code == 200
    data = response.json()

    # Check summary
    assert "summary" in data
    assert data["summary"]["total_logs"] == 3
    assert data["summary"]["success_count"] >= 2
    assert data["summary"]["fail_count"] >= 1

    # Check tag stats
    assert "tag_stats" in data
    assert len(data["tag_stats"]) > 0


def test_suggest_conflict_rules_no_data(client: TestClient):
    """Test conflict rules suggestion with no data."""
    project_name = _unique_project()
    response = client.get(
        f"/generation-logs/suggest-conflict-rules?project_name={project_name}"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["suggested_rules"] == []
    assert data["new_rules_count"] == 0
