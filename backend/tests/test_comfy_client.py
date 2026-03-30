"""Tests for ComfyUIClient — SDClientBase implementation (SP-022 + SP-115)."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Helper to create async mock for patch.object on async methods
_async_upload = lambda rv: AsyncMock(return_value=rv)  # noqa: E731
_async_mask_pair = lambda c, b: AsyncMock(return_value=(c, b))  # noqa: E731


def _make_client() -> ComfyUIClient:
    """Create ComfyUIClient pre-configured to avoid network calls in tests."""
    client = ComfyUIClient(base_url="http://test:8188")
    client._loras_fetched = True
    client._current_checkpoint = "test_model.safetensors"
    return client


from services.sd_client import SDClientBase
from services.sd_client.comfyui import ComfyUIClient
from services.sd_client.comfyui.workflow_loader import load_workflow
from services.sd_client.types import SDTxt2ImgResult


class TestComfyUIClientInit:
    """ComfyUIClient instantiation and type."""

    def test_is_sd_client_base(self):
        client = ComfyUIClient(base_url="http://test:8188")
        assert isinstance(client, SDClientBase)

    def test_default_base_url(self):
        client = ComfyUIClient()
        assert "8188" in client._base_url

    @pytest.mark.asyncio
    async def test_close(self):
        client = ComfyUIClient(base_url="http://test:8188")
        await client.close()
        assert client._http.is_closed


class TestComfyUIClientTxt2Img:
    """txt2img() — payload conversion + workflow execution."""

    @pytest.mark.asyncio
    async def test_returns_sd_txt2img_result(self):
        """Should return SDTxt2ImgResult with base64 images."""
        fake_img = b"\x89PNG_fake_image"
        fake_b64 = base64.b64encode(fake_img).decode("ascii")

        client = ComfyUIClient(base_url="http://test:8188")

        with (
            patch("services.sd_client.comfyui.load_workflow") as mock_load,
            patch("services.sd_client.comfyui.inject_variables") as mock_inject,
            patch("services.sd_client.comfyui.run_workflow") as mock_run,
        ):
            mock_load.return_value = ({"nodes": {}}, "save_node")
            mock_inject.return_value = {"nodes": {}}
            mock_run.return_value = [fake_img]

            result = await client.txt2img(
                {
                    "prompt": "1girl, solo",
                    "negative_prompt": "lowres",
                    "seed": 42,
                    "_comfy_workflow": "reference",
                }
            )

        assert isinstance(result, SDTxt2ImgResult)
        assert len(result.images) == 1
        assert result.images[0] == fake_b64
        assert result.image == fake_b64
        assert result.info["comfyui"] is True
        assert result.info["workflow"] == "reference"

    @pytest.mark.asyncio
    async def test_default_workflow_is_scene_single(self):
        """When _comfy_workflow not specified, should use scene_single."""
        client = ComfyUIClient(base_url="http://test:8188")

        with (
            patch("services.sd_client.comfyui.load_workflow") as mock_load,
            patch("services.sd_client.comfyui.inject_variables", return_value={}),
            patch("services.sd_client.comfyui.run_workflow", return_value=[b"img"]),
        ):
            mock_load.return_value = ({}, "save")
            await client.txt2img({"prompt": "test"})

            mock_load.assert_called_once_with("scene_single")


class TestPayloadToVariables:
    """_payload_to_variables() — SD WebUI payload to workflow variables."""

    def test_basic_conversion(self):
        payload = {
            "prompt": "1girl, solo",
            "negative_prompt": "lowres",
            "seed": 42,
            "width": 832,
            "height": 1216,
            "steps": 25,
            "cfg_scale": 6.5,
            "sampler_name": "euler",
        }
        result = ComfyUIClient._payload_to_variables(payload)
        assert result["positive"] == "1girl, solo"
        assert result["negative"] == "lowres"
        assert result["seed"] == 42
        assert result["width"] == 832
        assert result["height"] == 1216
        assert result["steps"] == 25
        assert result["cfg"] == 6.5
        assert result["sampler_name"] == "euler"
        assert result["scheduler"] == "karras"  # noobaiXL v-pred default

    def test_sampler_mapping_dpmpp_karras(self):
        """DPM++ 2M + scheduler Karras → ComfyUI dpmpp_2m/karras."""
        payload = {"prompt": "test", "sampler_name": "DPM++ 2M", "scheduler": "Karras"}
        result = ComfyUIClient._payload_to_variables(payload)
        assert result["sampler_name"] == "dpmpp_2m"
        assert result["scheduler"] == "karras"

    def test_sampler_mapping_euler_a(self):
        """Euler a → ComfyUI euler_ancestral."""
        payload = {"prompt": "test", "sampler_name": "Euler a"}
        result = ComfyUIClient._payload_to_variables(payload)
        assert result["sampler_name"] == "euler_ancestral"
        assert result["scheduler"] == "karras"  # noobaiXL v-pred default

    def test_unknown_sampler_fallback(self):
        """Unknown sampler falls back to euler with a warning."""
        from services.sd_client.comfyui import _map_sampler_to_comfy

        sampler, scheduler = _map_sampler_to_comfy("UnknownSampler", None)
        assert sampler == "euler"
        assert scheduler == "karras"  # noobaiXL epsilon default

    def test_default_steps_and_cfg(self):
        """steps and cfg_scale defaults used when not in payload."""
        payload = {"prompt": "test"}
        result = ComfyUIClient._payload_to_variables(payload)
        assert result["steps"] == 28
        assert result["cfg"] == 7.0  # noobaiXL epsilon: standard cfg

    def test_lora_tags_stripped_from_prompt(self):
        """LoRA tags should be removed from the prompt text."""
        payload = {
            "prompt": "1girl, <lora:style:0.7>, solo, <lora:char:1.0>",
            "negative_prompt": "",
        }
        result = ComfyUIClient._payload_to_variables(payload)
        assert "<lora:" not in result["positive"]
        assert "1girl" in result["positive"]
        assert "solo" in result["positive"]

    def test_random_seed_when_minus_one(self):
        """seed=-1 should be replaced with a random seed."""
        payload = {"prompt": "test", "seed": -1}
        result = ComfyUIClient._payload_to_variables(payload)
        assert result["seed"] != -1
        assert 0 <= result["seed"] <= 2**32 - 1


class TestExtractLoraTags:
    """_extract_lora_tags() — parse <lora:name:weight> from prompt."""

    def test_single_lora(self):
        loras = ComfyUIClient._extract_lora_tags("1girl, <lora:anime_style:0.7>, solo")
        assert len(loras) == 1
        assert loras[0]["name"] == "anime_style.safetensors"
        assert loras[0]["weight"] == 0.7

    def test_multiple_loras(self):
        prompt = "<lora:style:0.5>, 1girl, <lora:char:1.0>, <lora:extra:0.3>"
        loras = ComfyUIClient._extract_lora_tags(prompt)
        assert len(loras) == 3
        assert loras[0]["name"] == "style.safetensors"
        assert loras[1]["name"] == "char.safetensors"
        assert loras[2]["name"] == "extra.safetensors"

    def test_no_loras(self):
        loras = ComfyUIClient._extract_lora_tags("1girl, solo, blue_hair")
        assert loras == []

    def test_lora_regex(self):
        """Regex should match standard LoRA tag format."""
        from services.sd_client.comfyui import _LORA_TAG_RE

        assert _LORA_TAG_RE.search("<lora:test_name:0.8>")
        assert _LORA_TAG_RE.search("<lora:MyModel:1.0>")
        assert not _LORA_TAG_RE.search("not a lora tag")


class TestApplyLorasToWorkflow:
    """_apply_loras_to_workflow() — Fat Template LoRA slot assignment."""

    def test_assign_lora_to_slot(self):
        workflow = {
            "lora_1": {
                "class_type": "LoraLoader",
                "inputs": {"lora_name": "placeholder", "strength_model": 0, "strength_clip": 0},
            },
        }
        loras = [{"name": "style.safetensors", "weight": 0.7}]
        result = ComfyUIClient._apply_loras_to_workflow(workflow, loras)
        assert result["lora_1"]["inputs"]["lora_name"] == "style.safetensors"
        assert result["lora_1"]["inputs"]["strength_model"] == 0.7

    def test_unused_slots_zeroed(self):
        workflow = {
            "a_lora": {
                "class_type": "LoraLoader",
                "inputs": {"lora_name": "p", "strength_model": 0.5, "strength_clip": 0.5},
            },
            "b_lora": {
                "class_type": "LoraLoader",
                "inputs": {"lora_name": "p", "strength_model": 0.5, "strength_clip": 0.5},
            },
        }
        loras = [{"name": "only_one.safetensors", "weight": 0.8}]
        result = ComfyUIClient._apply_loras_to_workflow(workflow, loras)
        assert result["a_lora"]["inputs"]["strength_model"] == 0.8
        assert result["b_lora"]["inputs"]["strength_model"] == 0

    def test_more_loras_than_slots(self):
        """Extra LoRAs beyond available slots should be ignored (no crash)."""
        workflow = {
            "lora_1": {
                "class_type": "LoraLoader",
                "inputs": {"lora_name": "p", "strength_model": 0, "strength_clip": 0},
            },
        }
        loras = [
            {"name": "a.safetensors", "weight": 0.7},
            {"name": "b.safetensors", "weight": 0.5},
        ]
        result = ComfyUIClient._apply_loras_to_workflow(workflow, loras)
        assert result["lora_1"]["inputs"]["lora_name"] == "a.safetensors"

    def test_placeholder_lora_bypassed_when_no_fallback(self):
        """placeholder.safetensors should be removed when no fallback LoRA is available (#198)."""
        workflow = {
            "1_cp": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "model.safetensors"},
            },
            "2_lora": {
                "class_type": "LoraLoader",
                "inputs": {
                    "lora_name": "placeholder.safetensors",
                    "strength_model": 0,
                    "strength_clip": 0,
                    "model": ["1_cp", 0],
                    "clip": ["1_cp", 1],
                },
            },
            "3_clip": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": "test", "clip": ["2_lora", 1]},
            },
            "4_sampler": {
                "class_type": "KSampler",
                "inputs": {"model": ["2_lora", 0]},
            },
        }
        loras: list[dict] = []
        result = ComfyUIClient._apply_loras_to_workflow(workflow, loras, available_loras=[])

        # LoRA node should be removed
        assert "2_lora" not in result
        # Downstream nodes should reference the checkpoint directly
        assert result["3_clip"]["inputs"]["clip"] == ["1_cp", 1]
        assert result["4_sampler"]["inputs"]["model"] == ["1_cp", 0]

    def test_placeholder_lora_replaced_when_fallback_available(self):
        """placeholder should be replaced with fallback LoRA, not bypassed."""
        workflow = {
            "1_lora": {
                "class_type": "LoraLoader",
                "inputs": {
                    "lora_name": "placeholder.safetensors",
                    "strength_model": 0,
                    "strength_clip": 0,
                    "model": ["cp", 0],
                    "clip": ["cp", 1],
                },
            },
        }
        result = ComfyUIClient._apply_loras_to_workflow(workflow, [], available_loras=["real_lora.safetensors"])
        # Node should still exist with fallback name
        assert "1_lora" in result
        assert result["1_lora"]["inputs"]["lora_name"] == "real_lora.safetensors"
        assert result["1_lora"]["inputs"]["strength_model"] == 0


