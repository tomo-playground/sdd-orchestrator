"""Tests for SD Client abstraction layer (SP-077)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from services.sd_client import SDClientBase
from services.sd_client.factory import get_sd_client, reset_sd_client
from services.sd_client.forge import ForgeClient
from services.sd_client.types import SDProgressResult, SDTxt2ImgResult

# ============================================================
# DoD-1: SDClientBase ABC
# ============================================================


class TestSDClientBaseABC:
    """SDClientBase is an ABC that cannot be instantiated directly."""

    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            SDClientBase()  # type: ignore[abstract]

    def test_has_9_abstract_methods(self):
        expected = {
            "txt2img",
            "get_options",
            "set_options",
            "get_models",
            "get_loras",
            "get_progress",
            "controlnet_detect",
            "check_controlnet",
            "get_controlnet_models",
        }
        assert SDClientBase.__abstractmethods__ == expected


class TestSDTxt2ImgResult:
    """SDTxt2ImgResult fields and convenience properties."""

    def test_image_property(self):
        r = SDTxt2ImgResult(images=["img1", "img2"], seed=42)
        assert r.image == "img1"

    def test_image_property_empty(self):
        r = SDTxt2ImgResult(images=[])
        assert r.image == ""

    def test_fields(self):
        r = SDTxt2ImgResult(images=["a"], info={"seed": 1}, seed=1)
        assert r.images == ["a"]
        assert r.info == {"seed": 1}
        assert r.seed == 1


class TestSDProgressResult:
    """SDProgressResult default values."""

    def test_defaults(self):
        r = SDProgressResult()
        assert r.progress == 0.0
        assert r.textinfo == ""
        assert r.current_image is None


# ============================================================
# DoD-2: ForgeClient
# ============================================================


class TestForgeClient:
    """ForgeClient instantiation and method signatures."""

    def test_is_sd_client_base(self):
        client = ForgeClient(base_url="http://test:7860")
        assert isinstance(client, SDClientBase)

    def test_default_base_url_from_config(self):
        client = ForgeClient()
        assert "7860" in client._base_url

    @pytest.mark.asyncio
    async def test_txt2img_returns_result(self):
        sd_response = {
            "images": ["base64img"],
            "info": json.dumps({"seed": 12345}),
        }

        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = lambda: sd_response
        mock_resp.raise_for_status = lambda: None

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_resp
        mock_http.is_closed = False

        with patch("services.sd_client.forge.httpx.AsyncClient", return_value=mock_http):
            client = ForgeClient(base_url="http://test:7860")
            result = await client.txt2img({"prompt": "test"})

            assert isinstance(result, SDTxt2ImgResult)
            assert result.images == ["base64img"]
            assert result.seed == 12345
            assert result.image == "base64img"

    @pytest.mark.asyncio
    async def test_txt2img_timeout_override(self):
        sd_response = {"images": ["img"], "info": "{}"}

        mock_resp = AsyncMock()
        mock_resp.json = lambda: sd_response
        mock_resp.raise_for_status = lambda: None

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_resp
        mock_http.is_closed = False

        with patch("services.sd_client.forge.httpx.AsyncClient", return_value=mock_http):
            client = ForgeClient(base_url="http://test:7860")
            await client.txt2img({"prompt": "test"}, timeout=30.0)

            _, kwargs = mock_http.post.call_args
            assert kwargs["timeout"] == 30.0


# ============================================================
# DoD-3: SD_CLIENT_TYPE config
# ============================================================


class TestSDClientTypeConfig:
    """SD_CLIENT_TYPE env var defaults to 'forge'."""

    def test_default_forge(self):
        from config import SD_CLIENT_TYPE

        assert SD_CLIENT_TYPE == "forge"


# ============================================================
# DoD-4: Factory
# ============================================================


class TestFactory:
    """get_sd_client() returns singleton ForgeClient."""

    def setup_method(self):
        reset_sd_client()

    def teardown_method(self):
        reset_sd_client()

    def test_returns_forge_client(self):
        client = get_sd_client()
        assert isinstance(client, ForgeClient)

    def test_singleton(self):
        a = get_sd_client()
        b = get_sd_client()
        assert a is b

    def test_reset_creates_new(self):
        a = get_sd_client()
        reset_sd_client()
        b = get_sd_client()
        assert a is not b

    def test_invalid_type_raises(self):
        with patch("services.sd_client.factory.SD_CLIENT_TYPE", "unknown"):
            with pytest.raises(ValueError, match="Unknown SD_CLIENT_TYPE"):
                get_sd_client()

    def test_comfy_not_implemented(self):
        with patch("services.sd_client.factory.SD_CLIENT_TYPE", "comfy"):
            with pytest.raises(NotImplementedError, match="SP-022"):
                get_sd_client()


# ============================================================
# DoD-5: Call site conversion verification
# ============================================================


class TestCallSiteConversion:
    """Verify SD direct calls are replaced with get_sd_client()."""

    def test_generation_uses_sd_client(self):
        """generation.py _call_sd_api_raw should use get_sd_client."""
        import inspect

        import services.generation as mod

        source = inspect.getsource(mod._call_sd_api_raw)
        assert "get_sd_client()" in source
        assert "SD_TXT2IMG_URL" not in source

    def test_image_generation_core_uses_sd_client(self):
        """image_generation_core.py should use get_sd_client."""
        import inspect

        import services.image_generation_core as mod

        # _ensure_correct_checkpoint
        source_cp = inspect.getsource(mod._ensure_correct_checkpoint)
        assert "get_sd_client()" in source_cp
        assert "SD_BASE_URL" not in source_cp

        # generate_image_with_v3
        source_gen = inspect.getsource(mod.generate_image_with_v3)
        assert "get_sd_client()" in source_gen
        assert "SD_TXT2IMG_URL" not in source_gen

    def test_avatar_uses_sd_client(self):
        """avatar.py should use get_sd_client."""
        import inspect

        import services.avatar as mod

        source = inspect.getsource(mod.ensure_avatar_file)
        assert "get_sd_client()" in source
        assert "SD_TXT2IMG_URL" not in source

    def test_sd_progress_poller_uses_sd_client(self):
        """sd_progress_poller.py should use get_sd_client."""
        import inspect

        import services.sd_progress_poller as mod

        source = inspect.getsource(mod.poll_sd_progress)
        assert "get_sd_client()" in source

    def test_controlnet_reference_uses_sd_client(self):
        """controlnet.py generate_reference_for_character should use get_sd_client."""
        import inspect

        import services.controlnet as mod

        source = inspect.getsource(mod.generate_reference_for_character)
        assert "get_sd_client()" in source
        assert "httpx" not in source

    def test_router_sd_models_uses_sd_client(self):
        """routers/sd_models.py should use get_sd_client."""
        import inspect

        import routers.sd_models as mod

        source = inspect.getsource(mod)
        assert "get_sd_client()" in source
        assert "SD_MODELS_URL" not in source
        assert "SD_OPTIONS_URL" not in source
        assert "SD_LORAS_URL" not in source
