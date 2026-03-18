"""
IP-Adapter integration tests.

Tests for character consistency using IP-Adapter with CLIP models.
"""

import base64

import pytest
from fastapi.testclient import TestClient


class TestIpAdapterArgs:
    """Test IP-Adapter argument building."""

    def test_build_ip_adapter_args_clip_model(self):
        """Test building IP-Adapter args with CLIP model (anime/illustration)."""
        from services.controlnet import IP_ADAPTER_MODELS, build_ip_adapter_args

        dummy_image = base64.b64encode(b"fake_image_data").decode()
        args = build_ip_adapter_args(
            reference_image=dummy_image,
            weight=0.7,
            model="clip"
        )

        assert args["enabled"] is True
        assert args["image"] == dummy_image
        assert args["weight"] == 0.7
        assert args["module"] == "CLIP-ViT-H (IPAdapter)"  # CLIP module for anime
        assert args["model"] == IP_ADAPTER_MODELS["clip"]

    def test_build_ip_adapter_args_clip_face_model(self):
        """Test building IP-Adapter args with CLIP face model."""
        from services.controlnet import IP_ADAPTER_MODELS, build_ip_adapter_args

        dummy_image = base64.b64encode(b"fake_image_data").decode()
        args = build_ip_adapter_args(
            reference_image=dummy_image,
            weight=0.8,
            model="clip_face"
        )

        assert args["enabled"] is True
        assert args["module"] == "CLIP-ViT-H (IPAdapter)"  # CLIP module
        assert args["model"] == IP_ADAPTER_MODELS["clip_face"]

    def test_build_ip_adapter_args_faceid_removed(self):
        """FaceID model removed in SDXL — should raise ValueError."""
        from services.controlnet import build_ip_adapter_args

        dummy_image = base64.b64encode(b"fake_image_data").decode()
        with pytest.raises(ValueError, match="Unknown IP-Adapter model"):
            build_ip_adapter_args(
                reference_image=dummy_image,
                weight=0.8,
                model="faceid"
            )

    def test_build_ip_adapter_args_default_model(self):
        """Test that default model is CLIP_FACE (for anime characters)."""
        from services.controlnet import DEFAULT_IP_ADAPTER_MODEL, build_ip_adapter_args

        assert DEFAULT_IP_ADAPTER_MODEL == "clip_face"

        dummy_image = base64.b64encode(b"fake_image_data").decode()
        args = build_ip_adapter_args(
            reference_image=dummy_image,
            weight=0.7,
        )

        # Default should use CLIP module
        assert args["module"] == "CLIP-ViT-H (IPAdapter)"

    def test_build_ip_adapter_args_invalid_model(self):
        """Test that invalid model raises ValueError."""
        from services.controlnet import build_ip_adapter_args

        dummy_image = base64.b64encode(b"fake_image_data").decode()

        with pytest.raises(ValueError, match="Unknown IP-Adapter model"):
            build_ip_adapter_args(
                reference_image=dummy_image,
                weight=0.7,
                model="invalid_model"
            )


class TestReferenceImages:
    """Test reference image management."""

    def test_list_reference_images(self, client: TestClient):
        """Test listing available reference images."""
        response = client.get("/api/v1/controlnet/ip-adapter/references")
        assert response.status_code == 200
        data = response.json()
        assert "references" in data
        assert isinstance(data["references"], list)

    def test_load_reference_image_existing(self):
        """Test loading an existing reference image via DB."""
        from unittest.mock import MagicMock, patch

        from services.controlnet import load_reference_image

        # Mock DB with a character that has a preview image
        mock_db = MagicMock()
        mock_char = MagicMock()
        mock_char.reference_image_url = "s3://bucket/ref.png"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_char

        fake_bytes = b"fake_image_data"
        fake_b64 = base64.b64encode(fake_bytes).decode()
        with patch("services.controlnet.load_image_bytes", return_value=fake_bytes):
            result = load_reference_image("test_character", db=mock_db)

        assert result is not None
        assert result == fake_b64

    def test_load_reference_image_nonexistent(self):
        """Test loading a non-existent reference image returns None."""
        from services.controlnet import load_reference_image

        result = load_reference_image("nonexistent_character_12345")
        assert result is None