class TestResolveCheckpoint:
    """_resolve_checkpoint() — extract from payload sd_model_checkpoint field."""

    def test_from_payload(self):
        payload = {"sd_model_checkpoint": "model.safetensors"}
        assert ComfyUIClient._resolve_checkpoint(payload) == "model.safetensors"

    def test_no_checkpoint(self):
        assert ComfyUIClient._resolve_checkpoint({}) == ""

    @pytest.mark.asyncio
    async def test_fallback_to_current_checkpoint(self):
        """When sd_model_checkpoint missing, _current_checkpoint is used (BLOCKER fix)."""
        client = ComfyUIClient(base_url="http://test:8188")
        client._current_checkpoint = "noob_v1.safetensors"

        captured_workflows: list[dict] = []

        async def fake_run(http, workflow, output_node):
            captured_workflows.append(workflow)
            return [b"fake_image"]

        with (
            patch("services.sd_client.comfyui.load_workflow") as mock_load,
            patch("services.sd_client.comfyui.inject_variables") as mock_inject,
            patch("services.sd_client.comfyui.run_workflow", side_effect=fake_run),
            patch.object(ComfyUIClient, "_set_checkpoint_in_workflow") as mock_set_ckpt,
        ):
            mock_load.return_value = (
                {"1_cp": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "{{checkpoint}}"}}},
                "save",
            )
            mock_inject.return_value = {
                "1_cp": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "{{checkpoint}}"}}
            }

            await client.txt2img({"prompt": "test"})  # No sd_model_checkpoint

        mock_set_ckpt.assert_called_once_with(mock_inject.return_value, "noob_v1.safetensors")


