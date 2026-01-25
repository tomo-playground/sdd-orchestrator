"""
VRT (Visual Regression Test) pytest configuration and fixtures.
"""

import os
import random
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Paths
TESTS_DIR = Path(__file__).parent
GOLDEN_MASTERS_DIR = TESTS_DIR / "golden_masters"
FIXTURES_DIR = TESTS_DIR / "fixtures"
BACKEND_DIR = TESTS_DIR.parent

# Add backend to path for imports
sys.path.insert(0, str(BACKEND_DIR))

from main import app  # Import app after sys.path setup


@pytest.fixture(autouse=True)
def set_test_mode():
    """Automatically set test mode for all tests."""
    os.environ["VRT_TEST_MODE"] = "1"
    yield
    # Cleanup after test
    if "VRT_TEST_MODE" in os.environ:
        del os.environ["VRT_TEST_MODE"]


@pytest.fixture(autouse=True)
def seed_random():
    """Seed random for deterministic tests."""
    random.seed(42)
    yield


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


@pytest.fixture
def fixed_seed() -> int:
    """Return the fixed seed for deterministic tests."""
    from constants.testing import VRTConfig
    return VRTConfig.FIXED_SEED


@pytest.fixture
def test_random() -> random.Random:
    """Return a seeded Random instance for tests."""
    from constants.testing import create_seeded_random
    return create_seeded_random()


@pytest.fixture
def client() -> TestClient:
    """Return a FastAPI TestClient."""
    return TestClient(app)

