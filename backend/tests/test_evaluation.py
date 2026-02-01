"""Unit tests for evaluation service (Quality Evaluation System 15.6).

Tests cover:
- Test prompt retrieval
- Prompt building logic
- Evaluation summary computation
- Database query functions (with mocks)
"""

from unittest.mock import MagicMock

import pytest

from services.evaluation import (
    EvaluationResult,
    TestPrompt,
    build_test_prompt,
    compute_evaluation_summary,
    get_evaluation_results,
    get_evaluation_summary,
    get_test_prompt,
    get_test_prompts,
)


class TestGetTestPrompts:
    """Test get_test_prompts() function."""

    def test_returns_dict(self):
        """Should return a dictionary."""
        prompts = get_test_prompts()
        assert isinstance(prompts, dict)

    def test_contains_basic_prompts(self):
        """Should contain the basic 6 test prompts."""
        prompts = get_test_prompts()
        assert "simple_portrait" in prompts
        assert "full_body_pose" in prompts
        assert "action_scene" in prompts
        assert "complex_indoor" in prompts
        assert "emotional_close" in prompts
        assert "multi_element" in prompts

    def test_contains_expression_prompts(self):
        """Should contain expression test prompts."""
        prompts = get_test_prompts()
        assert "expr_angry" in prompts
        assert "expr_surprised" in prompts
        assert "expr_blush" in prompts
        assert "expr_laugh" in prompts

    def test_contains_pose_prompts(self):
        """Should contain pose test prompts."""
        prompts = get_test_prompts()
        assert "pose_jumping" in prompts
        assert "pose_lying" in prompts
        assert "pose_walking" in prompts
        assert "pose_leaning" in prompts

    def test_contains_angle_prompts(self):
        """Should contain camera angle test prompts."""
        prompts = get_test_prompts()
        assert "angle_from_above" in prompts
        assert "angle_from_below" in prompts
        assert "angle_dutch" in prompts

    def test_contains_environment_prompts(self):
        """Should contain environment test prompts."""
        prompts = get_test_prompts()
        assert "env_cafe" in prompts
        assert "env_street" in prompts
        assert "env_beach" in prompts
        assert "env_forest" in prompts

    def test_contains_time_weather_prompts(self):
        """Should contain time/weather test prompts."""
        prompts = get_test_prompts()
        assert "time_night" in prompts
        assert "weather_rain" in prompts
        assert "weather_snow" in prompts
        assert "time_golden" in prompts

    def test_contains_clothing_prompts(self):
        """Should contain clothing test prompts."""
        prompts = get_test_prompts()
        assert "cloth_casual" in prompts
        assert "cloth_formal" in prompts
        assert "cloth_winter" in prompts

    def test_contains_prop_prompts(self):
        """Should contain prop/action test prompts."""
        prompts = get_test_prompts()
        assert "prop_phone" in prompts
        assert "prop_book" in prompts

    def test_returns_copy(self):
        """Should return a copy, not the original dict."""
        prompts1 = get_test_prompts()
        prompts2 = get_test_prompts()
        assert prompts1 is not prompts2  # Different objects
        assert prompts1 == prompts2  # Same content

    def test_all_values_are_test_prompts(self):
        """All values should be TestPrompt instances."""
        prompts = get_test_prompts()
        for value in prompts.values():
            assert isinstance(value, TestPrompt)


class TestGetTestPrompt:
    """Test get_test_prompt() function."""

    def test_get_existing_prompt(self):
        """Should return TestPrompt for valid name."""
        prompt = get_test_prompt("simple_portrait")
        assert isinstance(prompt, TestPrompt)
        assert prompt.name == "simple_portrait"
        assert "smile" in prompt.tokens
        assert "upper body" in prompt.tokens

    def test_get_nonexistent_prompt(self):
        """Should return None for invalid name."""
        prompt = get_test_prompt("nonexistent_prompt")
        assert prompt is None

    def test_get_empty_string(self):
        """Should return None for empty string."""
        prompt = get_test_prompt("")
        assert prompt is None

    def test_verify_prompt_structure(self):
        """Should have correct structure for all required fields."""
        prompt = get_test_prompt("action_scene")
        assert prompt is not None
        assert hasattr(prompt, "name")
        assert hasattr(prompt, "description")
        assert hasattr(prompt, "tokens")
        assert hasattr(prompt, "subject")
        assert prompt.subject == "1girl"