class TestSetCheckpointInWorkflow:
    """_set_checkpoint_in_workflow() — set checkpoint in workflow node."""

    def test_sets_checkpoint(self):
        workflow = {
            "cp": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "old.safetensors"}},
            "other": {"class_type": "KSampler", "inputs": {}},
        }
        ComfyUIClient._set_checkpoint_in_workflow(workflow, "new.safetensors")
        assert workflow["cp"]["inputs"]["ckpt_name"] == "new.safetensors"


class TestComfyUIClientGetModels:
    """get_models() / get_loras() — ComfyUI /object_info API."""

    @pytest.mark.asyncio
    async def test_get_models(self):
        client = ComfyUIClient(base_url="http://test:8188")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "CheckpointLoaderSimple": {"input": {"required": {"ckpt_name": [["model_a.safetensors", "model_b.ckpt"]]}}}
        }
        mock_resp.raise_for_status = MagicMock()
        client._http = AsyncMock()
        client._http.get.return_value = mock_resp

        models = await client.get_models()
        assert len(models) == 2
        assert models[0]["title"] == "model_a.safetensors"
        assert models[0]["model_name"] == "model_a"

    @pytest.mark.asyncio
    async def test_get_loras(self):
        client = ComfyUIClient(base_url="http://test:8188")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "LoraLoader": {"input": {"required": {"lora_name": [["lora_a.safetensors", "lora_b.safetensors"]]}}}
        }
        mock_resp.raise_for_status = MagicMock()
        client._http = AsyncMock()
        client._http.get.return_value = mock_resp

        loras = await client.get_loras()
        assert len(loras) == 2
        assert loras[0]["name"] == "lora_a.safetensors"
        assert loras[0]["alias"] == "lora_a"


