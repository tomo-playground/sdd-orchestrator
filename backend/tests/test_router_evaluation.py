"""Tests for evaluation router endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from models import EvaluationRun


class TestListTestPrompts:
    """Test GET /eval/tests endpoint."""

    def test_list_test_prompts(self, client: TestClient):
        """Returns all test prompts with expected structure."""
        response = client.get("/eval/tests")
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        # Verify structure of each item
        for item in data:
            assert "name" in item
            assert "description" in item
            assert "tokens" in item
            assert "subject" in item
            assert isinstance(item["tokens"], list)

    def test_list_test_prompts_contains_known(self, client: TestClient):
        """Known test prompts are included."""
        response = client.get("/eval/tests")
        data = response.json()
        names = [item["name"] for item in data]

        assert "simple_portrait" in names
        assert "full_body_pose" in names
        assert "action_scene" in names


class TestRunEvaluation:
    """Test POST /eval/run endpoint."""

    @patch("routers.evaluation.run_evaluation_batch", new_callable=AsyncMock)
    def test_run_evaluation_valid_tests(self, mock_run, client: TestClient, db_session):
        """Run evaluation with valid test names."""
        mock_run.return_value = {
            "batch_id": "batch_001",
            "total_runs": 6,
            "tests": [
                {"test_name": "simple_portrait", "mode": "standard", "match_rate": 0.85},
            ],
            "overall": {
                "standard_avg": 0.85,
                "lora_avg": 0.90,
                "diff": 0.05,
                "winner": "lora",
            },
        }

        request_data = {
            "test_names": ["simple_portrait"],
            "repetitions": 1,
        }
        response = client.post("/eval/run", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["batch_id"] == "batch_001"
        assert data["total_runs"] == 6
        assert isinstance(data["tests"], list)
        assert data["overall"]["winner"] == "lora"

    def test_run_evaluation_invalid_test_names(self, client: TestClient, db_session):
        """Invalid test names return empty result."""
        request_data = {
            "test_names": ["nonexistent_test"],
            "repetitions": 1,
        }
        response = client.post("/eval/run", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["batch_id"] == ""
        assert data["total_runs"] == 0
        assert data["tests"] == []

    @patch("routers.evaluation.run_evaluation_batch", new_callable=AsyncMock)
    def test_run_evaluation_with_character(self, mock_run, client: TestClient, db_session):
        """Run evaluation with character_id."""
        from models import Character

        char = Character(name="Eval Char", gender="female")
        db_session.add(char)
        db_session.commit()

        mock_run.return_value = {
            "batch_id": "batch_char",
            "total_runs": 2,
            "tests": [],
            "overall": {"standard_avg": 0, "lora_avg": 0, "diff": 0, "winner": "tie"},
        }

        request_data = {
            "test_names": ["simple_portrait"],
            "character_id": char.id,
            "modes": ["standard", "lora"],
            "repetitions": 1,
        }
        response = client.post("/eval/run", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["batch_id"] == "batch_char"

    def test_run_evaluation_validation_error(self, client: TestClient, db_session):
        """Missing required fields returns 422."""
        response = client.post("/eval/run", json={})
        assert response.status_code == 422

    def test_run_evaluation_repetitions_range(self, client: TestClient, db_session):
        """Repetitions must be between 1 and 10."""
        request_data = {
            "test_names": ["simple_portrait"],
            "repetitions": 0,
        }
        response = client.post("/eval/run", json=request_data)
        assert response.status_code == 422

        request_data["repetitions"] = 11
        response = client.post("/eval/run", json=request_data)
        assert response.status_code == 422


class TestGetResults:
    """Test GET /eval/results endpoint."""

    def test_get_results_empty(self, client: TestClient, db_session):
        """Empty DB returns empty list."""
        response = client.get("/eval/results")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_results_with_data(self, client: TestClient, db_session):
        """Returns evaluation run records."""
        run = EvaluationRun(
            test_name="simple_portrait",
            mode="standard",
            prompt_used="1girl, smile",
            match_rate=0.85,
            matched_tags=["smile"],
            missing_tags=["upper_body"],
            seed=42,
            batch_id="batch_test",
        )
        db_session.add(run)
        db_session.commit()

        response = client.get("/eval/results")
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        item = data[0]
        assert item["test_name"] == "simple_portrait"
        assert item["mode"] == "standard"
        assert item["match_rate"] == 0.85
        assert item["seed"] == 42
        assert item["batch_id"] == "batch_test"

    def test_get_results_filter_by_test_name(self, client: TestClient, db_session):
        """Filter results by test_name."""
        run1 = EvaluationRun(
            test_name="simple_portrait",
            mode="standard",
            prompt_used="1girl, smile",
            match_rate=0.85,
        )
        run2 = EvaluationRun(
            test_name="full_body_pose",
            mode="standard",
            prompt_used="1girl, standing",
            match_rate=0.70,
        )
        db_session.add_all([run1, run2])
        db_session.commit()

        response = client.get("/eval/results?test_name=simple_portrait")
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["test_name"] == "simple_portrait"

    def test_get_results_filter_by_batch_id(self, client: TestClient, db_session):
        """Filter results by batch_id."""
        run1 = EvaluationRun(
            test_name="test1",
            mode="standard",
            prompt_used="prompt",
            batch_id="batch_a",
        )
        run2 = EvaluationRun(
            test_name="test2",
            mode="lora",
            prompt_used="prompt",
            batch_id="batch_b",
        )
        db_session.add_all([run1, run2])
        db_session.commit()

        response = client.get("/eval/results?batch_id=batch_a")
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["batch_id"] == "batch_a"

    def test_get_results_filter_by_character_id(self, client: TestClient, db_session):
        """Filter results by character_id."""
        run1 = EvaluationRun(
            test_name="test1",
            mode="standard",
            prompt_used="prompt",
            character_id=10,
        )
        run2 = EvaluationRun(
            test_name="test2",
            mode="standard",
            prompt_used="prompt",
            character_id=20,
        )
        db_session.add_all([run1, run2])
        db_session.commit()

        response = client.get("/eval/results?character_id=10")
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["character_id"] == 10

    def test_get_results_limit(self, client: TestClient, db_session):
        """Limit parameter restricts result count."""
        for i in range(5):
            db_session.add(EvaluationRun(
                test_name=f"test_{i}",
                mode="standard",
                prompt_used="prompt",
            ))
        db_session.commit()

        response = client.get("/eval/results?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestGetSummary:
    """Test GET /eval/summary endpoint."""

    def test_summary_empty(self, client: TestClient, db_session):
        """Empty DB returns zero summary."""
        response = client.get("/eval/summary")
        assert response.status_code == 200
        data = response.json()

        assert "tests" in data
        assert "overall" in data
        assert isinstance(data["tests"], list)

    def test_summary_with_data(self, client: TestClient, db_session):
        """Summary aggregates match rates by test and mode."""
        runs = [
            EvaluationRun(
                test_name="simple_portrait",
                mode="standard",
                prompt_used="prompt",
                match_rate=0.80,
            ),
            EvaluationRun(
                test_name="simple_portrait",
                mode="standard",
                prompt_used="prompt",
                match_rate=0.90,
            ),
            EvaluationRun(
                test_name="simple_portrait",
                mode="lora",
                prompt_used="prompt",
                match_rate=0.95,
            ),
        ]
        db_session.add_all(runs)
        db_session.commit()

        response = client.get("/eval/summary")
        assert response.status_code == 200
        data = response.json()

        assert len(data["tests"]) >= 1
        test_data = data["tests"][0]
        assert test_data["test_name"] == "simple_portrait"
        assert "standard_avg" in test_data
        assert "lora_avg" in test_data

        overall = data["overall"]
        assert "standard_avg" in overall
        assert "lora_avg" in overall
        assert "winner" in overall

    def test_summary_filter_by_character(self, client: TestClient, db_session):
        """Summary filtered by character_id."""
        runs = [
            EvaluationRun(
                test_name="test1",
                mode="standard",
                prompt_used="prompt",
                match_rate=0.80,
                character_id=10,
            ),
            EvaluationRun(
                test_name="test1",
                mode="standard",
                prompt_used="prompt",
                match_rate=0.60,
                character_id=20,
            ),
        ]
        db_session.add_all(runs)
        db_session.commit()

        response = client.get("/eval/summary?character_id=10")
        assert response.status_code == 200
        data = response.json()

        # Only character_id=10 data included
        if data["tests"]:
            assert data["overall"]["standard_avg"] == 0.8
