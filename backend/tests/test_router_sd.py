"""Tests for sd router endpoints (SD WebUI proxy)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi.testclient import TestClient

PATCH_PREFIX = "routers.sd_models"


class TestListSDModels:
    """Test GET /sd/models."""

    @patch(f"{PATCH_PREFIX}.httpx.AsyncClient")
    def test_list_models_success(self, mock_client_cls, client: TestClient):
        """Return model list from SD WebUI."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = [
            {"title": "model_a.safetensors", "model_name": "model_a"},
            {"title": "model_b.safetensors", "model_name": "model_b"},
        ]

        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_instance

        resp = client.get("/api/admin/sd/models")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
        assert len(data["models"]) == 2

    @patch(f"{PATCH_PREFIX}.httpx.AsyncClient")
    def test_list_models_sd_error(self, mock_client_cls, client: TestClient):
        """Return 502 when SD WebUI is unreachable."""
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(side_effect=httpx.HTTPError("Connection refused"))
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_instance

        resp = client.get("/api/admin/sd/models")
        assert resp.status_code == 502


class TestGetSDOptions:
    """Test GET /sd/options."""

    @patch(f"{PATCH_PREFIX}.httpx.AsyncClient")
    def test_get_options_success(self, mock_client_cls, client: TestClient):
        """Return SD options with current model name."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "sd_model_checkpoint": "animagine-xl.safetensors",
            "sd_vae": "auto",
        }

        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_instance

        resp = client.get("/api/admin/sd/options")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model"] == "animagine-xl.safetensors"
        assert "options" in data

    @patch(f"{PATCH_PREFIX}.httpx.AsyncClient")
    def test_get_options_non_dict_response(self, mock_client_cls, client: TestClient):
        """Handle non-dict response from SD WebUI."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = "unexpected"

        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_instance

        resp = client.get("/api/admin/sd/options")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model"] == "Unknown"

    @patch(f"{PATCH_PREFIX}.httpx.AsyncClient")
    def test_get_options_error(self, mock_client_cls, client: TestClient):
        """Return 502 when SD WebUI is unreachable."""
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(side_effect=httpx.HTTPError("timeout"))
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_instance

        resp = client.get("/api/admin/sd/options")
        assert resp.status_code == 502


class TestUpdateSDOptions:
    """Test POST /sd/options."""

    @patch(f"{PATCH_PREFIX}.httpx.AsyncClient")
    def test_update_options_success(self, mock_client_cls, client: TestClient):
        """Update SD model checkpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"sd_model_checkpoint": "new_model.safetensors"}

        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_instance

        resp = client.post("/api/admin/sd/options", json={"sd_model_checkpoint": "new_model.safetensors"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["model"] == "new_model.safetensors"

    @patch(f"{PATCH_PREFIX}.httpx.AsyncClient")
    def test_update_options_error(self, mock_client_cls, client: TestClient):
        """Return 502 when SD WebUI is unreachable."""
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(side_effect=httpx.HTTPError("Connection refused"))
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_instance

        resp = client.post("/api/admin/sd/options", json={"sd_model_checkpoint": "model"})
        assert resp.status_code == 502


class TestListSDLoRAs:
    """Test GET /sd/loras."""

    @patch(f"{PATCH_PREFIX}.httpx.AsyncClient")
    def test_list_loras_success(self, mock_client_cls, client: TestClient):
        """Return LoRA list from SD WebUI."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = [
            {"name": "lora_a", "alias": "lora_a"},
            {"name": "lora_b", "alias": "lora_b"},
        ]

        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_instance

        resp = client.get("/api/admin/sd/loras")
        assert resp.status_code == 200
        data = resp.json()
        assert "loras" in data
        assert len(data["loras"]) == 2

    @patch(f"{PATCH_PREFIX}.httpx.AsyncClient")
    def test_list_loras_non_list_response(self, mock_client_cls, client: TestClient):
        """Handle non-list response gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"error": "unexpected format"}

        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_instance

        resp = client.get("/api/admin/sd/loras")
        assert resp.status_code == 200
        data = resp.json()
        assert data["loras"] == []

    @patch(f"{PATCH_PREFIX}.httpx.AsyncClient")
    def test_list_loras_error(self, mock_client_cls, client: TestClient):
        """Return 502 when SD WebUI is unreachable."""
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(side_effect=httpx.HTTPError("timeout"))
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_instance

        resp = client.get("/api/admin/sd/loras")
        assert resp.status_code == 502
