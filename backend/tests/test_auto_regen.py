"""Tests for auto-regeneration helpers (Phase 16-C)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.auto_regen import describe_failure, has_critical_failure, shift_seed_for_retry


class TestHasCriticalFailure:
    def test_no_failure_key(self):
        assert has_critical_failure({}) is False

    def test_failure_key_none(self):
        assert has_critical_failure({"_critical_failure": None}) is False

    def test_failure_key_empty(self):
        assert has_critical_failure({"_critical_failure": {"has_failure": False}}) is False

    def test_failure_present(self):
        result = {
            "_critical_failure": {
                "has_failure": True,
                "failures": [{"failure_type": "gender_swap"}],
            }
        }
        assert has_critical_failure(result) is True


class TestDescribeFailure:
    def test_no_failure(self):
        assert describe_failure({}) == ""

    def test_gender_swap(self):
        result = {
            "_critical_failure": {
                "has_failure": True,
                "failures": [{"failure_type": "gender_swap"}],
            }
        }
        assert "성별 반전" in describe_failure(result)

    def test_no_subject(self):
        result = {
            "_critical_failure": {
                "has_failure": True,
                "failures": [{"failure_type": "no_subject"}],
            }
        }
        assert "인물 미감지" in describe_failure(result)

    def test_count_mismatch(self):
        result = {
            "_critical_failure": {
                "has_failure": True,
                "failures": [{"failure_type": "count_mismatch"}],
            }
        }
        assert "인물수 불일치" in describe_failure(result)

    def test_multiple_failures(self):
        result = {
            "_critical_failure": {
                "has_failure": True,
                "failures": [
                    {"failure_type": "gender_swap"},
                    {"failure_type": "count_mismatch"},
                ],
            }
        }
        desc = describe_failure(result)
        assert "성별 반전" in desc
        assert "인물수 불일치" in desc


class TestShiftSeedForRetry:
    def test_random_seed_unchanged(self):
        req = SimpleNamespace(seed=-1)
        shift_seed_for_retry(req, 1)
        assert req.seed == -1

    def test_fixed_seed_shifted(self):
        req = SimpleNamespace(seed=42)
        shift_seed_for_retry(req, 1)
        assert req.seed == (42 + 1000) % (2**31)

    def test_fixed_seed_second_retry(self):
        req = SimpleNamespace(seed=42)
        shift_seed_for_retry(req, 2)
        assert req.seed == (42 + 2000) % (2**31)

    def test_large_seed_wraps(self):
        req = SimpleNamespace(seed=2**31 - 500)
        shift_seed_for_retry(req, 1)
        assert req.seed == (2**31 - 500 + 1000) % (2**31)

    def test_zero_seed_unchanged(self):
        """Seed 0 is treated as random (not positive)."""
        req = SimpleNamespace(seed=0)
        shift_seed_for_retry(req, 1)
        assert req.seed == 0


class TestValidateForCriticalFailure:
    @patch("PIL.Image.open")
    @patch("services.image.load_image_bytes")
    @patch("services.validation.wd14_predict_tags")
    @patch("services.critical_failure.detect_critical_failure")
    def test_no_failure(self, mock_detect, mock_predict, mock_load, mock_open):
        from services.auto_regen import validate_for_critical_failure
        from services.critical_failure import CriticalFailureResult

        mock_load.return_value = b"fake_png"
        mock_open.return_value = MagicMock()
        mock_predict.return_value = [{"tag": "1girl", "score": 0.95, "category": "0"}]
        mock_detect.return_value = CriticalFailureResult(has_failure=False)

        result = validate_for_critical_failure({"image": "base64data"}, "1girl, smile")
        assert result is None

    @patch("PIL.Image.open")
    @patch("services.image.load_image_bytes")
    @patch("services.validation.wd14_predict_tags")
    @patch("services.critical_failure.detect_critical_failure")
    def test_failure_detected(self, mock_detect, mock_predict, mock_load, mock_open):
        from services.auto_regen import validate_for_critical_failure
        from services.critical_failure import CriticalFailure, CriticalFailureResult

        mock_load.return_value = b"fake_png"
        mock_open.return_value = MagicMock()
        mock_predict.return_value = [{"tag": "1boy", "score": 0.95, "category": "0"}]
        mock_detect.return_value = CriticalFailureResult(
            has_failure=True,
            failures=[CriticalFailure("gender_swap", "female", "male", 0.95)],
        )

        result = validate_for_critical_failure({"image": "base64data"}, "1girl, smile")
        assert result is not None
        assert result["has_failure"] is True

    def test_no_image(self):
        from services.auto_regen import validate_for_critical_failure

        assert validate_for_critical_failure({}, "1girl") is None

    def test_no_prompt(self):
        from services.auto_regen import validate_for_critical_failure

        assert validate_for_critical_failure({"image": "data"}, "") is None
