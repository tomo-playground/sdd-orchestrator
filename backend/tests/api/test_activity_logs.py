"""Tests for activity logs API endpoints."""

from conftest import create_test_storyboard
from fastapi.testclient import TestClient


def _create_storyboard_with_scenes(client: TestClient, scene_count: int = 3) -> dict:
    """Create a test storyboard with scenes and return IDs."""
    scenes = [{"scene_id": i, "script": f"Scene {i}"} for i in range(scene_count)]
    data = create_test_storyboard(client, scenes=scenes)
    sb_id = data["storyboard_id"]
    # Fetch the storyboard to get scene IDs
    resp = client.get(f"/storyboards/{sb_id}")
    scene_ids = [s["id"] for s in resp.json()["scenes"]]
    return {"storyboard_id": sb_id, "scene_ids": scene_ids}


def test_create_activity_log_minimal(client: TestClient):
    """Test creating a activity log with minimal data."""
    ctx = _create_storyboard_with_scenes(client, 1)
    response = client.post(
        "/activity-logs",
        json={
            "storyboard_id": ctx["storyboard_id"],
            "scene_id": ctx["scene_ids"][0],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["storyboard_id"] == ctx["storyboard_id"]
    assert data["scene_id"] == ctx["scene_ids"][0]
    assert data["status"] == "pending"
    assert "id" in data


def test_create_activity_log_full(client: TestClient):
    """Test creating a activity log with full data."""
    ctx = _create_storyboard_with_scenes(client, 2)
    response = client.post(
        "/activity-logs",
        json={
            "storyboard_id": ctx["storyboard_id"],
            "scene_id": ctx["scene_ids"][1],
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
    assert data["storyboard_id"] == ctx["storyboard_id"]
    assert data["scene_id"] == ctx["scene_ids"][1]
    assert data["status"] == "success"
    assert data["match_rate"] == 0.85
    assert "id" in data


def test_get_storyboard_logs_empty(client: TestClient):
    """Test getting logs for a storyboard with no logs."""
    ctx = _create_storyboard_with_scenes(client, 1)
    response = client.get(f"/activity-logs/storyboard/{ctx['storyboard_id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["logs"] == []


def test_get_storyboard_logs_with_data(client: TestClient):
    """Test getting logs for a storyboard after creating some."""
    ctx = _create_storyboard_with_scenes(client, 3)
    for scene_id in ctx["scene_ids"]:
        client.post(
            "/activity-logs",
            json={
                "storyboard_id": ctx["storyboard_id"],
                "scene_id": scene_id,
                "status": "success" if scene_id % 2 == 0 else "fail",
            },
        )

    response = client.get(f"/activity-logs/storyboard/{ctx['storyboard_id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["logs"]) == 3


def test_get_storyboard_logs_filter_by_status(client: TestClient):
    """Test filtering logs by status."""
    ctx = _create_storyboard_with_scenes(client, 4)
    for i, scene_id in enumerate(ctx["scene_ids"]):
        client.post(
            "/activity-logs",
            json={
                "storyboard_id": ctx["storyboard_id"],
                "scene_id": scene_id,
                "status": "success" if i < 2 else "fail",
            },
        )

    # Filter success only
    response = client.get(f"/activity-logs/storyboard/{ctx['storyboard_id']}?status=success")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(log["status"] == "success" for log in data["logs"])

    # Filter fail only
    response = client.get(f"/activity-logs/storyboard/{ctx['storyboard_id']}?status=fail")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(log["status"] == "fail" for log in data["logs"])


def test_get_storyboard_logs_with_limit(client: TestClient):
    """Test limiting the number of returned logs."""
    ctx = _create_storyboard_with_scenes(client, 10)
    for scene_id in ctx["scene_ids"]:
        client.post(
            "/activity-logs",
            json={
                "storyboard_id": ctx["storyboard_id"],
                "scene_id": scene_id,
            },
        )

    # Get with limit=5
    response = client.get(f"/activity-logs/storyboard/{ctx['storyboard_id']}?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["logs"]) == 5


def test_update_log_status(client: TestClient):
    """Test updating a log's status."""
    ctx = _create_storyboard_with_scenes(client, 1)
    create_response = client.post(
        "/activity-logs",
        json={
            "storyboard_id": ctx["storyboard_id"],
            "scene_id": ctx["scene_ids"][0],
            "status": "pending",
        },
    )
    log_id = create_response.json()["id"]

    # Update status to success
    response = client.patch(
        f"/activity-logs/{log_id}/status",
        json={"status": "success"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == log_id
    assert data["status"] == "success"

    # Update status to fail
    response = client.patch(
        f"/activity-logs/{log_id}/status",
        json={"status": "fail"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "fail"


def test_update_nonexistent_log_status(client: TestClient):
    """Test updating status of non-existent log."""
    response = client.patch(
        "/activity-logs/99999/status",
        json={"status": "success"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_delete_log(client: TestClient):
    """Test deleting a log."""
    ctx = _create_storyboard_with_scenes(client, 1)
    create_response = client.post(
        "/activity-logs",
        json={
            "storyboard_id": ctx["storyboard_id"],
            "scene_id": ctx["scene_ids"][0],
        },
    )
    log_id = create_response.json()["id"]

    # Delete log
    response = client.delete(f"/activity-logs/{log_id}")
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Verify deletion
    get_response = client.get(f"/activity-logs/storyboard/{ctx['storyboard_id']}")
    assert get_response.json()["total"] == 0


def test_delete_nonexistent_log(client: TestClient):
    """Test deleting non-existent log."""
    response = client.delete("/activity-logs/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_log_data_integrity(client: TestClient):
    """Test that log data is stored and retrieved correctly."""
    ctx = _create_storyboard_with_scenes(client, 6)
    scene_id = ctx["scene_ids"][4]  # Use 5th scene
    test_data = {
        "storyboard_id": ctx["storyboard_id"],
        "scene_id": scene_id,
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
        "image_url": "projects/1/scenes/test_scene_5.png",
    }

    create_response = client.post("/activity-logs", json=test_data)
    assert create_response.status_code == 200

    # Retrieve and verify
    get_response = client.get(f"/activity-logs/storyboard/{ctx['storyboard_id']}")
    assert get_response.status_code == 200
    logs = get_response.json()["logs"]
    assert len(logs) == 1

    log = logs[0]
    assert log["storyboard_id"] == ctx["storyboard_id"]
    assert log["scene_id"] == scene_id
    assert log["prompt"] == test_data["prompt"]
    assert log["tags"] == test_data["tags"]
    assert log["sd_params"] == test_data["sd_params"]
    assert log["match_rate"] == test_data["match_rate"]
    assert log["seed"] == test_data["seed"]
    assert log["status"] == test_data["status"]
    # image_url is derived from media_asset relationship;
    # no matching media_asset exists in the test DB, so it should be None
    assert log["image_url"] is None


def test_isolation(client: TestClient):
    """Test that logs from different storyboards are isolated."""
    ctx_a = _create_storyboard_with_scenes(client, 3)
    ctx_b = _create_storyboard_with_scenes(client, 2)

    # Create logs for storyboard A
    for scene_id in ctx_a["scene_ids"]:
        client.post(
            "/activity-logs",
            json={"storyboard_id": ctx_a["storyboard_id"], "scene_id": scene_id},
        )

    # Create logs for storyboard B
    for scene_id in ctx_b["scene_ids"]:
        client.post(
            "/activity-logs",
            json={"storyboard_id": ctx_b["storyboard_id"], "scene_id": scene_id},
        )

    # Verify storyboard A
    response_a = client.get(f"/activity-logs/storyboard/{ctx_a['storyboard_id']}")
    assert response_a.json()["total"] == 3

    # Verify storyboard B
    response_b = client.get(f"/activity-logs/storyboard/{ctx_b['storyboard_id']}")
    assert response_b.json()["total"] == 2


def test_success_combinations_empty(client: TestClient):
    """Test success combinations with no data."""
    ctx = _create_storyboard_with_scenes(client, 1)
    response = client.get(
        f"/activity-logs/success-combinations?storyboard_id={ctx['storyboard_id']}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_success"] == 0
    assert data["summary"]["analyzed_tags"] == 0
    assert len(data["combinations_by_category"]) == 0
    assert len(data["suggested_combinations"]) == 0


def test_success_combinations_with_success_logs(client: TestClient):
    """Test success combinations generation with real data."""
    ctx = _create_storyboard_with_scenes(client, 3)
    success_logs = [
        {
            "storyboard_id": ctx["storyboard_id"],
            "scene_id": ctx["scene_ids"][0],
            "tags": ["smile", "standing", "cowboy shot", "classroom"],
            "match_rate": 0.85,
            "status": "success",
        },
        {
            "storyboard_id": ctx["storyboard_id"],
            "scene_id": ctx["scene_ids"][1],
            "tags": ["smile", "standing", "cowboy shot", "outdoors"],
            "match_rate": 0.90,
            "status": "success",
        },
        {
            "storyboard_id": ctx["storyboard_id"],
            "scene_id": ctx["scene_ids"][2],
            "tags": ["smile", "sitting", "close-up", "classroom"],
            "match_rate": 0.80,
            "status": "success",
        },
    ]

    for log_data in success_logs:
        client.post("/activity-logs", json=log_data)

    response = client.get(
        f"/activity-logs/success-combinations?storyboard_id={ctx['storyboard_id']}&min_occurrences=2"
    )

    assert response.status_code == 200
    data = response.json()

    assert data["summary"]["total_success"] == 3
    assert data["summary"]["analyzed_tags"] > 0

    assert "combinations_by_category" in data
    categories = data["combinations_by_category"]

    assert len(categories) > 0

    for tags in categories.values():
        assert isinstance(tags, list)
        if len(tags) > 0:
            tag_data = tags[0]
            assert "tag" in tag_data
            assert "success_rate" in tag_data
            assert "occurrences" in tag_data
            assert "avg_match_rate" in tag_data


def test_success_combinations_filtering(client: TestClient):
    """Test success combinations with different match rate thresholds."""
    ctx = _create_storyboard_with_scenes(client, 3)
    logs = [
        {
            "storyboard_id": ctx["storyboard_id"],
            "scene_id": ctx["scene_ids"][0],
            "tags": ["smile"],
            "match_rate": 0.95,
            "status": "success",
        },
        {
            "storyboard_id": ctx["storyboard_id"],
            "scene_id": ctx["scene_ids"][1],
            "tags": ["frown"],
            "match_rate": 0.60,
            "status": "fail",
        },
        {
            "storyboard_id": ctx["storyboard_id"],
            "scene_id": ctx["scene_ids"][2],
            "tags": ["neutral"],
            "match_rate": 0.75,
            "status": "success",
        },
    ]

    for log_data in logs:
        client.post("/activity-logs", json=log_data)

    # Test with default threshold (0.7)
    response = client.get(
        f"/activity-logs/success-combinations?storyboard_id={ctx['storyboard_id']}&min_occurrences=1"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_success"] >= 2  # smile (0.95) and neutral (0.75)

    # Test with higher threshold (0.8)
    response = client.get(
        f"/activity-logs/success-combinations?storyboard_id={ctx['storyboard_id']}&match_rate_threshold=0.8&min_occurrences=1"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_success"] >= 1  # only smile (0.95)


def test_analyze_patterns_basic(client: TestClient):
    """Test basic pattern analysis."""
    ctx = _create_storyboard_with_scenes(client, 3)
    logs = [
        {"storyboard_id": ctx["storyboard_id"], "scene_id": ctx["scene_ids"][0], "tags": ["smile", "standing"], "status": "success"},
        {"storyboard_id": ctx["storyboard_id"], "scene_id": ctx["scene_ids"][1], "tags": ["smile", "sitting"], "status": "success"},
        {"storyboard_id": ctx["storyboard_id"], "scene_id": ctx["scene_ids"][2], "tags": ["frown", "standing"], "status": "fail"},
    ]

    for log_data in logs:
        client.post("/activity-logs", json=log_data)

    response = client.get(
        f"/activity-logs/analyze/patterns?storyboard_id={ctx['storyboard_id']}&min_occurrences=1"
    )

    assert response.status_code == 200
    data = response.json()

    assert "summary" in data
    assert data["summary"]["total_logs"] == 3
    assert data["summary"]["success_count"] >= 2
    assert data["summary"]["fail_count"] >= 1

    assert "tag_stats" in data
    assert len(data["tag_stats"]) > 0


def test_suggest_conflict_rules_no_data(client: TestClient):
    """Test conflict rules suggestion with no data."""
    ctx = _create_storyboard_with_scenes(client, 1)
    response = client.get(
        f"/activity-logs/suggest-conflict-rules?storyboard_id={ctx['storyboard_id']}"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["suggested_rules"] == []
    assert data["new_rules_count"] == 0