class TestBuildTestPrompt:
    """Test build_test_prompt() function."""

    def test_basic_prompt_standard_mode(self):
        """Should build basic prompt in standard mode."""
        test = TestPrompt(
            name="test",
            description="Test",
            tokens=["smile", "standing"],
        )
        result = build_test_prompt(test)

        # Should include base tokens + test tokens
        assert "masterpiece" in result
        assert "best quality" in result
        assert "1girl" in result
        assert "smile" in result
        assert "standing" in result

    def test_basic_prompt_lora_mode(self):
        """Should build basic prompt in lora mode with BREAK."""
        test = TestPrompt(
            name="test",
            description="Test",
            tokens=["smile", "standing"],
        )
        result = build_test_prompt(test, mode="lora")

        # Should include BREAK for lora mode
        assert "BREAK" in result

    def test_with_character_identity_tags(self):
        """Should include character identity tags."""
        test = TestPrompt(
            name="test",
            description="Test",
            tokens=["smile"],
        )
        identity_tags = ["blue_hair", "red_eyes", "short_hair"]
        result = build_test_prompt(test, character_identity_tags=identity_tags)

        assert "blue_hair" in result
        assert "red_eyes" in result
        assert "short_hair" in result
        assert "smile" in result

    def test_with_character_clothing_tags(self):
        """Should include character clothing tags."""
        test = TestPrompt(
            name="test",
            description="Test",
            tokens=["standing"],
        )
        clothing_tags = ["school_uniform", "necktie"]
        result = build_test_prompt(test, character_clothing_tags=clothing_tags)

        assert "school_uniform" in result
        assert "necktie" in result

    def test_with_lora_trigger_words(self):
        """Should include LoRA trigger words."""
        test = TestPrompt(
            name="test",
            description="Test",
            tokens=["smile"],
        )
        lora_triggers = ["chibi", "cute"]
        result = build_test_prompt(test, lora_trigger_words=lora_triggers)

        assert "chibi" in result
        assert "cute" in result

    def test_lora_mode_adds_break(self):
        """Should add BREAK token in lora mode."""
        test = TestPrompt(
            name="test",
            description="Test",
            tokens=["smile"],
        )
        result_standard = build_test_prompt(test, mode="standard")
        result_lora = build_test_prompt(test, mode="lora")

        assert "BREAK" not in result_standard
        assert "BREAK" in result_lora

    def test_token_ordering(self):
        """Should maintain correct token ordering."""
        test = TestPrompt(
            name="test",
            description="Test",
            tokens=["smile", "standing"],
        )
        identity_tags = ["blue_hair"]
        clothing_tags = ["school_uniform"]
        lora_triggers = ["chibi"]

        result = build_test_prompt(
            test,
            character_identity_tags=identity_tags,
            character_clothing_tags=clothing_tags,
            lora_trigger_words=lora_triggers,
            mode="lora",
        )

        tokens = [t.strip() for t in result.split(",")]

        # Expected order: masterpiece, best quality, 1girl, identity, test tokens, clothing, lora triggers, BREAK
        assert tokens[0] == "masterpiece"
        assert tokens[1] == "best quality"
        assert tokens[2] == "1girl"
        assert "blue_hair" in tokens
        assert "school_uniform" in tokens
        assert "chibi" in tokens
        assert tokens[-1] == "BREAK"

    def test_empty_optional_parameters(self):
        """Should handle None/empty optional parameters."""
        test = TestPrompt(
            name="test",
            description="Test",
            tokens=["smile"],
        )
        result = build_test_prompt(
            test,
            character_identity_tags=None,
            character_clothing_tags=None,
            lora_trigger_words=None,
        )

        # Should only have base + test tokens
        assert "masterpiece" in result
        assert "1girl" in result
        assert "smile" in result
        assert result.count(",") >= 3  # At least 4 tokens

    def test_custom_subject(self):
        """Should use custom subject if provided."""
        test = TestPrompt(
            name="test",
            description="Test",
            tokens=["smile"],
            subject="2girls",
        )
        result = build_test_prompt(test)

        assert "2girls" in result
        assert "1girl" not in result


