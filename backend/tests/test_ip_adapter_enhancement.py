"""Tests for IP-Adapter Enhancement Phase 1~3.

Phase 1-B: Reference quality validation
Phase 3-A: Per-character guidance parameters
Phase 3-B: Face tag suppression for FaceID
Phase 1-A: Photo upload preprocessing
Phase 2-A: Multi-angle reference selection
Phase 2-B: Dual IP-Adapter units
"""

from __future__ import annotations

import base64
import io
from unittest.mock import patch

from PIL import Image

# ── Helpers ────────────────────────────────────────────────────


def _make_test_image(width: int = 512, height: int = 512, color: str = "white") -> str:
    """Create a test image as base64."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ── Phase 1-B: Reference Quality Validation ───────────────────


class TestReferenceQualityValidation:
    """Tests for validate_reference_quality()."""

    @patch("services.ip_adapter._detect_all_faces")
    def test_valid_reference(self, mock_faces):
        """Good reference: face detected, good resolution, single person."""
        from services.ip_adapter import validate_reference_quality

        mock_faces.return_value = [(100, 100, 200, 200)]  # 1 face

        image_b64 = _make_test_image(512, 512)
        report = validate_reference_quality(image_b64)

        assert report.valid is True
        assert report.face_detected is True
        assert report.resolution_ok is True
        assert report.face_count == 1
        assert report.face_size_ratio > 0.10
        assert len(report.warnings) == 0

    @patch("services.ip_adapter._detect_all_faces")
    def test_no_face_detected(self, mock_faces):
        """No face → invalid."""
        from services.ip_adapter import validate_reference_quality

        mock_faces.return_value = []

        image_b64 = _make_test_image(512, 512)
        report = validate_reference_quality(image_b64)

        assert report.valid is False
        assert report.face_detected is False
        assert any("얼굴을 탐지하지 못했습니다" in w for w in report.warnings)

    @patch("services.ip_adapter._detect_all_faces")
    def test_low_resolution_rejected(self, mock_faces):
        """Resolution below 256x256 → invalid."""
        from services.ip_adapter import validate_reference_quality

        mock_faces.return_value = [(10, 10, 50, 50)]

        image_b64 = _make_test_image(128, 128)
        report = validate_reference_quality(image_b64)

        assert report.valid is False
        assert report.resolution_ok is False
        assert any("해상도가 너무 낮습니다" in w for w in report.warnings)

    @patch("services.ip_adapter._detect_all_faces")
    def test_small_face_warning(self, mock_faces):
        """Face too small (< 10% of image) → warning."""
        from services.ip_adapter import validate_reference_quality

        mock_faces.return_value = [(200, 200, 20, 20)]  # Tiny face

        image_b64 = _make_test_image(512, 512)
        report = validate_reference_quality(image_b64)

        assert report.valid is False  # face too small
        assert report.face_size_ratio < 0.10
        assert any("얼굴이 너무 작습니다" in w for w in report.warnings)

    @patch("services.ip_adapter._detect_all_faces")
    def test_multiple_faces_warning(self, mock_faces):
        """Multiple faces → warning but still valid if primary face is good."""
        from services.ip_adapter import validate_reference_quality

        # 3 faces, largest is (100, 100, 200, 200)
        mock_faces.return_value = [
            (100, 100, 200, 200),
            (350, 100, 80, 80),
            (50, 300, 60, 60),
        ]

        image_b64 = _make_test_image(512, 512)
        report = validate_reference_quality(image_b64)

        assert report.face_count == 3
        assert any("복수 얼굴 감지" in w for w in report.warnings)


# ── Phase 3-A: Guidance Parameters ────────────────────────────


class TestGuidanceParameters:
    """Tests for per-character guidance in build_ip_adapter_args."""

    def test_faceid_default_guidance(self):
        """FaceID model defaults to guidance_end=0.85."""
        from services.controlnet import build_ip_adapter_args

        args = build_ip_adapter_args(
            reference_image="test_b64",
            weight=0.5,
            model="faceid",
        )
        assert args["guidance_start"] == 0.0
        assert args["guidance_end"] == 0.85

    def test_clip_default_guidance(self):
        """CLIP model defaults to guidance_end=1.0."""
        from services.controlnet import build_ip_adapter_args

        args = build_ip_adapter_args(
            reference_image="test_b64",
            weight=0.5,
            model="clip_face",
        )
        assert args["guidance_start"] == 0.0
        assert args["guidance_end"] == 1.0

    def test_custom_guidance_override(self):
        """Custom guidance values override defaults."""
        from services.controlnet import build_ip_adapter_args

        args = build_ip_adapter_args(
            reference_image="test_b64",
            weight=0.5,
            model="faceid",
            guidance_start=0.1,
            guidance_end=0.9,
        )
        assert args["guidance_start"] == 0.1
        assert args["guidance_end"] == 0.9

    def test_consistency_strategy_includes_guidance(self):
        """ConsistencyStrategy carries guidance_start and guidance_end."""
        from services.character_consistency import ConsistencyStrategy

        strategy = ConsistencyStrategy(
            ip_adapter_enabled=True,
            ip_adapter_guidance_start=0.1,
            ip_adapter_guidance_end=0.9,
        )
        assert strategy.ip_adapter_guidance_start == 0.1
        assert strategy.ip_adapter_guidance_end == 0.9

    def test_consistency_strategy_guidance_defaults_none(self):
        """Default strategy has None guidance (uses config defaults)."""
        from services.character_consistency import ConsistencyStrategy

        strategy = ConsistencyStrategy()
        assert strategy.ip_adapter_guidance_start is None
        assert strategy.ip_adapter_guidance_end is None


# ── Phase 3-B: Face Tag Suppression ───────────────────────────


class TestFaceTagSuppression:
    """Tests for suppress_face_tags_for_faceid()."""

    def test_faceid_suppresses_face_tags(self):
        """FaceID mode suppresses hair/eye color tags to 0.3 weight."""
        from services.generation_prompt import suppress_face_tags_for_faceid

        prompt = "brown_hair, blue_eyes, 1girl, school_uniform, smile"
        result = suppress_face_tags_for_faceid(prompt, "faceid")

        assert "(brown_hair:0.3)" in result
        assert "(blue_eyes:0.3)" in result
        assert "1girl" in result  # Not suppressed
        assert "school_uniform" in result  # Not suppressed
        assert "smile" in result  # Not suppressed

    def test_clip_does_not_suppress(self):
        """CLIP mode leaves face tags unchanged."""
        from services.generation_prompt import suppress_face_tags_for_faceid

        prompt = "brown_hair, blue_eyes, 1girl"
        result = suppress_face_tags_for_faceid(prompt, "clip_face")

        assert result == prompt

    def test_clip_model_does_not_suppress(self):
        """Explicit clip model leaves face tags unchanged."""
        from services.generation_prompt import suppress_face_tags_for_faceid

        prompt = "brown_hair, blue_eyes, 1girl"
        result = suppress_face_tags_for_faceid(prompt, "clip")

        assert result == prompt

    def test_none_model_does_not_suppress(self):
        """None model leaves face tags unchanged."""
        from services.generation_prompt import suppress_face_tags_for_faceid

        prompt = "brown_hair, blue_eyes, 1girl"
        result = suppress_face_tags_for_faceid(prompt, None)

        assert result == prompt

    def test_lora_tags_preserved(self):
        """LoRA tags are never suppressed."""
        from services.generation_prompt import suppress_face_tags_for_faceid

        prompt = "<lora:brown_hair_lora:0.7>, brown_hair, 1girl"
        result = suppress_face_tags_for_faceid(prompt, "faceid")

        assert "<lora:brown_hair_lora:0.7>" in result
        assert "(brown_hair:0.3)" in result

    def test_already_weighted_tags_skipped(self):
        """Already weighted tags (parenthesized) are skipped."""
        from services.generation_prompt import suppress_face_tags_for_faceid

        prompt = "(brown_hair:1.2), blue_eyes, 1girl"
        result = suppress_face_tags_for_faceid(prompt, "faceid")

        # Already weighted → preserved as-is
        assert "(brown_hair:1.2)" in result
        assert "(blue_eyes:0.3)" in result

    def test_freckles_suppressed(self):
        """Facial feature tags like freckles are suppressed."""
        from services.generation_prompt import suppress_face_tags_for_faceid

        prompt = "freckles, 1girl, school_uniform"
        result = suppress_face_tags_for_faceid(prompt, "faceid")

        assert "(freckles:0.3)" in result


# ── Phase 1-A: Photo Upload Preprocessing ─────────────────────


class TestPhotoPreprocessing:
    """Tests for _preprocess_uploaded_photo()."""

    @patch("services.image.detect_face")
    def test_face_crop_and_resize(self, mock_detect):
        """Photo with face → face-centered crop to 512x512."""
        from services.ip_adapter import _preprocess_uploaded_photo

        # Face at (200, 150, 100, 100) in a 800x600 image
        mock_detect.return_value = (200, 150, 100, 100)
        img = Image.new("RGB", (800, 600), "white")

        result = _preprocess_uploaded_photo(img)

        assert result.size == (512, 512)

    @patch("services.image.detect_face")
    def test_no_face_center_crop(self, mock_detect):
        """No face detected → center square crop to 512x512."""
        from services.ip_adapter import _preprocess_uploaded_photo

        mock_detect.return_value = None
        img = Image.new("RGB", (800, 600), "white")

        result = _preprocess_uploaded_photo(img)

        assert result.size == (512, 512)

    @patch("services.image.detect_face")
    def test_square_image_no_face(self, mock_detect):
        """Square image without face → full image resized."""
        from services.ip_adapter import _preprocess_uploaded_photo

        mock_detect.return_value = None
        img = Image.new("RGB", (1024, 1024), "white")

        result = _preprocess_uploaded_photo(img)

        assert result.size == (512, 512)


# ── Phase 2-A: Multi-Angle Reference Selection ────────────────


class TestMultiAngleSelection:
    """Tests for select_best_reference()."""

    def _make_refs(self) -> list[dict]:
        return [
            {"angle": "front", "asset_id": 1, "image_b64": "front_b64"},
            {"angle": "side_left", "asset_id": 2, "image_b64": "side_left_b64"},
            {"angle": "side_right", "asset_id": 3, "image_b64": "side_right_b64"},
            {"angle": "back", "asset_id": 4, "image_b64": "back_b64"},
        ]

    def test_side_tag_selects_side_ref(self):
        """from_side tag → side_left reference."""
        from services.ip_adapter import select_best_reference

        refs = self._make_refs()
        result = select_best_reference(["from_side", "1girl"], refs)

        assert result is not None
        assert result["angle"] == "side_left"

    def test_profile_tag_selects_side_ref(self):
        """profile tag → side_left reference."""
        from services.ip_adapter import select_best_reference

        refs = self._make_refs()
        result = select_best_reference(["profile", "smile"], refs)

        assert result is not None
        assert result["angle"] == "side_left"

    def test_from_behind_selects_back_ref(self):
        """from_behind tag → back reference."""
        from services.ip_adapter import select_best_reference

        refs = self._make_refs()
        result = select_best_reference(["from_behind", "1girl"], refs)

        assert result is not None
        assert result["angle"] == "back"

    def test_no_angle_tag_defaults_to_front(self):
        """No angle tag → fallback to front reference."""
        from services.ip_adapter import select_best_reference

        refs = self._make_refs()
        result = select_best_reference(["1girl", "school_uniform"], refs)

        assert result is not None
        assert result["angle"] == "front"

    def test_empty_refs_returns_none(self):
        """No references → None."""
        from services.ip_adapter import select_best_reference

        result = select_best_reference(["from_side"], [])
        assert result is None

    def test_missing_angle_falls_back_to_front(self):
        """Requested angle not available → fallback to front."""
        from services.ip_adapter import select_best_reference

        refs = [{"angle": "front", "asset_id": 1, "image_b64": "front_b64"}]
        result = select_best_reference(["from_behind"], refs)

        assert result is not None
        assert result["angle"] == "front"


# ── Phase 2-B: Dual IP-Adapter Units ──────────────────────────


class TestDualIPAdapter:
    """Tests for build_dual_ip_adapter_args()."""

    def test_dual_args_count(self):
        """Dual unit produces exactly 2 args."""
        from services.ip_adapter import build_dual_ip_adapter_args

        args = build_dual_ip_adapter_args(
            primary_image="primary_b64",
            secondary_image="secondary_b64",
            weight=0.5,
            model="clip_face",
        )

        assert len(args) == 2

    def test_dual_weight_distribution(self):
        """Primary gets 70%, secondary gets 30% of base weight."""
        from services.ip_adapter import build_dual_ip_adapter_args

        args = build_dual_ip_adapter_args(
            primary_image="primary_b64",
            secondary_image="secondary_b64",
            weight=1.0,
            model="clip_face",
        )

        assert abs(args[0]["weight"] - 0.7) < 0.01  # 70%
        assert abs(args[1]["weight"] - 0.3) < 0.01  # 30%

    def test_dual_guidance_passthrough(self):
        """Custom guidance passed to both units."""
        from services.ip_adapter import build_dual_ip_adapter_args

        args = build_dual_ip_adapter_args(
            primary_image="primary_b64",
            secondary_image="secondary_b64",
            weight=0.5,
            model="faceid",
            guidance_start=0.1,
            guidance_end=0.8,
        )

        for arg in args:
            assert arg["guidance_start"] == 0.1
            assert arg["guidance_end"] == 0.8

    def test_dual_default_weight(self):
        """Default weight from config when None."""
        from services.ip_adapter import build_dual_ip_adapter_args

        args = build_dual_ip_adapter_args(
            primary_image="p",
            secondary_image="s",
            model="clip_face",
        )

        # Default weight is 0.50 from config (DEFAULT_CHARACTER_PRESET["weight"])
        from config import DEFAULT_CHARACTER_PRESET
        default_w = DEFAULT_CHARACTER_PRESET["weight"]
        assert abs(args[0]["weight"] - default_w * 0.7) < 0.01
        assert abs(args[1]["weight"] - default_w * 0.3) < 0.01


# ── Config Constants ───────────────────────────────────────────


class TestConfigConstants:
    """Verify config constants are properly set."""

    def test_guidance_defaults(self):
        from config import (
            DEFAULT_IP_ADAPTER_GUIDANCE_END_CLIP,
            DEFAULT_IP_ADAPTER_GUIDANCE_END_FACEID,
            DEFAULT_IP_ADAPTER_GUIDANCE_START,
        )

        assert DEFAULT_IP_ADAPTER_GUIDANCE_START == 0.0
        assert DEFAULT_IP_ADAPTER_GUIDANCE_END_FACEID == 0.85
        assert DEFAULT_IP_ADAPTER_GUIDANCE_END_CLIP == 1.0

    def test_faceid_suppress_tags_nonempty(self):
        from config import FACEID_SUPPRESS_TAGS, FACEID_SUPPRESS_WEIGHT

        assert len(FACEID_SUPPRESS_TAGS) > 10
        assert FACEID_SUPPRESS_WEIGHT == 0.3
        assert "brown_hair" in FACEID_SUPPRESS_TAGS
        assert "blue_eyes" in FACEID_SUPPRESS_TAGS

    def test_reference_quality_thresholds(self):
        from config import REFERENCE_MIN_FACE_RATIO, REFERENCE_MIN_RESOLUTION

        assert REFERENCE_MIN_RESOLUTION == 256
        assert REFERENCE_MIN_FACE_RATIO == 0.10

    def test_dual_adapter_config(self):
        from config import (
            IP_ADAPTER_DUAL_ENABLED,
            IP_ADAPTER_DUAL_PRIMARY_RATIO,
            IP_ADAPTER_DUAL_SECONDARY_RATIO,
        )

        assert IP_ADAPTER_DUAL_ENABLED is False  # opt-in
        assert IP_ADAPTER_DUAL_PRIMARY_RATIO == 0.7
        assert IP_ADAPTER_DUAL_SECONDARY_RATIO == 0.3
        assert abs(IP_ADAPTER_DUAL_PRIMARY_RATIO + IP_ADAPTER_DUAL_SECONDARY_RATIO - 1.0) < 0.01
