"""TDD tests for Lab router endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from models.lab import LabExperiment


class TestRunExperiment:
    """POST /lab/experiments/run"""

    def test_run_experiment_success(self, client: TestClient, db_session):
        """Successful experiment via API."""
        exp = LabExperiment(
            experiment_type="tag_render",
            status="completed",
            prompt_used="1girl, smile",
            target_tags=["1girl", "smile"],
            match_rate=0.8,
            wd14_result={
                "matched": ["1girl", "smile"],
                "missing": [],
                "extra": [],
            },
            seed=12345,
        )
        db_session.add(exp)
        db_session.commit()

        with patch(
            "routers.lab.run_experiment",
            new_callable=AsyncMock,
            return_value=exp,
        ):
            resp = client.post(
                "/lab/experiments/run",
                json={
                    "target_tags": ["1girl", "smile"],
                    "sd_params": {"steps": 20},
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["match_rate"] == 0.8
        assert data["seed"] == 12345

    def test_run_experiment_minimal_payload(
        self, client: TestClient, db_session,
    ):
        """Minimal payload with only required fields."""
        exp = LabExperiment(
            experiment_type="tag_render",
            status="completed",
            prompt_used="1girl",
            target_tags=["1girl"],
            seed=-1,
        )
        db_session.add(exp)
        db_session.commit()

        with patch(
            "routers.lab.run_experiment",
            new_callable=AsyncMock,
            return_value=exp,
        ):
            resp = client.post(
                "/lab/experiments/run",
                json={"target_tags": ["1girl"]},
            )

        assert resp.status_code == 200
        assert resp.json()["experiment_type"] == "tag_render"

    def test_run_experiment_missing_tags(self, client: TestClient):
        """Missing target_tags field should fail validation."""
        resp = client.post("/lab/experiments/run", json={})
        assert resp.status_code == 422


class TestRunBatch:
    """POST /lab/experiments/run-batch"""

    def test_run_batch_success(self, client: TestClient, db_session):
        """Successful batch run via API."""
        exp = LabExperiment(
            experiment_type="tag_render",
            status="completed",
            prompt_used="1girl",
            target_tags=["1girl"],
            seed=1,
            match_rate=0.9,
        )
        db_session.add(exp)
        db_session.commit()

        batch_result = {
            "batch_id": "abc123",
            "total": 1,
            "completed": 1,
            "failed": 0,
            "experiments": [exp],
        }
        with patch(
            "routers.lab.run_batch",
            new_callable=AsyncMock,
            return_value=batch_result,
        ):
            resp = client.post(
                "/lab/experiments/run-batch",
                json={"target_tags": ["1girl"], "count": 1},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["batch_id"] == "abc123"
        assert data["total"] == 1
        assert data["completed"] == 1


class TestGetExperiments:
    """GET /lab/experiments"""

    def test_list_experiments(self, client: TestClient, db_session):
        """List experiments returns items and total."""
        exp = LabExperiment(
            experiment_type="tag_render",
            status="completed",
            prompt_used="1girl",
            target_tags=["1girl"],
            match_rate=0.9,
            seed=1,
        )
        db_session.add(exp)
        db_session.commit()

        resp = client.get("/lab/experiments")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_list_experiments_filter_type(
        self, client: TestClient, db_session,
    ):
        """Filter by experiment_type."""
        exp1 = LabExperiment(
            experiment_type="tag_render",
            status="completed",
            prompt_used="a",
            target_tags=["a"],
            seed=1,
        )
        exp2 = LabExperiment(
            experiment_type="scene_translate",
            status="completed",
            prompt_used="b",
            target_tags=["b"],
            seed=2,
        )
        db_session.add_all([exp1, exp2])
        db_session.commit()

        resp = client.get("/lab/experiments?experiment_type=tag_render")
        assert resp.status_code == 200
        data = resp.json()
        assert all(
            item["experiment_type"] == "tag_render"
            for item in data["items"]
        )

    def test_list_experiments_empty(self, client: TestClient):
        """Empty DB returns zero items."""
        resp = client.get("/lab/experiments")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_experiments_pagination(
        self, client: TestClient, db_session,
    ):
        """Offset/limit pagination works."""
        for i in range(3):
            db_session.add(LabExperiment(
                experiment_type="tag_render",
                status="completed",
                prompt_used=f"tag_{i}",
                target_tags=[f"tag_{i}"],
                seed=i,
            ))
        db_session.commit()

        resp = client.get("/lab/experiments?limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2


class TestGetExperiment:
    """GET /lab/experiments/{id}"""

    def test_get_experiment_by_id(self, client: TestClient, db_session):
        """Retrieve single experiment by ID."""
        exp = LabExperiment(
            experiment_type="tag_render",
            status="completed",
            prompt_used="1girl",
            target_tags=["1girl"],
            seed=1,
            match_rate=0.8,
        )
        db_session.add(exp)
        db_session.commit()

        resp = client.get(f"/lab/experiments/{exp.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == exp.id

    def test_get_experiment_not_found(self, client: TestClient):
        """Non-existent ID returns 404."""
        resp = client.get("/lab/experiments/99999")
        assert resp.status_code == 404


class TestDeleteExperiment:
    """DELETE /lab/experiments/{id}"""

    def test_delete_experiment(self, client: TestClient, db_session):
        """Delete removes the experiment from DB."""
        exp = LabExperiment(
            experiment_type="tag_render",
            status="completed",
            prompt_used="1girl",
            target_tags=["1girl"],
            seed=1,
        )
        db_session.add(exp)
        db_session.commit()
        exp_id = exp.id

        resp = client.delete(f"/lab/experiments/{exp_id}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Verify deleted from DB
        assert (
            db_session.query(LabExperiment)
            .filter_by(id=exp_id)
            .first()
        ) is None

    def test_delete_experiment_not_found(self, client: TestClient):
        """Delete non-existent experiment returns 404."""
        resp = client.delete("/lab/experiments/99999")
        assert resp.status_code == 404


class TestAnalytics:
    """GET /lab/analytics/tag-effectiveness
    POST /lab/analytics/sync-effectiveness
    """

    def test_get_effectiveness_empty(self, client: TestClient):
        """Empty DB returns zero experiments."""
        resp = client.get("/lab/analytics/tag-effectiveness")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_experiments"] == 0
        assert data["items"] == []

    def test_get_effectiveness_with_data(
        self, client: TestClient, db_session,
    ):
        """Tag effectiveness aggregates from completed experiments."""
        exp = LabExperiment(
            experiment_type="tag_render",
            status="completed",
            prompt_used="1girl, smile",
            target_tags=["1girl", "smile"],
            seed=1,
            match_rate=0.5,
            wd14_result={
                "matched": ["1girl"],
                "missing": ["smile"],
                "extra": [],
            },
        )
        db_session.add(exp)
        db_session.commit()

        resp = client.get("/lab/analytics/tag-effectiveness")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_experiments"] == 1
        assert len(data["items"]) == 2

    def test_sync_effectiveness(self, client: TestClient):
        """Sync endpoint returns synced count."""
        with patch("routers.lab.sync_to_engine", return_value=5):
            resp = client.post("/lab/analytics/sync-effectiveness")
        assert resp.status_code == 200
        assert resp.json()["synced"] == 5
