"""Tests for controlnet router endpoints."""

from unittest.mock import patch

from fastapi.testclient import TestClient

# Patch targets are in routers.controlnet (imported from services.controlnet)
PATCH_PREFIX = "routers.controlnet"


class TestControlNetStatus:
    """Test GET /controlnet/status."""

    @patch(f"{PATCH_PREFIX}.get_controlnet_models", return_value=["openpose", "depth"])
    @patch(f"{PATCH_PREFIX}.check_controlnet_available", return_value=True)
    def test_status_available(self, mock_check, mock_models, client: TestClient):
        """Return available status with models."""
        resp = client.get("/api/admin/controlnet/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is True
        assert "openpose" in data["models"]
        assert isinstance(data["pose_references"], list)

    @patch(f"{PATCH_PREFIX}.check_controlnet_available", return_value=False)
    def test_status_unavailable(self, mock_check, client: TestClient):
        """Return unavailable status with empty models."""
        resp = client.get("/api/admin/controlnet/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is False
        assert data["models"] == []


class TestPoses:
    """Test pose-related endpoints."""

    @patch(f"{PATCH_PREFIX}.load_pose_reference")
    def test_list_poses(self, mock_load, client: TestClient):
        """List available pose references."""
        mock_load.return_value = "base64data"
        resp = client.get("/api/admin/controlnet/poses")
        assert resp.status_code == 200
        data = resp.json()
        assert "poses" in data
        assert len(data["poses"]) > 0
        # All items have required keys
        for pose in data["poses"]:
            assert "name" in pose
            assert "filename" in pose
            assert "available" in pose

    @patch(f"{PATCH_PREFIX}.load_pose_reference", return_value="base64posedata")
    def test_get_pose_reference(self, mock_load, client: TestClient):
        """Get a specific pose reference image."""
        resp = client.get("/api/admin/controlnet/pose/standing")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pose_name"] == "standing"
        assert data["image_b64"] == "base64posedata"

    @patch(f"{PATCH_PREFIX}.load_pose_reference", return_value=None)
    def test_get_pose_not_found(self, mock_load, client: TestClient):
        """Return 404 for non-existent pose."""
        resp = client.get("/api/admin/controlnet/pose/nonexistent_pose")
        assert resp.status_code == 404


class TestDetectPose:
    """Test POST /controlnet/detect-pose."""

    @patch(f"{PATCH_PREFIX}.create_pose_from_image")
    def test_detect_pose_success(self, mock_create, client: TestClient):
        """Successfully detect a pose from image."""
        mock_create.return_value = {"images": ["pose_skeleton_b64"]}
        resp = client.post("/api/admin/controlnet/detect-pose", json={"image_b64": "test_image_data"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["pose_image"] == "pose_skeleton_b64"

    @patch(f"{PATCH_PREFIX}.create_pose_from_image")
    def test_detect_pose_no_result(self, mock_create, client: TestClient):
        """Return failure when no pose detected."""
        mock_create.return_value = {"images": []}
        resp = client.post("/api/admin/controlnet/detect-pose", json={"image_b64": "test_image_data"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False

    @patch(f"{PATCH_PREFIX}.create_pose_from_image", side_effect=Exception("SD WebUI connection failed"))
    def test_detect_pose_error(self, mock_create, client: TestClient):
        """Return error on SD WebUI failure."""
        resp = client.post("/api/admin/controlnet/detect-pose", json={"image_b64": "test_image_data"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "error" in data


class TestSuggestPose:
    """Test POST /controlnet/suggest-pose."""

    @patch(f"{PATCH_PREFIX}.load_pose_reference", return_value="pose_b64")
    @patch(f"{PATCH_PREFIX}.detect_pose_from_prompt", return_value="standing")
    def test_suggest_pose_found(self, mock_detect, mock_load, client: TestClient):
        """Suggest a pose based on prompt tags."""
        resp = client.post("/api/admin/controlnet/suggest-pose", json=["standing", "1girl"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["suggested_pose"] == "standing"
        assert data["available"] is True
        assert data["image_b64"] == "pose_b64"

    @patch(f"{PATCH_PREFIX}.detect_pose_from_prompt", return_value=None)
    def test_suggest_pose_none(self, mock_detect, client: TestClient):
        """Return no suggestion when no pose matches."""
        resp = client.post("/api/admin/controlnet/suggest-pose", json=["abstract", "background"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["suggested_pose"] is None
        assert data["available"] is False


class TestIPAdapterStatus:
    """Test GET /controlnet/ip-adapter/status."""

    @patch(f"{PATCH_PREFIX}.get_controlnet_models", return_value=["ip-adapter-plus-face_sdxl_vit-h", "openpose"])
    @patch(f"{PATCH_PREFIX}.check_controlnet_available", return_value=True)
    def test_ip_adapter_available(self, mock_check, mock_models, client: TestClient):
        """Return IP-Adapter availability."""
        resp = client.get("/api/admin/controlnet/ip-adapter/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is True
        assert len(data["models"]) == 1  # Only ip-adapter model
        assert "ip-adapter" in data["models"][0]

    @patch(f"{PATCH_PREFIX}.get_controlnet_models", return_value=["openpose"])
    @patch(f"{PATCH_PREFIX}.check_controlnet_available", return_value=True)
    def test_ip_adapter_no_models(self, mock_check, mock_models, client: TestClient):
        """IP-Adapter unavailable when no matching models."""
        resp = client.get("/api/admin/controlnet/ip-adapter/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is False


class TestIPAdapterReferences:
    """Test IP-Adapter reference image endpoints."""

    @patch(f"{PATCH_PREFIX}.list_reference_images")
    def test_list_references(self, mock_list, client: TestClient, db_session):
        """List reference images."""
        mock_list.return_value = [
            {"character_key": "hana", "filename": "hana.png"},
        ]
        resp = client.get("/api/v1/controlnet/ip-adapter/references")
        assert resp.status_code == 200
        data = resp.json()
        assert "references" in data
        assert len(data["references"]) == 1
        assert data["references"][0]["character_key"] == "hana"
        assert "preset" in data["references"][0]

    @patch(f"{PATCH_PREFIX}.save_reference_image", return_value="hana.png")
    def test_upload_reference(self, mock_save, client: TestClient):
        """Upload a reference image."""
        resp = client.post(
            "/api/admin/controlnet/ip-adapter/reference",
            json={
                "character_key": "hana",
                "image_b64": "fake_base64_data",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["character_key"] == "hana"

    @patch(f"{PATCH_PREFIX}.save_reference_image", side_effect=Exception("Disk full"))
    def test_upload_reference_error(self, mock_save, client: TestClient):
        """Handle upload error gracefully."""
        resp = client.post(
            "/api/admin/controlnet/ip-adapter/reference",
            json={
                "character_key": "hana",
                "image_b64": "fake_base64_data",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "error" in data

    @patch(f"{PATCH_PREFIX}.load_reference_image", return_value="ref_b64_data")
    def test_get_reference(self, mock_load, client: TestClient):
        """Get a reference image as JSON."""
        resp = client.get("/api/admin/controlnet/ip-adapter/reference/hana")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["image_b64"] == "ref_b64_data"

    @patch(f"{PATCH_PREFIX}.load_reference_image", return_value=None)
    def test_get_reference_not_found(self, mock_load, client: TestClient):
        """Return failure when reference not found."""
        resp = client.get("/api/admin/controlnet/ip-adapter/reference/nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False

    @patch(f"{PATCH_PREFIX}.delete_reference_image", return_value=True)
    def test_delete_reference(self, mock_del, client: TestClient):
        """Delete a reference image."""
        resp = client.delete("/api/admin/controlnet/ip-adapter/reference/hana")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] == "hana"

    @patch(f"{PATCH_PREFIX}.delete_reference_image", return_value=False)
    def test_delete_reference_not_found(self, mock_del, client: TestClient):
        """Return 404 when reference not found."""
        resp = client.delete("/api/admin/controlnet/ip-adapter/reference/nonexistent")
        assert resp.status_code == 404
