"""Tests for ComfyUIClient — SDClientBase implementation (SP-022)."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.sd_client import SDClientBase
from services.sd_client.comfyui import ComfyUIClient
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
        assert scheduler == "karras"  # noobaiXL v-pred default

    def test_default_steps_and_cfg(self):
        """steps and cfg_scale defaults used when not in payload."""
        payload = {"prompt": "test"}
        result = ComfyUIClient._payload_to_variables(payload)
        assert result["steps"] == 28
        assert result["cfg"] == 5.5  # noobaiXL v-pred: lower cfg recommended

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


class TestComfyUIClientPayloadNotMutated:
    """txt2img() should not mutate the caller's payload dict (WARNING 4 fix)."""

    @pytest.mark.asyncio
    async def test_payload_not_mutated(self):
        """_comfy_workflow key must remain in caller's dict after txt2img."""
        client = ComfyUIClient(base_url="http://test:8188")
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
