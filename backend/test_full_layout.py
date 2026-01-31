#!/usr/bin/env python3
"""Test script for Full Layout improvements.

Tests:
1. Subtitle size increase (0.034 → 0.042)
2. Subtitle position lowering (0.72 → 0.85)
3. Crop position constant (CROP_Y_RATIO = 0.3)
"""

from constants.layout import FullLayout


def test_subtitle_size():
    """Test subtitle font size increase."""
    print("=" * 60)
    print("Test 1: Subtitle Size")
    print("=" * 60)

    height = 1920  # Full layout height

    # Base font size
    font_size = int(height * FullLayout.SUBTITLE_FONT_RATIO)
    expected = 80  # 1920 * 0.042 = 80.64 → int() = 80
    print(f"✓ Base font size: {font_size}px (expected: {expected}px)")
    assert font_size == expected, f"Expected {expected}, got {font_size}"

    # Min font size
    min_font_size = int(height * FullLayout.SUBTITLE_MIN_FONT_RATIO)
    expected_min = 61  # 1920 * 0.032 = 61.44 → int() = 61
    print(f"✓ Min font size: {min_font_size}px (expected: {expected_min}px)")
    assert min_font_size == expected_min, f"Expected {expected_min}, got {min_font_size}"

    # Comparison
    old_size = int(height * 0.034)  # 65px
    increase = ((font_size - old_size) / old_size) * 100
    print(f"✓ Size increase: {old_size}px → {font_size}px (+{increase:.1f}%)")
    print()


def test_subtitle_position():
    """Test subtitle position lowering."""
    print("=" * 60)
    print("Test 2: Subtitle Position")
    print("=" * 60)

    height = 1920

    # Single line position
    y_single = int(height * FullLayout.SUBTITLE_Y_SINGLE_LINE_RATIO)
    expected_single = 1632  # 1920 * 0.85 = 1632
    bottom_margin_single = height - y_single
    print(f"✓ Single line Y: {y_single}px (bottom margin: {bottom_margin_single}px)")
    assert y_single == expected_single, f"Expected {expected_single}, got {y_single}"

    # Multi line position
    y_multi = int(height * FullLayout.SUBTITLE_Y_MULTI_LINE_RATIO)
    expected_multi = 1574  # 1920 * 0.82 = 1574.4 ≈ 1574
    bottom_margin_multi = height - y_multi
    print(f"✓ Multi line Y: {y_multi}px (bottom margin: {bottom_margin_multi}px)")
    assert y_multi == expected_multi, f"Expected {expected_multi}, got {y_multi}"

    # Comparison
    old_single = int(height * 0.72)  # 1382px
    old_multi = int(height * 0.70)  # 1344px
    print(f"✓ Single line: {old_single}px → {y_single}px (Δ{y_single - old_single}px lower)")
    print(f"✓ Multi line: {old_multi}px → {y_multi}px (Δ{y_multi - old_multi}px lower)")
    print()


def test_crop_position():
    """Test crop position constant."""
    print("=" * 60)
    print("Test 3: Crop Position")
    print("=" * 60)

    crop_y = FullLayout.CROP_Y_RATIO
    expected = 0.3
    print(f"✓ Crop Y ratio: {crop_y} (expected: {expected})")
    assert crop_y == expected, f"Expected {expected}, got {crop_y}"

    # FFmpeg crop calculation example
    # 512x768 → scale to 1080x1920 → 1280x1920 → crop to 1080x1920
    input_h = 1920
    scaled_h = 1920
    output_h = 1920
    crop_y_px = int((scaled_h - output_h) * crop_y)

    print(f"✓ Crop Y position: 30% from top")
    print(f"  - For 512x768 → 1080x1920: Y offset = {crop_y_px}px")
    print(f"  - Preserves top 30% (character head)")
    print()


def test_ffmpeg_filter():
    """Generate sample FFmpeg filter string."""
    print("=" * 60)
    print("Test 4: FFmpeg Filter Generation")
    print("=" * 60)

    out_w = 1080
    out_h = 1920
    crop_y_ratio = FullLayout.CROP_Y_RATIO

    # Simulate filter generation
    filter_str = (
        f"[0:v]scale={out_w}:{out_h}:"
        f"force_original_aspect_ratio=increase,"
        f"crop={out_w}:{out_h}:0:(ih-oh)*{crop_y_ratio}[v0_scaled]"
    )

    print("✓ Generated FFmpeg filter:")
    print(f"  {filter_str}")
    print()
    print("✓ Explanation:")
    print("  - scale=1080:1920:force_original_aspect_ratio=increase")
    print("    → Scale image to cover 1080x1920 (may exceed)")
    print("  - crop=1080:1920:0:(ih-oh)*0.3")
    print("    → Crop to exact 1080x1920")
    print("    → X: 0 (center)")
    print("    → Y: (ih-oh)*0.3 (30% from top)")
    print()


def main():
    """Run all tests."""
    print("\n")
    print("🎬 Full Layout Improvements - Test Suite")
    print("=========================================\n")

    try:
        test_subtitle_size()
        test_subtitle_position()
        test_crop_position()
        test_ffmpeg_filter()

        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print("\nSummary:")
        print("  - Subtitle size: 65px → 80px (+23%)")
        print("  - Subtitle position: Lower by 250-230px")
        print("  - Crop position: Top-weighted (30% from top)")
        print("\nNext: Test with actual video rendering")
        print()

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
