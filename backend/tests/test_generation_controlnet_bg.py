"""Tests for SP-115: Background IP-Adapter in generation_controlnet.py."""

from __future__ import annotations

import base64
import os
import tempfile
from unittest.mock import MagicMock, patch

from services.generation_controlnet import _inject_ip_adapter_payload, _load_bg_reference


class TestLoadBgReference:
    """_load_bg_reference() — background reference image loading."""

    def test_no_environment_reference_id(self):
        """Should return None when no environment_reference_id."""
        req = MagicMock()
        req.environment_reference_id = None
        db = MagicMock()
        assert _load_bg_reference(req, db) is None

    def test_asset_not_found(self):
        """Should return None when MediaAsset not in DB."""
        req = MagicMock()
        req.environment_reference_id = 42
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        assert _load_bg_reference(req, db) is None

    def test_asset_file_missing(self):
        """Should return None when asset file doesn't exist on disk."""
        req = MagicMock()
        req.environment_reference_id = 42
        asset = MagicMock()
        asset.local_path = "/nonexistent/path/image.png"
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = asset
        assert _load_bg_reference(req, db) is None

    def test_asset_loaded_as_base64(self):
        """Should return base64-encoded file content."""
        req = MagicMock()
        req.environment_reference_id = 42
        content = b"\x89PNG_test_bg_image"

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name

        try:
            asset = MagicMock()
            asset.local_path = tmp_path
            db = MagicMock()
            db.query.return_value.filter.return_value.first.return_value = asset

            result = _load_bg_reference(req, db)
            assert result == base64.b64encode(content).decode("utf-8")
        finally:
            os.unlink(tmp_path)


class TestInjectIpAdapterPayload:
    """_inject_ip_adapter_payload() — combining char + bg IP-Adapter payload."""

    def test_char_only_no_bg(self):
        """When only char IP-Adapter, payload should contain char data without bg."""
        payload: dict = {}
        ctx = MagicMock()
        ctx._ip_adapter_payload = {"image_b64": "chardata", "name": "char", "weight": 0.5, "end_at": 0.4}
        req = MagicMock()
        req.environment_reference_id = None
        db = MagicMock()

        _inject_ip_adapter_payload(payload, ctx, req, db)

        assert "_ip_adapter" in payload
        assert payload["_ip_adapter"]["image_b64"] == "chardata"
        assert "bg_image_b64" not in payload["_ip_adapter"]

    @patch("services.generation_controlnet._load_bg_reference")
    def test_char_plus_bg(self, mock_load_bg):
        """When both char and bg available, payload should contain both."""
        mock_load_bg.return_value = "bg_base64_data"
        payload: dict = {}
        ctx = MagicMock()
        ctx._ip_adapter_payload = {"image_b64": "chardata"}
        req = MagicMock()
        req.environment_reference_id = 99
        db = MagicMock()

        with patch("config.BG_IP_ADAPTER_ENABLED", True):
            _inject_ip_adapter_payload(payload, ctx, req, db)

        assert payload["_ip_adapter"]["image_b64"] == "chardata"
        assert payload["_ip_adapter"]["bg_image_b64"] == "bg_base64_data"
        assert payload["_ip_adapter"]["bg_weight"] > 0

    @patch("services.generation_controlnet._load_bg_reference")
    def test_bg_only_no_char(self, mock_load_bg):
        """When no char IP-Adapter but bg available, should still inject bg."""
        mock_load_bg.return_value = "bg_base64_data"
        payload: dict = {}
        ctx = MagicMock()
        ctx._ip_adapter_payload = None
        req = MagicMock()
        req.environment_reference_id = 99
        db = MagicMock()

        with patch("config.BG_IP_ADAPTER_ENABLED", True):
            _inject_ip_adapter_payload(payload, ctx, req, db)

        assert "_ip_adapter" in payload
        assert payload["_ip_adapter"]["bg_image_b64"] == "bg_base64_data"
        assert "image_b64" not in payload["_ip_adapter"]

    @patch("services.generation_controlnet._load_bg_reference")
    def test_bg_disabled_by_config(self, mock_load_bg):
        """When BG_IP_ADAPTER_ENABLED=False, should not inject bg."""
        mock_load_bg.return_value = "bg_base64_data"
        payload: dict = {}
        ctx = MagicMock()
        ctx._ip_adapter_payload = {"image_b64": "chardata"}
        req = MagicMock()
        req.environment_reference_id = 99
        db = MagicMock()

        with patch("config.BG_IP_ADAPTER_ENABLED", False):
            _inject_ip_adapter_payload(payload, ctx, req, db)

        assert "bg_image_b64" not in payload.get("_ip_adapter", {})

    def test_no_char_no_bg(self):
        """When neither char nor bg, payload should not have _ip_adapter key."""
        payload: dict = {}
        ctx = MagicMock()
        ctx._ip_adapter_payload = None
        req = MagicMock()
        req.environment_reference_id = None
        db = MagicMock()

        _inject_ip_adapter_payload(payload, ctx, req, db)

        assert "_ip_adapter" not in payload