class TestComfyUIClientControlnet:
    """ControlNet-related methods."""

    @pytest.mark.asyncio
    async def test_controlnet_detect_raises(self):
        client = ComfyUIClient(base_url="http://test:8188")
        with pytest.raises(NotImplementedError, match="workflow nodes"):
            await client.controlnet_detect({})

    @pytest.mark.asyncio
    async def test_check_controlnet(self):
        client = ComfyUIClient(base_url="http://test:8188")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "ControlNetLoader": {},
            "ControlNetApplyAdvanced": {},
        }
        mock_resp.raise_for_status = MagicMock()
        client._http = AsyncMock()
        client._http.get.return_value = mock_resp

        assert await client.check_controlnet() is True


class TestComfyUIClientHealthCheck:
    """health_check() — verify connectivity and required nodes."""

    @pytest.mark.asyncio
    async def test_healthy(self):
        client = ComfyUIClient(base_url="http://test:8188")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "DynamicThresholdingFull": {},
            "KSampler": {},
            "LoraLoader": {},
            "CheckpointLoaderSimple": {},
        }
        mock_resp.raise_for_status = MagicMock()
        client._http = AsyncMock()
        client._http.get.return_value = mock_resp

        result = await client.health_check()
        assert result["connected"] is True
        assert result["DynamicThresholdingFull"] is True
        assert result["KSampler"] is True

    @pytest.mark.asyncio
    async def test_unreachable(self):
        client = ComfyUIClient(base_url="http://test:8188")
        client._http = AsyncMock()
        client._http.get.side_effect = Exception("connection refused")

        result = await client.health_check()
        assert result["connected"] is False


class TestComfyUIClientGetProgress:
    """get_progress() — queue_remaining is int, not list (WARNING fix)."""

    @pytest.mark.asyncio
    async def test_queue_remaining_int_busy(self):
        """queue_remaining=3 (int) → progress=0.0."""
        client = ComfyUIClient(base_url="http://test:8188")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"exec_info": {"queue_remaining": 3}}
        mock_resp.raise_for_status = MagicMock()
        client._http = AsyncMock()
        client._http.get.return_value = mock_resp

        result = await client.get_progress()
        assert result.progress == 0.0
        assert "3" in result.textinfo

    @pytest.mark.asyncio
    async def test_queue_remaining_zero_idle(self):
        """queue_remaining=0 → progress=1.0."""
        client = ComfyUIClient(base_url="http://test:8188")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"exec_info": {"queue_remaining": 0}}
        mock_resp.raise_for_status = MagicMock()
        client._http = AsyncMock()
        client._http.get.return_value = mock_resp

        result = await client.get_progress()
        assert result.progress == 1.0

    @pytest.mark.asyncio
    async def test_queue_remaining_non_int_defaults_to_zero(self):
        """Non-int queue_remaining treated as 0 (idle)."""
        client = ComfyUIClient(base_url="http://test:8188")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"exec_info": {"queue_remaining": "unexpected_string"}}
        mock_resp.raise_for_status = MagicMock()
        client._http = AsyncMock()
        client._http.get.return_value = mock_resp

        result = await client.get_progress()
        assert result.progress == 1.0


# ── SP-115: Dual IP-Adapter (Background + Character) ────────────────────