class TestComputeEvaluationSummary:
    """Test compute_evaluation_summary() function."""

    def test_empty_results(self):
        """Should handle empty results list."""
        summary = compute_evaluation_summary([])

        assert summary["tests"] == []
        assert summary["overall"]["standard_avg"] == 0.0
        assert summary["overall"]["lora_avg"] == 0.0
        assert summary["overall"]["diff"] == 0.0
        assert summary["overall"]["winner"] == "tie"

    def test_single_result(self):
        """Should compute summary for single result."""
        results = [
            EvaluationResult(
                test_name="simple_portrait",
                mode="standard",
                match_rate=0.85,
                matched_tags=["1girl", "smile"],
                missing_tags=["hair"],
                extra_tags=[],
            )
        ]

        summary = compute_evaluation_summary(results)

        assert len(summary["tests"]) == 1
        assert summary["tests"][0]["test_name"] == "simple_portrait"
        assert summary["tests"][0]["standard_avg"] == 0.85
        assert summary["tests"][0]["standard_count"] == 1

    def test_multiple_results_same_test_mode(self):
        """Should average multiple runs of same test/mode."""
        results = [
            EvaluationResult("test1", "standard", 0.8, [], [], []),
            EvaluationResult("test1", "standard", 0.9, [], [], []),
            EvaluationResult("test1", "standard", 0.85, [], [], []),
        ]

        summary = compute_evaluation_summary(results)

        # Average of 0.8, 0.9, 0.85 = 0.85
        assert summary["tests"][0]["standard_avg"] == 0.85
        assert summary["tests"][0]["standard_count"] == 3

    def test_standard_vs_lora_comparison(self):
        """Should compare standard vs lora modes."""
        results = [
            EvaluationResult("test1", "standard", 0.7, [], [], []),
            EvaluationResult("test1", "lora", 0.9, [], [], []),
        ]

        summary = compute_evaluation_summary(results)

        test_summary = summary["tests"][0]
        assert test_summary["standard_avg"] == 0.7
        assert test_summary["lora_avg"] == 0.9
        assert test_summary["diff"] == 0.2
        assert test_summary["winner"] == "lora"

    def test_standard_wins(self):
        """Should identify standard as winner when it's better."""
        results = [
            EvaluationResult("test1", "standard", 0.95, [], [], []),
            EvaluationResult("test1", "lora", 0.75, [], [], []),
        ]

        summary = compute_evaluation_summary(results)

        assert summary["tests"][0]["winner"] == "standard"
        assert summary["tests"][0]["diff"] == -0.2

    def test_tie_case(self):
        """Should identify tie when rates are equal."""
        results = [
            EvaluationResult("test1", "standard", 0.85, [], [], []),
            EvaluationResult("test1", "lora", 0.85, [], [], []),
        ]

        summary = compute_evaluation_summary(results)

        assert summary["tests"][0]["winner"] == "tie"
        assert summary["tests"][0]["diff"] == 0.0

    def test_multiple_tests(self):
        """Should group by test name."""
        results = [
            EvaluationResult("test1", "standard", 0.8, [], [], []),
            EvaluationResult("test1", "lora", 0.9, [], [], []),
            EvaluationResult("test2", "standard", 0.7, [], [], []),
            EvaluationResult("test2", "lora", 0.6, [], [], []),
        ]

        summary = compute_evaluation_summary(results)

        assert len(summary["tests"]) == 2
        test_names = [t["test_name"] for t in summary["tests"]]
        assert "test1" in test_names
        assert "test2" in test_names

    def test_overall_statistics(self):
        """Should compute overall statistics across all tests."""
        results = [
            EvaluationResult("test1", "standard", 0.8, [], [], []),
            EvaluationResult("test1", "lora", 0.9, [], [], []),
            EvaluationResult("test2", "standard", 0.6, [], [], []),
            EvaluationResult("test2", "lora", 0.7, [], [], []),
        ]

        summary = compute_evaluation_summary(results)

        # Overall standard avg: (0.8 + 0.6) / 2 = 0.7
        # Overall lora avg: (0.9 + 0.7) / 2 = 0.8
        assert summary["overall"]["standard_avg"] == 0.7
        assert summary["overall"]["lora_avg"] == 0.8
        assert summary["overall"]["diff"] == 0.1
        assert summary["overall"]["winner"] == "lora"

    def test_rounding_precision(self):
        """Should round to 3 decimal places."""
        results = [
            EvaluationResult("test1", "standard", 0.123456, [], [], []),
            EvaluationResult("test1", "lora", 0.987654, [], [], []),
        ]

        summary = compute_evaluation_summary(results)

        assert summary["tests"][0]["standard_avg"] == 0.123
        assert summary["tests"][0]["lora_avg"] == 0.988
        # diff is computed as lora_avg - standard_avg (both already rounded)
        assert summary["tests"][0]["diff"] == 0.865  # 0.988 - 0.123


