"""
VRT (Visual Regression Test) pytest configuration and fixtures.
"""

import os
from pathlib import Path

import pytest

# Paths
TESTS_DIR = Path(__file__).parent
GOLDEN_MASTERS_DIR = TESTS_DIR / "golden_masters"
FIXTURES_DIR = TESTS_DIR / "fixtures"
BACKEND_DIR = TESTS_DIR.parent


@pytest.fixture
def golden_masters_dir() -> Path:
    """Return the golden masters directory path."""
    return GOLDEN_MASTERS_DIR


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the fixtures directory path."""
    return FIXTURES_DIR


@pytest.fixture
def backend_dir() -> Path:
    """Return the backend directory path."""
    return BACKEND_DIR


@pytest.fixture
def update_golden_mode() -> bool:
    """Check if we're in golden master update mode."""
    return os.environ.get("VRT_UPDATE_GOLDEN", "").lower() in ("1", "true", "yes")


@pytest.fixture
def ssim_threshold() -> float:
    """SSIM threshold for image comparison (0.95 = 95% similarity)."""
    return float(os.environ.get("VRT_SSIM_THRESHOLD", "0.95"))