class TestWorkflowBgIpAdapterNodes:
    """SP-115 DoD 1: Workflow node structure for dual IP-Adapter."""

    def test_scene_single_bg_ip_adapter_nodes_exist(self):
        """scene_single.json must contain background IP-Adapter nodes."""
        workflow, _ = load_workflow("scene_single")
        assert "15_bg_ip_apply" in workflow
        assert "15_bg_ref_image" in workflow
        assert "15b_bg_mask_image" in workflow
        assert "15c_bg_mask" in workflow
        assert workflow["15_bg_ip_apply"]["class_type"] == "IPAdapterAdvanced"
        assert workflow["15_bg_ref_image"]["class_type"] == "LoadImage"
        assert workflow["15c_bg_mask"]["class_type"] == "ImageToMask"

    def test_scene_single_char_mask_nodes_exist(self):
        """scene_single.json must contain character mask nodes."""
        workflow, _ = load_workflow("scene_single")
        assert "13b_char_mask_image" in workflow
        assert "13b_char_mask" in workflow
        assert workflow["13b_char_mask"]["class_type"] == "ImageToMask"

    def test_scene_single_bg_char_chain(self):
        """Chain: dynthres → 15_bg_ip_apply → 14_ip_apply → 9_sampler."""
        workflow, _ = load_workflow("scene_single")
        # bg_ip_apply takes model from dynthres
        assert workflow["15_bg_ip_apply"]["inputs"]["model"] == ["5_dynthres", 0]
        # char ip_apply takes model from bg_ip_apply (chaining)
        assert workflow["14_ip_apply"]["inputs"]["model"] == ["15_bg_ip_apply", 0]
        # sampler takes model from char ip_apply
        assert workflow["9_sampler"]["inputs"]["model"] == ["14_ip_apply", 0]

    def test_scene_single_attn_mask_connected(self):
        """Both IP-Adapter nodes must have attn_mask inputs."""
        workflow, _ = load_workflow("scene_single")
        assert workflow["14_ip_apply"]["inputs"]["attn_mask"] == ["13b_char_mask", 0]
        assert workflow["15_bg_ip_apply"]["inputs"]["attn_mask"] == ["15c_bg_mask", 0]

    def test_scene_single_shared_ip_model_clip(self):
        """Both IP-Adapter nodes share the same ip_model and clip_vision."""
        workflow, _ = load_workflow("scene_single")
        assert workflow["14_ip_apply"]["inputs"]["ipadapter"] == ["12_ip_model", 0]
        assert workflow["15_bg_ip_apply"]["inputs"]["ipadapter"] == ["12_ip_model", 0]
        assert workflow["14_ip_apply"]["inputs"]["clip_vision"] == ["12b_clip_vision", 0]
        assert workflow["15_bg_ip_apply"]["inputs"]["clip_vision"] == ["12b_clip_vision", 0]

    def test_scene_2p_bg_ip_adapter_nodes_exist(self):
        """scene_2p.json must also contain background IP-Adapter nodes."""
        workflow, _ = load_workflow("scene_2p")
        assert "15_bg_ip_apply" in workflow
        assert "15_bg_ref_image" in workflow
        assert "13b_char_mask_image" in workflow

    def test_scene_2p_bg_char_chain(self):
        """2P: same chain as single — dynthres → bg → char → sampler."""
        workflow, _ = load_workflow("scene_2p")
        assert workflow["15_bg_ip_apply"]["inputs"]["model"] == ["5_dynthres", 0]
        assert workflow["14_ip_apply"]["inputs"]["model"] == ["15_bg_ip_apply", 0]
        assert workflow["9_sampler"]["inputs"]["model"] == ["14_ip_apply", 0]


class TestMaskGeneration:
    """SP-115 DoD 2: Mask generation utilities."""

    def test_character_mask_returns_base64(self):
        """generate_character_mask() should return valid base64 PNG."""
        from services.sd_client.comfyui.mask_utils import generate_character_mask

        b64 = generate_character_mask(832, 1216)
        img_bytes = base64.b64decode(b64)
        assert img_bytes[:4] == b"\x89PNG"

    def test_background_mask_returns_base64(self):
        """generate_background_mask() should return valid base64 PNG."""
        from services.sd_client.comfyui.mask_utils import generate_background_mask

        b64 = generate_background_mask(832, 1216)
        img_bytes = base64.b64decode(b64)
        assert img_bytes[:4] == b"\x89PNG"

    def test_masks_are_complementary(self):
        """Character mask center should be bright, background mask center should be dark."""
        from io import BytesIO

        from PIL import Image

        from services.sd_client.comfyui.mask_utils import generate_background_mask, generate_character_mask

        char_b64 = generate_character_mask(832, 1216)
        bg_b64 = generate_background_mask(832, 1216)

        char_img = Image.open(BytesIO(base64.b64decode(char_b64))).convert("L")
        bg_img = Image.open(BytesIO(base64.b64decode(bg_b64))).convert("L")

        # Center pixel: character mask bright, background mask dark
        cx, cy = 416, 608
        assert char_img.getpixel((cx, cy)) > 200
        assert bg_img.getpixel((cx, cy)) < 55

    @pytest.mark.asyncio
    async def test_mask_caching(self):
        """Same resolution → same cached result (no re-upload)."""
        client = ComfyUIClient(base_url="http://test:8188")
        # Pre-populate cache
        original_cache = ComfyUIClient._mask_cache.copy()
        try:
            client._mask_cache[(832, 1216)] = ("cached_char.png", "cached_bg.png")
            char_fn, bg_fn = await client._upload_mask_pair(832, 1216)
            assert char_fn == "cached_char.png"
            assert bg_fn == "cached_bg.png"
        finally:
            ComfyUIClient._mask_cache.clear()
            ComfyUIClient._mask_cache.update(original_cache)