class TestGetEvaluationResults:
    """Test get_evaluation_results() function with DB mocks."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_evaluation_run(self):
        """Create a mock EvaluationRun object."""
        from datetime import datetime

        run = MagicMock()
        run.id = 1
        run.test_name = "simple_portrait"
        run.mode = "standard"
        run.character_id = 100
        run.character_name = "Test Character"
        run.match_rate = 0.85
        run.matched_tags = ["1girl", "smile"]
        run.missing_tags = ["blue_hair"]
        run.seed = 12345
        run.batch_id = "batch123"
        run.created_at = datetime(2026, 1, 31, 12, 0, 0)
        return run

    def test_query_all_results(self, mock_db_session, mock_evaluation_run):
        """Should query all results with no filters."""
        # Mock query chain
        query_mock = MagicMock()
        query_mock.order_by.return_value.limit.return_value.all.return_value = [mock_evaluation_run]
        mock_db_session.query.return_value = query_mock

        results = get_evaluation_results(mock_db_session)

        assert len(results) == 1
        assert results[0]["id"] == 1
        assert results[0]["test_name"] == "simple_portrait"
        assert results[0]["mode"] == "standard"
        assert results[0]["match_rate"] == 0.85

    def test_filter_by_character_id(self, mock_db_session, mock_evaluation_run):
        """Should filter by character_id."""
        query_mock = MagicMock()
        query_mock.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_evaluation_run]
        mock_db_session.query.return_value = query_mock

        _ = get_evaluation_results(mock_db_session, character_id=100)

        # Verify filter was called
        query_mock.filter.assert_called_once()

    def test_filter_by_test_name(self, mock_db_session, mock_evaluation_run):
        """Should filter by test_name."""
        query_mock = MagicMock()
        query_mock.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_evaluation_run]
        mock_db_session.query.return_value = query_mock

        _ = get_evaluation_results(mock_db_session, test_name="simple_portrait")

        query_mock.filter.assert_called_once()

    def test_filter_by_batch_id(self, mock_db_session, mock_evaluation_run):
        """Should filter by batch_id."""
        query_mock = MagicMock()
        query_mock.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_evaluation_run]
        mock_db_session.query.return_value = query_mock

        _ = get_evaluation_results(mock_db_session, batch_id="batch123")

        query_mock.filter.assert_called_once()

    def test_limit_results(self, mock_db_session, mock_evaluation_run):
        """Should respect limit parameter."""
        query_mock = MagicMock()
        query_mock.order_by.return_value.limit.return_value.all.return_value = [mock_evaluation_run]
        mock_db_session.query.return_value = query_mock

        _ = get_evaluation_results(mock_db_session, limit=50)

        # Verify limit was called with correct value
        query_mock.order_by.return_value.limit.assert_called_with(50)

    def test_empty_results(self, mock_db_session):
        """Should handle empty query results."""
        query_mock = MagicMock()
        query_mock.order_by.return_value.limit.return_value.all.return_value = []
        mock_db_session.query.return_value = query_mock

        results = get_evaluation_results(mock_db_session)

        assert results == []

    def test_result_serialization(self, mock_db_session, mock_evaluation_run):
        """Should serialize results to dict format."""
        query_mock = MagicMock()
        query_mock.order_by.return_value.limit.return_value.all.return_value = [mock_evaluation_run]
        mock_db_session.query.return_value = query_mock

        results = get_evaluation_results(mock_db_session)

        result = results[0]
        assert isinstance(result, dict)
        assert "id" in result
        assert "test_name" in result
        assert "mode" in result
        assert "character_id" in result
        assert "character_name" in result
        assert "match_rate" in result
        assert "matched_tags" in result
        assert "missing_tags" in result
        assert "seed" in result
        assert "batch_id" in result
        assert "created_at" in result


class TestGetEvaluationSummary:
    """Test get_evaluation_summary() function with DB mocks."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return MagicMock()

    def test_summary_all_characters(self, mock_db_session):
        """Should compute summary for all characters."""
        # Mock query results (test_name, mode, avg_rate, count)
        mock_rows = [
            ("test1", "standard", 0.8, 3),
            ("test1", "lora", 0.9, 3),
            ("test2", "standard", 0.7, 2),
        ]

        query_mock = MagicMock()
        query_mock.group_by.return_value.all.return_value = mock_rows
        mock_db_session.query.return_value = query_mock

        summary = get_evaluation_summary(mock_db_session)

        assert len(summary["tests"]) == 2
        test_names = [t["test_name"] for t in summary["tests"]]
        assert "test1" in test_names
        assert "test2" in test_names

    def test_filter_by_character_id(self, mock_db_session):
        """Should filter by character_id."""
        mock_rows = [
            ("test1", "standard", 0.85, 2),
        ]

        query_mock = MagicMock()
        query_mock.filter.return_value.group_by.return_value.all.return_value = mock_rows
        mock_db_session.query.return_value = query_mock

        _ = get_evaluation_summary(mock_db_session, character_id=100)

        # Verify filter was called
        query_mock.filter.assert_called_once()

    def test_compute_diff_and_winner(self, mock_db_session):
        """Should compute diff and winner correctly."""
        mock_rows = [
            ("test1", "standard", 0.7, 3),
            ("test1", "lora", 0.9, 3),
        ]

        query_mock = MagicMock()
        query_mock.group_by.return_value.all.return_value = mock_rows
        mock_db_session.query.return_value = query_mock

        summary = get_evaluation_summary(mock_db_session)

        test_summary = summary["tests"][0]
        assert test_summary["standard_avg"] == 0.7
        assert test_summary["lora_avg"] == 0.9
        assert test_summary["diff"] == 0.2
        assert test_summary["winner"] == "lora"

    def test_overall_statistics(self, mock_db_session):
        """Should compute overall statistics."""
        mock_rows = [
            ("test1", "standard", 0.8, 3),
            ("test1", "lora", 0.9, 3),
            ("test2", "standard", 0.6, 2),
            ("test2", "lora", 0.7, 2),
        ]

        query_mock = MagicMock()
        query_mock.group_by.return_value.all.return_value = mock_rows
        mock_db_session.query.return_value = query_mock

        summary = get_evaluation_summary(mock_db_session)

        # Overall standard avg: (0.8 + 0.6) / 2 = 0.7
        # Overall lora avg: (0.9 + 0.7) / 2 = 0.8
        assert summary["overall"]["standard_avg"] == 0.7
        assert summary["overall"]["lora_avg"] == 0.8
        assert summary["overall"]["diff"] == 0.1
        assert summary["overall"]["winner"] == "lora"

    def test_empty_database(self, mock_db_session):
        """Should handle empty database."""
        query_mock = MagicMock()
        query_mock.group_by.return_value.all.return_value = []
        mock_db_session.query.return_value = query_mock

        summary = get_evaluation_summary(mock_db_session)

        assert summary["tests"] == []
        assert summary["overall"]["standard_avg"] == 0
        assert summary["overall"]["lora_avg"] == 0
        assert summary["overall"]["diff"] == 0
        assert summary["overall"]["winner"] == "tie"

    def test_mode_only_standard(self, mock_db_session):
        """Should handle case where only standard mode exists."""
        mock_rows = [
            ("test1", "standard", 0.85, 3),
        ]

        query_mock = MagicMock()
        query_mock.group_by.return_value.all.return_value = mock_rows
        mock_db_session.query.return_value = query_mock

        summary = get_evaluation_summary(mock_db_session)

        test_summary = summary["tests"][0]
        assert test_summary["standard_avg"] == 0.85
        assert test_summary.get("lora_avg", 0) == 0
        assert test_summary["winner"] == "standard"

    def test_mode_only_lora(self, mock_db_session):
        """Should handle case where only lora mode exists."""
        mock_rows = [
            ("test1", "lora", 0.92, 3),
        ]

        query_mock = MagicMock()
        query_mock.group_by.return_value.all.return_value = mock_rows
        mock_db_session.query.return_value = query_mock

        summary = get_evaluation_summary(mock_db_session)

        test_summary = summary["tests"][0]
        assert test_summary.get("standard_avg", 0) == 0
        assert test_summary["lora_avg"] == 0.92
        assert test_summary["winner"] == "lora"