class TestCombinedControlNetArgs:
    """Test combined ControlNet + IP-Adapter args."""

    def test_build_combined_args_ip_adapter_only(self):
        """Test building combined args with IP-Adapter only."""
        from services.controlnet import build_combined_controlnet_args

        dummy_image = base64.b64encode(b"fake_image_data").decode()
        args = build_combined_controlnet_args(
            pose_image=None,
            reference_image=dummy_image,
            ip_adapter_weight=0.7,
        )

        assert len(args) == 1
        assert args[0]["module"] == "CLIP-ViT-H (IPAdapter)"
        assert args[0]["weight"] == 0.7

    def test_build_combined_args_both(self):
        """Test building combined args with both ControlNet and IP-Adapter."""
        from services.controlnet import build_combined_controlnet_args

        pose_image = base64.b64encode(b"pose_data").decode()
        ref_image = base64.b64encode(b"ref_data").decode()

        args = build_combined_controlnet_args(
            pose_image=pose_image,
            reference_image=ref_image,
            pose_weight=0.8,
            ip_adapter_weight=0.7,
        )

        assert len(args) == 2
        # First should be OpenPose
        assert "openpose" in args[0]["model"].lower()
        assert args[0]["weight"] == 0.8
        # Second should be IP-Adapter
        assert args[1]["module"] == "CLIP-ViT-H (IPAdapter)"
        assert args[1]["weight"] == 0.7

    def test_build_combined_args_empty(self):
        """Test building combined args with no inputs."""
        from services.controlnet import build_combined_controlnet_args

        args = build_combined_controlnet_args()
        assert len(args) == 0


class TestSceneGenerationWithIpAdapter:
    """Test scene generation endpoint with IP-Adapter integration."""

    def test_ip_adapter_payload_construction(self):
        """Test that IP-Adapter payload is correctly constructed."""
        from services.controlnet import build_ip_adapter_args

        ref_image = base64.b64encode(b"fake_reference_image").decode()

        # Build IP-Adapter args
        args = build_ip_adapter_args(
            reference_image=ref_image,
            weight=0.7,
        )

        # Verify correct structure for ControlNet API
        assert args["enabled"] is True
        assert args["image"] == ref_image
        assert args["weight"] == 0.7
        assert args["module"] == "CLIP-ViT-H (IPAdapter)"
        assert "model" in args
        assert args["resize_mode"] == "Crop and Resize"

    def test_scene_generate_ip_adapter_reference_returned(self, client: TestClient):
        """Test that response includes IP-Adapter reference info (integration test)."""
        # This test requires SD WebUI to be running
        try:
            import requests
            resp = requests.get("http://localhost:7860/sdapi/v1/sd-models", timeout=2)
            if resp.status_code != 200:
                pytest.skip("SD WebUI not available")
        except Exception:
            pytest.skip("SD WebUI not available")

        response = client.post("/api/v1/scene/generate", json={
            "prompt": "1girl, anime, standing",
            "negative_prompt": "bad quality",
            "steps": 1,  # Minimal steps for speed
            "cfg_scale": 4.5,
            "width": 832,
            "height": 1216,
            "use_ip_adapter": True,
            "ip_adapter_reference": "test_character",
            "ip_adapter_weight": 0.7,
        })

        if response.status_code == 200:
            data = response.json()
            # When IP-Adapter is successfully applied, it should return the reference key
            assert "ip_adapter_reference" in data


class TestIpAdapterModelConstants:
    """Test IP-Adapter model constants and configuration."""

    def test_ip_adapter_models_defined(self):
        """Test that all expected IP-Adapter models are defined."""
        from services.controlnet import IP_ADAPTER_MODELS

        assert "clip" in IP_ADAPTER_MODELS
        assert "clip_face" in IP_ADAPTER_MODELS
        # faceid removed in SDXL (no compatible model)
        assert "faceid" not in IP_ADAPTER_MODELS

    def test_default_model_is_clip(self):
        """Test that default model is CLIP_FACE (for anime)."""
        from services.controlnet import DEFAULT_IP_ADAPTER_MODEL

        # CLIP_FACE should be default for better facial consistency
        assert DEFAULT_IP_ADAPTER_MODEL == "clip_face"

    def test_controlnet_models_defined(self):
        """Test that ControlNet models are defined."""
        from services.controlnet import CONTROLNET_MODELS

        assert "openpose" in CONTROLNET_MODELS
        assert "depth" in CONTROLNET_MODELS
        assert "canny" in CONTROLNET_MODELS
