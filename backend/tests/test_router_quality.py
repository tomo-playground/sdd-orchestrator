"""Tests for quality router endpoints.

Note: The quality router uses Depends(get_db) for session injection.
Tests mock the service functions only; DB session is provided by TestClient fixture.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient


class TestBatchValidate:
    """Test POST /quality/batch-validate endpoint."""

    def test_batch_validate_success(self, client: TestClient, db_session):
        """Batch validate returns expected structure."""
        mock_result = {
            "total": 2,
            "validated": 2,
            "average_match_rate": 0.85,
            "scores": [
                {"scene_id": 1, "match_rate": 0.9, "matched_count": 9, "missing_count": 1},
                {"scene_id": 2, "match_rate": 0.8, "matched_count": 8, "missing_count": 2},
            ],
        }

        with patch("routers.quality.batch_validate_scenes", return_value=mock_result):
            request_data = {
                "storyboard_id": 1,
                "scenes": [
                    {"scene_id": 1, "image_url": "/outputs/images/s1.png", "prompt": "test1"},
                    {"scene_id": 2, "image_url": "/outputs/images/s2.png", "prompt": "test2"},
                ],
            }

            response = client.post("/api/admin/quality/batch-validate", json=request_data)
            assert response.status_code == 200
            data = response.json()

            assert data["total"] == 2
            assert data["validated"] == 2
            assert data["average_match_rate"] == 0.85
            assert len(data["scores"]) == 2

    def test_batch_validate_empty_scenes(self, client: TestClient, db_session):
        """Batch validate with empty scenes list."""
        mock_result = {
            "total": 0,
            "validated": 0,
            "average_match_rate": 0.0,
            "scores": [],
        }

        with patch("routers.quality.batch_validate_scenes", return_value=mock_result):
            request_data = {
                "storyboard_id": 1,
                "scenes": [],
            }

            response = client.post("/api/admin/quality/batch-validate", json=request_data)
            assert response.status_code == 200
            data = response.json()

            assert data["total"] == 0
            assert data["validated"] == 0

    def test_batch_validate_service_error(self, client: TestClient, db_session):
        """Batch validate returns 500 when service raises."""
        with patch(
            "routers.quality.batch_validate_scenes",
            side_effect=RuntimeError("WD14 model not loaded"),
        ):
            request_data = {
                "storyboard_id": 1,
                "scenes": [
                    {"scene_id": 1, "image_url": "/outputs/images/s1.png", "prompt": "test"},
                ],
            }

            response = client.post("/api/admin/quality/batch-validate", json=request_data)
            assert response.status_code == 500

    def test_batch_validate_missing_storyboard_id(self, client: TestClient, db_session):
        """Missing storyboard_id returns 422."""
        request_data = {
            "scenes": [{"scene_id": 1, "image_url": "/test.png", "prompt": "test"}],
        }
        response = client.post("/api/admin/quality/batch-validate", json=request_data)
        assert response.status_code == 422


class TestQualitySummary:
    """Test GET /quality/summary/{storyboard_id} endpoint."""

    def test_quality_summary_success(self, client: TestClient, db_session):
        """Quality summary returns expected structure."""
        mock_summary = {
            "total_scenes": 5,
            "average_match_rate": 0.82,
            "excellent_count": 3,
            "good_count": 1,
            "poor_count": 1,
            "scores": [],
        }

        with patch("routers.quality.get_quality_summary", return_value=mock_summary):
            response = client.get("/api/v1/quality/summary/1")
            assert response.status_code == 200
            data = response.json()

            assert data["total_scenes"] == 5
            assert data["average_match_rate"] == 0.82
            assert data["excellent_count"] == 3
            assert data["good_count"] == 1
            assert data["poor_count"] == 1

    def test_quality_summary_empty(self, client: TestClient, db_session):
        """Quality summary for storyboard with no scores."""
        mock_summary = {
            "total_scenes": 0,
            "average_match_rate": 0.0,
            "excellent_count": 0,
            "good_count": 0,
            "poor_count": 0,
            "scores": [],
        }

        with patch("routers.quality.get_quality_summary", return_value=mock_summary):
            response = client.get("/api/v1/quality/summary/999")
            assert response.status_code == 200
            data = response.json()

            assert data["total_scenes"] == 0

    def test_quality_summary_service_error(self, client: TestClient, db_session):
        """Quality summary returns 500 on service error."""
        with patch(
            "routers.quality.get_quality_summary",
            side_effect=RuntimeError("DB error"),
        ):
            response = client.get("/api/v1/quality/summary/1")
            assert response.status_code == 500


class TestQualitySummaryById:
    """Test GET /quality/summary/storyboard/{storyboard_id} endpoint."""

    def test_summary_by_id_success(self, client: TestClient, db_session):
        """Storyboard-specific quality summary."""
        mock_summary = {
            "total_scenes": 3,
            "average_match_rate": 0.75,
            "excellent_count": 1,
            "good_count": 1,
            "poor_count": 1,
            "scores": [],
        }

        with patch("routers.quality.get_quality_summary", return_value=mock_summary):
            response = client.get("/api/v1/quality/summary/storyboard/1")
            assert response.status_code == 200
            data = response.json()

            assert data["total_scenes"] == 3


class TestQualityAlerts:
    """Test GET /quality/alerts/{storyboard_id} endpoint."""

    def test_quality_alerts_success(self, client: TestClient, db_session):
        """Quality alerts returns scenes below threshold."""
        mock_alerts = [
            {
                "scene_id": 3,
                "match_rate": 0.5,
                "missing_tags": ["smile", "looking_at_viewer"],
                "prompt": "test prompt",
                "image_url": "/outputs/images/s3.png",
            },
        ]

        with patch("routers.quality.get_quality_alerts", return_value=mock_alerts):
            response = client.get("/api/v1/quality/alerts/1")
            assert response.status_code == 200
            data = response.json()

            assert data["count"] == 1
            assert len(data["alerts"]) == 1
            assert data["alerts"][0]["scene_id"] == 3
            assert data["alerts"][0]["match_rate"] == 0.5

    def test_quality_alerts_empty(self, client: TestClient, db_session):
        """No alerts when all scenes are above threshold."""
        with patch("routers.quality.get_quality_alerts", return_value=[]):
            response = client.get("/api/v1/quality/alerts/1")
            assert response.status_code == 200
            data = response.json()

            assert data["count"] == 0
            assert data["alerts"] == []

    def test_quality_alerts_custom_threshold(self, client: TestClient, db_session):
        """Quality alerts respects custom threshold parameter."""
        with patch("routers.quality.get_quality_alerts", return_value=[]) as mock_fn:
            response = client.get("/api/v1/quality/alerts/1?threshold=0.9")
            assert response.status_code == 200

            # Verify the threshold was passed to the service (db is injected by Depends)
            mock_fn.assert_called_once()
            call_args = mock_fn.call_args
            assert call_args[0][0] == 0.9  # threshold
            assert call_args[1]["storyboard_id"] == 1

    def test_quality_alerts_service_error(self, client: TestClient, db_session):
        """Quality alerts returns 500 on service error."""
        with patch(
            "routers.quality.get_quality_alerts",
            side_effect=RuntimeError("DB error"),
        ):
            response = client.get("/api/v1/quality/alerts/1")
            assert response.status_code == 500