class TestDualIpAdapterTxt2Img:
    """SP-115 DoD 2: txt2img() with dual IP-Adapter (bg + char)."""

    @pytest.mark.asyncio
    async def test_txt2img_with_bg_and_char(self):
        """Both char and bg active: variables should have both weights and mask filenames."""
        client = _make_client()
        char_b64 = base64.b64encode(b"\x89PNG_char").decode()
        bg_b64 = base64.b64encode(b"\x89PNG_bg").decode()

        with (
            patch("services.sd_client.comfyui.load_workflow") as mock_load,
            patch("services.sd_client.comfyui.inject_variables") as mock_inject,
            patch("services.sd_client.comfyui.run_workflow", return_value=[b"result_img"]),
            patch.object(client, "_upload_image", new=_async_upload("uploaded.png")),
            patch.object(client, "_upload_mask_pair", new=_async_mask_pair("mask_char.png", "mask_bg.png")),
        ):
            mock_load.return_value = ({"9_sampler": {"class_type": "KSampler", "inputs": {}}}, "save")
            mock_inject.return_value = mock_load.return_value[0]

            await client.txt2img(
                {
                    "prompt": "1girl",
                    "_ip_adapter": {
                        "image_b64": char_b64,
                        "name": "testchar",
                        "weight": 0.5,
                        "end_at": 0.4,
                        "bg_image_b64": bg_b64,
                        "bg_weight": 0.2,
                        "bg_end_at": 0.6,
                    },
                }
            )

        variables = mock_inject.call_args[0][1]
        assert variables["ip_adapter_image"] == "uploaded.png"
        assert variables["ip_adapter_weight"] == 0.5
        assert variables["bg_ref_image"] == "uploaded.png"
        assert variables["bg_ip_adapter_weight"] == 0.2
        assert variables["char_mask"] == "mask_char.png"
        assert variables["bg_mask"] == "mask_bg.png"

    @pytest.mark.asyncio
    async def test_txt2img_char_only_bg_bypass(self):
        """Char only: bg_ip_adapter_weight=0.0 (bypass), masks still uploaded."""
        client = _make_client()
        char_b64 = base64.b64encode(b"\x89PNG_char").decode()

        with (
            patch("services.sd_client.comfyui.load_workflow") as mock_load,
            patch("services.sd_client.comfyui.inject_variables") as mock_inject,
            patch("services.sd_client.comfyui.run_workflow", return_value=[b"img"]),
            patch.object(client, "_upload_image", new=_async_upload("uploaded.png")),
            patch.object(client, "_upload_mask_pair", new=_async_mask_pair("mask_char.png", "mask_bg.png")),
        ):
            mock_load.return_value = ({"9_sampler": {"class_type": "KSampler", "inputs": {}}}, "save")
            mock_inject.return_value = mock_load.return_value[0]

            await client.txt2img(
                {
                    "prompt": "1girl",
                    "_ip_adapter": {"image_b64": char_b64, "name": "char", "weight": 0.5, "end_at": 0.4},
                }
            )

        variables = mock_inject.call_args[0][1]
        assert variables["ip_adapter_weight"] == 0.5
        assert variables["bg_ip_adapter_weight"] == 0.0
        assert variables["bg_ref_image"] == "bypass_placeholder.png"
        assert variables["char_mask"] == "mask_char.png"

    @pytest.mark.asyncio
    async def test_txt2img_no_ip_adapter_all_bypass(self):
        """No IP-Adapter: all weights=0.0, placeholders for images and masks."""
        client = _make_client()

        with (
            patch("services.sd_client.comfyui.load_workflow") as mock_load,
            patch("services.sd_client.comfyui.inject_variables") as mock_inject,
            patch("services.sd_client.comfyui.run_workflow", return_value=[b"img"]),
        ):
            mock_load.return_value = ({"9_sampler": {"class_type": "KSampler", "inputs": {}}}, "save")
            mock_inject.return_value = mock_load.return_value[0]

            await client.txt2img({"prompt": "1girl"})

        variables = mock_inject.call_args[0][1]
        assert variables["ip_adapter_weight"] == 0.0
        assert variables["bg_ip_adapter_weight"] == 0.0
        assert variables["ip_adapter_image"] == "bypass_placeholder.png"
        assert variables["bg_ref_image"] == "bypass_placeholder.png"
        assert variables["char_mask"] == "bypass_placeholder.png"
        assert variables["bg_mask"] == "bypass_placeholder.png"

    @pytest.mark.asyncio
    async def test_txt2img_ip_adapter_upload_failure_bypasses(self):
        """When char IP-Adapter image upload fails, should bypass with weight=0."""
        client = _make_client()
        fake_img_b64 = base64.b64encode(b"\x89PNG").decode()

        with (
            patch("services.sd_client.comfyui.load_workflow") as mock_load,
            patch("services.sd_client.comfyui.inject_variables") as mock_inject,
            patch("services.sd_client.comfyui.run_workflow", return_value=[b"img"]),
            patch.object(client, "_upload_image", new=AsyncMock(side_effect=RuntimeError("upload failed"))),
        ):
            mock_load.return_value = ({"9_sampler": {"class_type": "KSampler", "inputs": {}}}, "save")
            mock_inject.return_value = mock_load.return_value[0]

            result = await client.txt2img(
                {
                    "prompt": "1girl",
                    "_ip_adapter": {"image_b64": fake_img_b64, "name": "char"},
                }
            )

        variables = mock_inject.call_args[0][1]
        assert variables["ip_adapter_weight"] == 0.0
        assert isinstance(result, SDTxt2ImgResult)

    @pytest.mark.asyncio
    async def test_txt2img_ip_adapter_weight_clamped(self):
        """Weight should be clamped to max allowed range."""
        client = _make_client()
        fake_img_b64 = base64.b64encode(b"\x89PNG").decode()

        with (
            patch("services.sd_client.comfyui.load_workflow") as mock_load,
            patch("services.sd_client.comfyui.inject_variables") as mock_inject,
            patch("services.sd_client.comfyui.run_workflow", return_value=[b"img"]),
            patch.object(client, "_upload_image", new=_async_upload("ref.png")),
            patch.object(client, "_upload_mask_pair", new=_async_mask_pair("mc.png", "mb.png")),
        ):
            mock_load.return_value = (
                {"9_sampler": {"class_type": "KSampler", "inputs": {"model": ["14_ip_apply", 0]}}},
                "save",
            )
            mock_inject.return_value = mock_load.return_value[0]

            await client.txt2img(
                {
                    "prompt": "test",
                    "_ip_adapter": {"image_b64": fake_img_b64, "weight": 1.5},
                }
            )

        variables = mock_inject.call_args[0][1]
        # DEFAULT_IP_ADAPTER_WEIGHT_VPRED is the max
        from config import DEFAULT_IP_ADAPTER_WEIGHT_VPRED

        assert variables["ip_adapter_weight"] == DEFAULT_IP_ADAPTER_WEIGHT_VPRED


