"""Test storage configuration validation."""

import logging
from unittest.mock import patch

import pytest


class TestValidateStorageConfig:
    """Test validate_storage_config() function."""

    def test_skip_when_local_mode(self):
        """Local storage mode should skip validation entirely."""
        with patch("config.STORAGE_MODE", "local"):
            from config import validate_storage_config

            validate_storage_config()  # Should not raise

    def test_error_when_s3_empty_access_key(self):
        """S3 mode with empty access key should raise ValueError."""
        with (
            patch("config.STORAGE_MODE", "s3"),
            patch("config.MINIO_ACCESS_KEY", ""),
            patch("config.MINIO_SECRET_KEY", "valid_secret_key_123"),
        ):
            from config import validate_storage_config

            with pytest.raises(ValueError, match="MINIO_ACCESS_KEY"):
                validate_storage_config()

    def test_error_when_s3_empty_secret_key(self):
        """S3 mode with empty secret key should raise ValueError."""
        with (
            patch("config.STORAGE_MODE", "s3"),
            patch("config.MINIO_ACCESS_KEY", "valid_access_key"),
            patch("config.MINIO_SECRET_KEY", ""),
        ):
            from config import validate_storage_config

            with pytest.raises(ValueError, match="MINIO_SECRET_KEY"):
                validate_storage_config()

    def test_warning_when_secret_too_short(self, caplog):
        """S3 mode with short secret key should log a warning."""
        with (
            patch("config.STORAGE_MODE", "s3"),
            patch("config.MINIO_ACCESS_KEY", "valid_access"),
            patch("config.MINIO_SECRET_KEY", "short"),
        ):
            from config import validate_storage_config

            with caplog.at_level(logging.WARNING, logger="backend"):
                validate_storage_config()

            assert any("미만" in r.message for r in caplog.records)

    def test_pass_when_valid_credentials(self):
        """S3 mode with valid credentials should pass without error."""
        with (
            patch("config.STORAGE_MODE", "s3"),
            patch("config.MINIO_ACCESS_KEY", "valid_access_key"),
            patch("config.MINIO_SECRET_KEY", "secure_password_123"),
        ):
            from config import validate_storage_config

            validate_storage_config()  # Should not raise
