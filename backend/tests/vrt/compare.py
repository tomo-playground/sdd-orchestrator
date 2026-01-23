"""
VRT Image Comparison Utilities.

Provides SSIM-based image comparison and diff visualization.
"""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def load_image(path: Path | str) -> np.ndarray:
    """Load an image as numpy array (BGR format for OpenCV)."""
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(f"Failed to load image: {path}")
    return img


def load_image_rgb(path: Path | str) -> np.ndarray:
    """Load an image as numpy array (RGB format)."""
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(f"Failed to load image: {path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def save_image(img: np.ndarray, path: Path | str) -> None:
    """Save numpy array as image."""
    if len(img.shape) == 3 and img.shape[2] == 3:
        # Assume RGB, convert to BGR for cv2
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(path), img)


def pil_to_numpy(pil_img: Image.Image) -> np.ndarray:
    """Convert PIL Image to numpy array (RGB)."""
    return np.array(pil_img.convert("RGB"))


def compute_ssim(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    Compute Structural Similarity Index (SSIM) between two images.

    Returns a value between 0 and 1, where 1 means identical images.
    Uses scikit-image's SSIM implementation.
    """
    from skimage.metrics import structural_similarity as ssim

    # Convert to grayscale for SSIM
    if len(img1.shape) == 3:
        gray1 = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
    else:
        gray1 = img1

    if len(img2.shape) == 3:
        gray2 = cv2.cvtColor(img2, cv2.COLOR_RGB2GRAY)
    else:
        gray2 = img2

    # Resize if dimensions don't match
    if gray1.shape != gray2.shape:
        gray2 = cv2.resize(gray2, (gray1.shape[1], gray1.shape[0]))

    return ssim(gray1, gray2)


def compute_pixel_diff(img1: np.ndarray, img2: np.ndarray) -> tuple[float, np.ndarray]:
    """
    Compute pixel-wise difference between two images.

    Returns:
        - diff_ratio: Percentage of pixels that differ (0.0 to 1.0)
        - diff_mask: Binary mask showing different pixels
    """
    # Resize if dimensions don't match
    if img1.shape != img2.shape:
        img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))

    # Compute absolute difference
    diff = cv2.absdiff(img1, img2)

    # Convert to grayscale if color
    if len(diff.shape) == 3:
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_RGB2GRAY)
    else:
        diff_gray = diff

    # Threshold to get binary mask (allow small differences for anti-aliasing)
    _, diff_mask = cv2.threshold(diff_gray, 10, 255, cv2.THRESH_BINARY)

    # Calculate ratio of different pixels
    total_pixels = diff_mask.size
    diff_pixels = np.count_nonzero(diff_mask)
    diff_ratio = diff_pixels / total_pixels

    return diff_ratio, diff_mask


def create_diff_visualization(
    img1: np.ndarray,
    img2: np.ndarray,
    output_path: Path | str | None = None,
) -> np.ndarray:
    """
    Create a side-by-side diff visualization.

    Layout: [Golden Master | Actual | Diff Highlight]
    """
    # Resize if dimensions don't match
    if img1.shape != img2.shape:
        img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))

    # Compute diff
    diff = cv2.absdiff(img1, img2)

    # Highlight differences in red
    diff_highlight = img2.copy()
    if len(diff.shape) == 3:
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_RGB2GRAY)
    else:
        diff_gray = diff

    mask = diff_gray > 10
    if len(diff_highlight.shape) == 3:
        diff_highlight[mask] = [255, 0, 0]  # Red for differences

    # Create side-by-side visualization
    h, w = img1.shape[:2]
    vis = np.zeros((h, w * 3, 3), dtype=np.uint8)

    # Convert grayscale to RGB if needed
    if len(img1.shape) == 2:
        img1 = cv2.cvtColor(img1, cv2.COLOR_GRAY2RGB)
    if len(img2.shape) == 2:
        img2 = cv2.cvtColor(img2, cv2.COLOR_GRAY2RGB)

    vis[:, :w] = img1
    vis[:, w : w * 2] = img2
    vis[:, w * 2 :] = diff_highlight

    # Add labels
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(vis, "Golden Master", (10, 30), font, 0.7, (255, 255, 255), 2)
    cv2.putText(vis, "Actual", (w + 10, 30), font, 0.7, (255, 255, 255), 2)
    cv2.putText(vis, "Diff", (w * 2 + 10, 30), font, 0.7, (255, 255, 255), 2)

    if output_path:
        save_image(vis, output_path)

    return vis


class VRTComparison:
    """
    Visual Regression Test comparison helper.

    Usage:
        vrt = VRTComparison(golden_masters_dir, threshold=0.95)
        result = vrt.compare("subtitle/test_case.png", actual_image)
        assert result.passed, f"VRT failed: SSIM={result.ssim}"
    """

    def __init__(
        self,
        golden_masters_dir: Path,
        ssim_threshold: float = 0.95,
        pixel_diff_threshold: float = 0.01,
        update_mode: bool = False,
    ):
        self.golden_masters_dir = Path(golden_masters_dir)
        self.ssim_threshold = ssim_threshold
        self.pixel_diff_threshold = pixel_diff_threshold
        self.update_mode = update_mode

    def compare(
        self,
        golden_name: str,
        actual: np.ndarray | Image.Image,
        save_diff: bool = True,
    ) -> "VRTResult":
        """
        Compare actual image against golden master.

        Args:
            golden_name: Relative path to golden master (e.g., "subtitle/test.png")
            actual: Actual image (numpy array or PIL Image)
            save_diff: Whether to save diff visualization on failure

        Returns:
            VRTResult with comparison details
        """
        golden_path = self.golden_masters_dir / golden_name

        # Convert PIL to numpy if needed
        if isinstance(actual, Image.Image):
            actual = pil_to_numpy(actual)

        # Update mode: save actual as new golden master
        if self.update_mode:
            golden_path.parent.mkdir(parents=True, exist_ok=True)
            save_image(actual, golden_path)
            return VRTResult(
                passed=True,
                ssim=1.0,
                pixel_diff=0.0,
                message=f"Updated golden master: {golden_name}",
                golden_path=golden_path,
            )

        # Check if golden master exists
        if not golden_path.exists():
            return VRTResult(
                passed=False,
                ssim=0.0,
                pixel_diff=1.0,
                message=f"Golden master not found: {golden_path}. Run with VRT_UPDATE_GOLDEN=1 to create.",
                golden_path=golden_path,
            )

        # Load golden master
        golden = load_image_rgb(golden_path)

        # Compute metrics
        ssim_score = compute_ssim(golden, actual)
        pixel_diff, diff_mask = compute_pixel_diff(golden, actual)

        # Determine pass/fail
        passed = ssim_score >= self.ssim_threshold and pixel_diff <= self.pixel_diff_threshold

        # Save diff visualization if failed
        diff_path = None
        if not passed and save_diff:
            diff_path = golden_path.parent / f"{golden_path.stem}_diff.png"
            create_diff_visualization(golden, actual, diff_path)

        return VRTResult(
            passed=passed,
            ssim=ssim_score,
            pixel_diff=pixel_diff,
            message=f"SSIM={ssim_score:.4f}, PixelDiff={pixel_diff:.4f}",
            golden_path=golden_path,
            diff_path=diff_path,
        )


class VRTResult:
    """Result of a VRT comparison."""

    def __init__(
        self,
        passed: bool,
        ssim: float,
        pixel_diff: float,
        message: str,
        golden_path: Path | None = None,
        diff_path: Path | None = None,
    ):
        self.passed = passed
        self.ssim = ssim
        self.pixel_diff = pixel_diff
        self.message = message
        self.golden_path = golden_path
        self.diff_path = diff_path

    def __bool__(self) -> bool:
        return self.passed

    def __repr__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"VRTResult({status}: {self.message})"