class TestIpAdapterWorkflowIntegration:
    """IP-Adapter workflow node presence and chain (SP-113 DoD 1/4, updated for SP-115)."""

    def test_scene_single_ip_adapter_nodes_exist(self):
        """scene_single.json should contain IP-Adapter core nodes."""
        workflow, _ = load_workflow("scene_single")
        assert "12_ip_model" in workflow
        assert "13_ip_image" in workflow
        assert "14_ip_apply" in workflow
        assert workflow["12_ip_model"]["class_type"] == "IPAdapterModelLoader"
        assert workflow["13_ip_image"]["class_type"] == "LoadImage"
        assert workflow["14_ip_apply"]["class_type"] == "IPAdapterAdvanced"

    def test_scene_single_ip_adapter_chain(self):
        """14_ip_apply should feed into 9_sampler model input, chained through bg."""
        workflow, _ = load_workflow("scene_single")
        assert workflow["9_sampler"]["inputs"]["model"] == ["14_ip_apply", 0]
        assert workflow["14_ip_apply"]["inputs"]["model"] == ["15_bg_ip_apply", 0]

    def test_scene_2p_ip_adapter_nodes_exist(self):
        """scene_2p.json should contain IP-Adapter nodes."""
        workflow, _ = load_workflow("scene_2p")
        assert "12_ip_model" in workflow
        assert "13_ip_image" in workflow
        assert "14_ip_apply" in workflow

    def test_scene_2p_ip_adapter_chain(self):
        """2P: sampler model → 14_ip_apply, ControlNet on conditioning (independent)."""
        workflow, _ = load_workflow("scene_2p")
        assert workflow["9_sampler"]["inputs"]["model"] == ["14_ip_apply", 0]
        assert workflow["9_sampler"]["inputs"]["positive"] == ["7_cn_apply", 0]


