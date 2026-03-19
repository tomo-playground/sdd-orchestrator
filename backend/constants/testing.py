"""
Testing constants and configuration for deterministic test results.

This module provides fixed seed values and test configurations
to ensure reproducible results in VRT and unit tests.

Usage:
    from constants.testing import VRTConfig, get_test_seed

    if VRTConfig.is_test_mode():
        seed = VRTConfig.FIXED_SEED
    else:
        seed = -1  # random
"""

import os
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class VRTConfig:
    """
    Test configuration for deterministic results.
    """

    # === Fixed Seeds ===
    FIXED_SEED: int = 42  # The answer to everything
    FIXED_SEED_ALT: int = 12345  # Alternative seed for variation tests

    # === SD API Seeds ===
    SD_IMAGE_SEED: int = 42
    SD_AVATAR_SEED: int = 1234

    # === Random State Seeds ===
    META_RANDOM_SEED: int = 9999
    AVATAR_COLOR_SEED: int = 7777

    # === Test Dimensions ===
    TEST_WIDTH_FULL: int = 1080
    TEST_HEIGHT_FULL: int = 1920
    TEST_WIDTH_POST: int = 1080
    TEST_HEIGHT_POST: int = 1080

    # === Test Content ===
    TEST_CHANNEL_NAME: str = "test_channel"
    TEST_CAPTION: str = "테스트 캡션입니다 #test #vrt"
    TEST_SUBTITLE: str = "테스트 자막"

    @staticmethod
    def is_test_mode() -> bool:
        """Check if running in test mode."""
        return os.environ.get("VRT_TEST_MODE", "").lower() in ("1", "true", "yes")

    @staticmethod
    def is_update_golden_mode() -> bool:
        """Check if running in golden master update mode."""
        return os.environ.get("VRT_UPDATE_GOLDEN", "").lower() in ("1", "true", "yes")

    @staticmethod
    def get_sd_seed() -> int:
        """Get SD seed: fixed in test mode, -1 (random) otherwise."""
        if VRTConfig.is_test_mode():
            return VRTConfig.SD_IMAGE_SEED
        return -1

    @staticmethod
    def get_meta_random() -> random.Random:
        """Get Random instance: seeded in test mode, time-based otherwise."""
        import time

        if VRTConfig.is_test_mode():
            return random.Random(VRTConfig.META_RANDOM_SEED)
        return random.Random(time.time_ns())


def get_test_seed(name: str = "default") -> int:
    """
    Get a deterministic seed based on name.
    Useful for generating consistent but different seeds for different test cases.

    Args:
        name: A string identifier for the seed

    Returns:
        A deterministic integer seed
    """
    import hashlib

    hash_value = hashlib.md5(f"{VRTConfig.FIXED_SEED}|{name}".encode()).hexdigest()
    return int(hash_value[:8], 16)


def create_seeded_random(seed: int | None = None) -> random.Random:
    """
    Create a seeded Random instance.

    Args:
        seed: Optional seed value. If None, uses FIXED_SEED in test mode
              or time-based seed otherwise.

    Returns:
        A Random instance
    """
    import time

    if seed is not None:
        return random.Random(seed)
    if VRTConfig.is_test_mode():
        return random.Random(VRTConfig.FIXED_SEED)
    return random.Random(time.time_ns())


# === Test Data Generators ===


def get_test_views_time(seed: int | None = None) -> tuple[str, str]:
    """
    Get deterministic views and time for testing.

    Returns:
        Tuple of (views_str, time_str)
    """
    views_pool = ["1.2k", "2.4k", "3.8k", "5.1k", "7.4k"]
    time_pool = ["방금 전", "1분 전", "5분 전", "10분 전"]

    rng = create_seeded_random(seed)
    return rng.choice(views_pool), rng.choice(time_pool)


def get_test_avatar_color(seed: int | None = None) -> tuple[int, int, int]:
    """
    Get deterministic avatar color for testing.

    Returns:
        RGB tuple
    """
    palette = [
        (255, 183, 77),  # Orange
        (129, 199, 132),  # Green
        (100, 181, 246),  # Blue
        (240, 98, 146),  # Pink
        (186, 104, 200),  # Purple
    ]

    rng = create_seeded_random(seed)
    return rng.choice(palette)
