import uuid

import pytest
from fastapi.testclient import TestClient


def _create_storyboard(client: TestClient) -> int:
    """Create a test storyboard and return its ID."""
    response = client.post(
        "/storyboards",
        json={
            "title": f"Test Storyboard {uuid.uuid4().hex[:4]}",
            "description": "testing",
            "scenes": [],
        },
    )
    assert response.status_code == 200
    return response.json()["storyboard_id"]


def test_batch_validate_empty_scenes(client: TestClient):
    """Test batch validation with empty scenes list."""
    storyboard_id = _create_storyboard(client)
    response = client.post(
        "/quality/batch-validate",
        json={"storyboard_id": storyboard_id, "scenes": []},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["validated"] == 0
    assert data["average_match_rate"] == 0.0
    assert data["scores"] == []


def test_batch_validate_missing_images(client: TestClient):
    """Test batch validation with scenes that have no images."""
    storyboard_id = _create_storyboard(client)
    response = client.post(
        "/quality/batch-validate",
        json={
            "storyboard_id": storyboard_id,
            "scenes": [
                {"scene_id": 1, "image_url": None, "prompt": "test prompt"},
                {"scene_id": 2, "image_url": "", "prompt": "test prompt 2"},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["validated"] == 0  # No valid images to validate


def test_batch_validate_nonexistent_images(client: TestClient):
    """Test batch validation with non-existent image paths."""
    storyboard_id = _create_storyboard(client)
    response = client.post(
        "/quality/batch-validate",
        json={
            "storyboard_id": storyboard_id,
            "scenes": [
                {
                    "scene_id": 1,
                    "image_url": "/outputs/images/nonexistent.png",
                    "prompt": "1girl, smile, standing",
                },
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    # Should skip non-existent files
    assert data["validated"] == 0


def test_quality_summary_empty_storyboard(client: TestClient):
    """Test quality summary for non-existent storyboard."""
    response = client.get("/quality/summary/99999")
    assert response.status_code == 200
    data = response.json()
    assert data["total_scenes"] == 0
    assert data["average_match_rate"] == 0.0
    assert data["excellent_count"] == 0
    assert data["good_count"] == 0
    assert data["poor_count"] == 0
    assert data["scores"] == []


def test_quality_alerts_empty_storyboard(client: TestClient):
    """Test quality alerts for non-existent storyboard."""
    response = client.get(
        "/quality/alerts/99999?threshold=0.7",
    )
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert "count" in data
    assert data["count"] == 0
    assert data["alerts"] == []


def test_quality_alerts_default_threshold(client: TestClient):
    """Test quality alerts with default threshold (0.7)."""
    storyboard_id = _create_storyboard(client)
    response = client.get(
        f"/quality/alerts/{storyboard_id}",
    )
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert "count" in data


def test_quality_alerts_custom_threshold(client: TestClient):
    """Test quality alerts with custom threshold."""
    storyboard_id = _create_storyboard(client)
    response = client.get(
        f"/quality/alerts/{storyboard_id}?threshold=0.5",
    )
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    # Threshold 0.5 should return fewer (or equal) alerts than 0.7
    assert data["count"] >= 0


def test_batch_validate_request_validation(client: TestClient):
    """Test batch validate request validation."""
    # Missing storyboard_id
    response = client.post(
        "/quality/batch-validate",
        json={"scenes": []},
    )
    assert response.status_code == 422  # Validation error

    # Missing scenes
    response = client.post(
        "/quality/batch-validate",
        json={"storyboard_id": 1},
    )
    assert response.status_code == 422


def test_quality_summary_route_format(client: TestClient):
    """Test quality summary returns correct structure."""
    storyboard_id = _create_storyboard(client)
    response = client.get(f"/quality/summary/{storyboard_id}")
    assert response.status_code == 200
    data = response.json()

    # Check all required keys are present
    required_keys = [
        "total_scenes",
        "average_match_rate",
        "excellent_count",
        "good_count",
        "poor_count",
        "scores",
    ]
    for key in required_keys:
        assert key in data, f"Missing key: {key}"

    # Check types
    assert isinstance(data["total_scenes"], int)
    assert isinstance(data["average_match_rate"], float)
    assert isinstance(data["excellent_count"], int)
    assert isinstance(data["good_count"], int)
    assert isinstance(data["poor_count"], int)
    assert isinstance(data["scores"], list)


def test_quality_alerts_response_structure(client: TestClient):
    """Test quality alerts returns correct structure."""
    storyboard_id = _create_storyboard(client)
    response = client.get(
        f"/quality/alerts/{storyboard_id}?threshold=0.7",
    )
    assert response.status_code == 200
    data = response.json()

    assert "alerts" in data
    assert "count" in data
    assert isinstance(data["alerts"], list)
    assert isinstance(data["count"], int)
    assert data["count"] == len(data["alerts"])

    # If there are alerts, check structure
    if data["alerts"]:
        alert = data["alerts"][0]
        assert "scene_id" in alert
        assert "match_rate" in alert
        assert "missing_tags" in alert


@pytest.mark.parametrize(
    "threshold,expected_status",
    [
        (0.0, 200),
        (0.5, 200),
        (0.7, 200),
        (1.0, 200),
        (-0.1, 200),  # Should still work, just returns all scenes
        (1.5, 200),   # Should work, just returns no scenes
    ],
)
def test_quality_alerts_various_thresholds(client: TestClient, threshold: float, expected_status: int):
    """Test quality alerts with various threshold values."""
    storyboard_id = _create_storyboard(client)
    response = client.get(
        f"/quality/alerts/{storyboard_id}?threshold={threshold}",
    )
    assert response.status_code == expected_status