class TestComfyUIClientPayloadNotMutated:
    """txt2img() should not mutate the caller's payload dict (WARNING 4 fix)."""

    @pytest.mark.asyncio
    async def test_payload_not_mutated(self):
        """_comfy_workflow key must remain in caller's dict after txt2img."""
        client = _make_client()
        payload = {"prompt": "test", "_comfy_workflow": "reference", "seed": 42}
        original_keys = set(payload.keys())

        with (
            patch("services.sd_client.comfyui.load_workflow") as mock_load,
            patch("services.sd_client.comfyui.inject_variables", return_value={}),
            patch("services.sd_client.comfyui.run_workflow", return_value=[b"img"]),
        ):
            mock_load.return_value = ({}, "save")
            await client.txt2img(payload)

        assert set(payload.keys()) == original_keys
        assert payload["_comfy_workflow"] == "reference"

    @pytest.mark.asyncio
    async def test_ip_adapter_key_not_removed_from_caller(self):
        """_ip_adapter key must remain in caller's dict after txt2img (retry safety)."""
        client = _make_client()
        fake_img_b64 = base64.b64encode(b"\x89PNG").decode()
        payload = {
            "prompt": "test",
            "_ip_adapter": {"image_b64": fake_img_b64, "name": "char", "weight": 0.5, "end_at": 0.7},
        }

        with (
            patch("services.sd_client.comfyui.load_workflow") as mock_load,
            patch("services.sd_client.comfyui.inject_variables", return_value={}),
            patch("services.sd_client.comfyui.run_workflow", return_value=[b"img"]),
            patch.object(client, "_upload_image", new=_async_upload("ip_ref_char_abc123.png")),
            patch.object(client, "_upload_mask_pair", new=_async_mask_pair("mc.png", "mb.png")),
        ):
            mock_load.return_value = ({}, "save")
            await client.txt2img(payload)

        assert "_ip_adapter" in payload
        assert payload["_ip_adapter"]["name"] == "char"


class TestIpAdapterUniqueFilename:
    """IP-Adapter upload filename should be unique per image content."""

    @pytest.mark.asyncio
    async def test_different_images_get_different_filenames(self):
        """Two requests with different images should use different filenames."""
        client = _make_client()
        img_a = base64.b64encode(b"\x89PNG_image_A").decode()
        img_b = base64.b64encode(b"\x89PNG_image_B").decode()

        uploaded_filenames: list[str] = []

        async def capture_upload(image_b64: str, filename: str) -> str:
            uploaded_filenames.append(filename)
            return filename

        for img in [img_a, img_b]:
            with (
                patch("services.sd_client.comfyui.load_workflow") as mock_load,
                patch("services.sd_client.comfyui.inject_variables", return_value={}),
                patch("services.sd_client.comfyui.run_workflow", return_value=[b"out"]),
                patch.object(client, "_upload_image", new=AsyncMock(side_effect=capture_upload)),
                patch.object(client, "_upload_mask_pair", new=_async_mask_pair("mc.png", "mb.png")),
            ):
                mock_load.return_value = ({}, "save")
                await client.txt2img(
                    {"prompt": "test", "_ip_adapter": {"image_b64": img, "name": "char", "weight": 0.5, "end_at": 0.7}}
                )

        assert len(uploaded_filenames) == 2
        assert uploaded_filenames[0] != uploaded_filenames[1]
        assert uploaded_filenames[0].startswith("ip_ref_char_")
        assert uploaded_filenames[1].startswith("ip_ref_char_")

    @pytest.mark.asyncio
    async def test_same_image_gets_same_filename(self):
        """Same image content should produce the same filename (cache-friendly)."""
        client = _make_client()
        img = base64.b64encode(b"\x89PNG_same_image").decode()

        uploaded_filenames: list[str] = []

        async def capture_upload(image_b64: str, filename: str) -> str:
            uploaded_filenames.append(filename)
            return filename

        for _ in range(2):
            with (
                patch("services.sd_client.comfyui.load_workflow") as mock_load,
                patch("services.sd_client.comfyui.inject_variables", return_value={}),
                patch("services.sd_client.comfyui.run_workflow", return_value=[b"out"]),
                patch.object(client, "_upload_image", new=AsyncMock(side_effect=capture_upload)),
                patch.object(client, "_upload_mask_pair", new=_async_mask_pair("mc.png", "mb.png")),
            ):
                mock_load.return_value = ({}, "save")
                await client.txt2img(
                    {"prompt": "test", "_ip_adapter": {"image_b64": img, "name": "char", "weight": 0.5, "end_at": 0.7}}
                )

        assert len(uploaded_filenames) == 2
        assert uploaded_filenames[0] == uploaded_filenames[1]
