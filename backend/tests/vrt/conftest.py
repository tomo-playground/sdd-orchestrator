"""
VRT-specific pytest fixtures.
"""

import sys
from pathlib import Path

import pytest

# Add backend to path for imports
BACKEND_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from tests.vrt.compare import VRTComparison


@pytest.fixture
def vrt(golden_masters_dir: Path, update_golden_mode: bool, ssim_threshold: float) -> VRTComparison:
    """Create a VRTComparison instance for tests."""
    return VRTComparison(
        golden_masters_dir=golden_masters_dir,
        ssim_threshold=ssim_threshold,
        update_mode=update_golden_mode,
    )


@pytest.fixture
def sample_font_path(backend_dir: Path) -> Path:
    """Return path to a sample font for testing."""
    fonts_dir = backend_dir / "assets" / "fonts"
    # Try to find any TTF font
    for font_file in fonts_dir.glob("*.ttf"):
        return font_file
    for font_file in fonts_dir.glob("*.TTF"):
        return font_file
    pytest.skip("No font files found in assets/fonts/")


@pytest.fixture
def sample_image_512(backend_dir: Path) -> Path | None:
    """Return path to a 512x512 sample image if available."""
    # Check outputs/images for any existing image
    outputs_dir = backend_dir / "outputs" / "images"
    if outputs_dir.exists():
        for img_file in outputs_dir.rglob("*.png"):
            return img_file
    return None
