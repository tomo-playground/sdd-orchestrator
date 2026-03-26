"""Tests for SP-023: 2P ControlNet Pose + BREAK pipeline.

Covers: scene_2p.json workflow, ComfyUI pose upload/cache,
2P pose mapping, generation.py workflow selection, generation_controlnet.py 2P pose application.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.sd_client.comfyui import ComfyUIClient

# ── Stubs ──────────────────────────────────────────────────────────────


@dataclass
class FakeRequest:
    use_controlnet: bool = False
    controlnet_pose: str | None = None
    controlnet_weight: float = 1.0
    controlnet_control_mode: str = "Balanced"
    character_id: int | None = None
    character_b_id: int | None = None
    scene_id: int | None = None
    prompt: str = ""
    comfy_workflow: str | None = None
    environment_reference_id: int | None = None


@dataclass
class FakeStrategy:
    ip_adapter_enabled: bool = False
    ip_adapter_reference: str | None = None
    ip_adapter_weight: float = 0.7
    ip_adapter_model: str = "NOOB-IPA-MARK1"
    ip_adapter_guidance_start: float | None = None
    ip_adapter_guidance_end: float | None = None
    reference_only_enabled: bool = False
    reference_only_weight: float = 0.5
    quality_score: str = "medium"


@dataclass
class FakeContext:
    request: FakeRequest = field(default_factory=FakeRequest)
    consistency: FakeStrategy = field(default_factory=FakeStrategy)
    prompt: str = ""
    negative_prompt: str = ""
    character_name: str | None = None
    character_b_id: int | None = None
    controlnet_used: str | None = None
    ip_adapter_used: str | None = None
    warnings: list[str] = field(default_factory=list)
    steps: int = 28
    cfg_scale: float = 5.5
    style_context: object = None


# ── B-1: scene_2p.json Workflow ────────────────────────────────────────


class TestScene2pWorkflow:
    """Validate scene_2p.json structure and required nodes."""

    def _load_workflow(self) -> dict:
        from services.sd_client.comfyui.workflow_loader import load_workflow

        workflow, output_node = load_workflow("scene_2p")
        return workflow

    def test_load_scene_2p(self):
        """scene_2p.json should load without errors."""
        workflow = self._load_workflow()
        assert isinstance(workflow, dict)
        assert len(workflow) > 0

    def test_has_controlnet_nodes(self):
        """Must contain ControlNetLoader, LoadImage, ControlNetApplyAdvanced."""
        workflow = self._load_workflow()
        class_types = {n.get("class_type") for n in workflow.values()}
        assert "ControlNetLoader" in class_types
        assert "LoadImage" in class_types
        assert "ControlNetApplyAdvanced" in class_types

    def test_has_dynamic_thresholding(self):
        workflow = self._load_workflow()
        dynthres_nodes = [n for n in workflow.values() if n.get("class_type") == "DynamicThresholdingFull"]
        assert len(dynthres_nodes) == 1
        inputs = dynthres_nodes[0]["inputs"]
        assert inputs["mimic_scale"] == 5.0
        assert inputs["scaling_startpoint"] == "MEAN"
        assert inputs["variability_measure"] == "AD"

    def test_has_lora_3_slots(self):
        workflow = self._load_workflow()
        lora_nodes = [n for n in workflow.values() if n.get("class_type") == "LoraLoader"]
        assert len(lora_nodes) == 3

    def test_pose_image_variable(self):
        """LoadImage node must use {{pose_image}} variable."""
        workflow = self._load_workflow()
        load_img_nodes = [n for n in workflow.values() if n.get("class_type") == "LoadImage"]
        assert len(load_img_nodes) == 1
        assert load_img_nodes[0]["inputs"]["image"] == "{{pose_image}}"

    def test_controlnet_strength_variable(self):
        """ControlNetApplyAdvanced must use {{controlnet_strength}} variable."""
        workflow = self._load_workflow()
        cn_apply = [n for n in workflow.values() if n.get("class_type") == "ControlNetApplyAdvanced"]
        assert len(cn_apply) == 1
        assert cn_apply[0]["inputs"]["strength"] == "{{controlnet_strength}}"

    def test_inject_variables_replaces_pose(self):
        """inject_variables should replace pose_image and controlnet_strength."""
        from services.sd_client.comfyui.workflow_loader import inject_variables, load_workflow

        workflow, _ = load_workflow("scene_2p")
        variables = {
            "positive": "1girl, 1boy, walking",
            "negative": "lowres",
            "seed": 42,
            "width": 832,
            "height": 1216,
            "steps": 28,
            "cfg": 5.5,
            "sampler_name": "dpmpp_2m",
            "scheduler": "karras",
            "pose_image": "2p_walking_together.png",
            "controlnet_strength": 0.7,
        }
        result = inject_variables(workflow, variables)
        raw = json.dumps(result)
        assert "{{pose_image}}" not in raw
        assert "{{controlnet_strength}}" not in raw
        assert "2p_walking_together.png" in raw

    def test_scene_single_unchanged(self):
        """scene_single.json must not be modified."""
        from services.sd_client.comfyui.workflow_loader import load_workflow

        workflow, _ = load_workflow("scene_single")
        class_types = {n.get("class_type") for n in workflow.values()}
        assert "ControlNetLoader" not in class_types
        assert "ControlNetApply" not in class_types


# ── B-2: ComfyUI Client Pose Upload ───────────────────────────────────


class TestComfyUIPoseUpload:
    """Test _upload_image and _ensure_pose_uploaded."""

    @pytest.mark.asyncio
    async def test_ensure_pose_uploaded_caches(self):
        """Second call should NOT call _upload_image again."""
        client = ComfyUIClient(base_url="http://test:8188")
        fake_b64 = base64.b64encode(b"fake_pose").decode()

        with patch.object(client, "_upload_image", new_callable=AsyncMock, return_value="2p_walk.png") as mock_upload:
            name1 = await client._ensure_pose_uploaded("walk", fake_b64)
            name2 = await client._ensure_pose_uploaded("walk", fake_b64)

        assert name1 == "2p_walk.png"
        assert name2 == "2p_walk.png"
        mock_upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_different_poses_uploaded_separately(self):
        """Different pose names should each be uploaded once."""
        client = ComfyUIClient(base_url="http://test:8188")
        fake_b64 = base64.b64encode(b"fake").decode()

        with patch.object(client, "_upload_image", new_callable=AsyncMock, return_value="uploaded.png") as mock_upload:
            await client._ensure_pose_uploaded("walk", fake_b64)
            await client._ensure_pose_uploaded("sit", fake_b64)

        assert mock_upload.call_count == 2

    @pytest.mark.asyncio
    async def test_txt2img_with_pose_payload(self):
        """When _pose_image_b64 in payload, pose should be uploaded and injected."""
        client = ComfyUIClient(base_url="http://test:8188")
        fake_b64 = base64.b64encode(b"pose_img").decode()

        with (
            patch("services.sd_client.comfyui.load_workflow") as mock_load,
            patch("services.sd_client.comfyui.inject_variables") as mock_inject,
            patch("services.sd_client.comfyui.run_workflow", return_value=[b"img"]),
            patch.object(client, "_ensure_pose_uploaded", new_callable=AsyncMock, return_value="2p_walk.png"),
        ):
            mock_load.return_value = ({}, "save")
            mock_inject.return_value = {}

            await client.txt2img(
                {
                    "prompt": "1girl, 1boy",
                    "_comfy_workflow": "scene_2p",
                    "_pose_image_b64": fake_b64,
                    "_pose_name": "walking_together",
                    "_controlnet_strength": 0.7,
                }
            )

            # inject_variables should receive pose_image and controlnet_strength
            call_args = mock_inject.call_args
            variables = call_args[0][1]
            assert variables["pose_image"] == "2p_walk.png"
            assert variables["controlnet_strength"] == 0.7

    @pytest.mark.asyncio
    async def test_txt2img_without_pose_unchanged(self):
        """Without _pose_image_b64, existing behavior unchanged."""
        client = ComfyUIClient(base_url="http://test:8188")

        with (
            patch("services.sd_client.comfyui.load_workflow") as mock_load,
            patch("services.sd_client.comfyui.inject_variables") as mock_inject,
            patch("services.sd_client.comfyui.run_workflow", return_value=[b"img"]),
        ):
            mock_load.return_value = ({}, "save")
            mock_inject.return_value = {}

            await client.txt2img({"prompt": "1girl, solo", "seed": 42})

            variables = mock_inject.call_args[0][1]
            assert "pose_image" not in variables

    @pytest.mark.asyncio
    async def test_pose_cache_invalidated_on_failure(self):
        """When run_workflow fails, pose cache entry should be removed."""
        client = ComfyUIClient(base_url="http://test:8188")
        fake_b64 = base64.b64encode(b"pose").decode()
        client._uploaded_poses["walk"] = "2p_walk.png"  # Pre-populate cache

        with (
            patch("services.sd_client.comfyui.load_workflow", return_value=({}, "save")),
            patch("services.sd_client.comfyui.inject_variables", return_value={}),
            patch("services.sd_client.comfyui.run_workflow", side_effect=RuntimeError("ComfyUI error")),
        ):
            with pytest.raises(RuntimeError):
                await client.txt2img(
                    {
                        "prompt": "test",
                        "_pose_image_b64": fake_b64,
                        "_pose_name": "walk",
                    }
                )

        assert "walk" not in client._uploaded_poses


# ── B-3: 2P Pose Library ──────────────────────────────────────────────


class TestPose2pMapping:
    """Test POSE_2P_MAPPING and load_2p_pose_reference."""

    def test_mapping_has_6_poses(self):
        from services.controlnet import POSE_2P_MAPPING

        assert len(POSE_2P_MAPPING) == 6

    def test_all_filenames_prefixed(self):
        from services.controlnet import POSE_2P_MAPPING

        for name, filename in POSE_2P_MAPPING.items():
            assert filename.startswith("2p_"), f"{name}: {filename} missing 2p_ prefix"
            assert filename.endswith(".png"), f"{name}: {filename} not .png"

    @patch("services.storage.get_storage")
    def test_load_2p_pose_reference_success(self, mock_get_storage):
        from services.controlnet import load_2p_pose_reference

        mock_storage = MagicMock()
        mock_get_storage.return_value = mock_storage
        mock_storage.exists.return_value = True
        mock_path = MagicMock()
        mock_path.read_bytes.return_value = b"fake_png"
        mock_storage.get_local_path.return_value = mock_path

        result = load_2p_pose_reference("walking_together")
        assert result is not None
        assert result == base64.b64encode(b"fake_png").decode("utf-8")
        mock_storage.exists.assert_called_once_with("shared/poses/2p/2p_walking_together.png")

    @patch("services.storage.get_storage")
    def test_load_2p_pose_reference_not_found(self, mock_get_storage):
        from services.controlnet import load_2p_pose_reference

        mock_storage = MagicMock()
        mock_get_storage.return_value = mock_storage
        mock_storage.exists.return_value = False

        result = load_2p_pose_reference("walking_together")
        assert result is None

    def test_load_2p_pose_reference_unknown_pose(self):
        from services.controlnet import load_2p_pose_reference

        result = load_2p_pose_reference("nonexistent_pose")
        assert result is None

    def test_detect_2p_pose_from_prompt(self):
        from services.controlnet import detect_2p_pose_from_prompt

        assert detect_2p_pose_from_prompt("1girl, 1boy, walking_together") == "walking_together"
        assert detect_2p_pose_from_prompt("sitting_together on bench") == "sitting_together"
        assert detect_2p_pose_from_prompt("1girl, solo") is None

    def test_detect_2p_pose_longest_match(self):
        from services.controlnet import detect_2p_pose_from_prompt

        # "standing_side_by_side" is longer than "back_to_back" — longest wins
        result = detect_2p_pose_from_prompt("standing_side_by_side and talking")
        assert result == "standing_side_by_side"

    def test_detect_2p_pose_space_format(self):
        from services.controlnet import detect_2p_pose_from_prompt

        assert detect_2p_pose_from_prompt("walking together in park") == "walking_together"
        assert detect_2p_pose_from_prompt("facing each other") == "facing_each_other"


# ── C-1: generation.py 2P Auto-Detection ──────────────────────────────


class TestGeneration2pDetection:
    """Test that _build_payload selects scene_2p workflow for 2P scenes."""

    def test_character_b_id_selects_scene_2p(self):
        from services.generation import _build_payload

        ctx = FakeContext(
            request=FakeRequest(comfy_workflow=None),
            character_b_id=123,
        )
        ctx.steps = 28
        ctx.cfg_scale = 5.5
        ctx.request.seed = 42
        ctx.request.width = 832
        ctx.request.height = 1216
        ctx.request.clip_skip = 2
        ctx.request.sampler_name = "euler"
        ctx.prompt = "1girl, 1boy"
        ctx.negative_prompt = "lowres"

        payload = _build_payload(ctx)
        assert payload["_comfy_workflow"] == "scene_2p"

    def test_no_character_b_selects_scene_single(self):
        from services.generation import _build_payload

        ctx = FakeContext(
            request=FakeRequest(comfy_workflow=None),
            character_b_id=None,
        )
        ctx.steps = 28
        ctx.cfg_scale = 5.5
        ctx.request.seed = 42
        ctx.request.width = 832
        ctx.request.height = 1216
        ctx.request.clip_skip = 2
        ctx.request.sampler_name = "euler"
        ctx.prompt = "1girl"
        ctx.negative_prompt = "lowres"

        payload = _build_payload(ctx)
        assert payload["_comfy_workflow"] == "scene_single"

    def test_req_character_b_id_selects_scene_2p(self):
        """req.character_b_id should select scene_2p even if ctx.character_b_id is None (prepare_prompt failed)."""
        from services.generation import _build_payload

        ctx = FakeContext(
            request=FakeRequest(comfy_workflow=None, character_b_id=789),
            character_b_id=None,
        )
        ctx.steps = 28
        ctx.cfg_scale = 5.5
        ctx.request.seed = 42
        ctx.request.width = 832
        ctx.request.height = 1216
        ctx.request.clip_skip = 2
        ctx.request.sampler_name = "euler"
        ctx.prompt = "1girl, 1boy"
        ctx.negative_prompt = "lowres"

        payload = _build_payload(ctx)
        assert payload["_comfy_workflow"] == "scene_2p"

    def test_explicit_workflow_overrides(self):
        from services.generation import _build_payload

        ctx = FakeContext(
            request=FakeRequest(comfy_workflow="custom"),
            character_b_id=123,
        )
        ctx.steps = 28
        ctx.cfg_scale = 5.5
        ctx.request.seed = 42
        ctx.request.width = 832
        ctx.request.height = 1216
        ctx.request.clip_skip = 2
        ctx.request.sampler_name = "euler"
        ctx.prompt = "1girl, 1boy"
        ctx.negative_prompt = "lowres"

        payload = _build_payload(ctx)
        assert payload["_comfy_workflow"] == "custom"


# ── C-2: generation_controlnet.py 2P Pose ─────────────────────────────


class TestApply2pPose:
    """Test _apply_2p_pose and apply_controlnet 2P branch."""

    @patch("services.controlnet.load_2p_pose_reference", return_value="base64posedata")
    def test_2p_pose_applied_to_payload(self, mock_load):
        from services.generation_controlnet import _apply_2p_pose

        req = FakeRequest()
        ctx = FakeContext(request=req, prompt="1girl, 1boy, walking_together", character_b_id=123)
        payload: dict = {}
        _apply_2p_pose(req, ctx, payload, db=None)

        assert payload["_pose_image_b64"] == "base64posedata"
        assert payload["_pose_name"] == "walking_together"
        assert payload["_controlnet_strength"] == 0.7
        assert ctx.controlnet_used == "walking_together"

    @patch("services.controlnet.load_2p_pose_reference", return_value="base64data")
    def test_2p_pose_default_fallback(self, mock_load):
        """When no pose detected in prompt, uses CONTROLNET_2P_DEFAULT_POSE."""
        from services.generation_controlnet import _apply_2p_pose

        req = FakeRequest()
        ctx = FakeContext(request=req, prompt="1girl, 1boy, talking", character_b_id=123)
        payload: dict = {}
        _apply_2p_pose(req, ctx, payload, db=None)

        assert payload["_pose_name"] == "standing_side_by_side"

    @patch("services.controlnet.load_2p_pose_reference", return_value=None)
    def test_2p_pose_asset_missing_skips(self, mock_load):
        """When pose asset file doesn't exist, ControlNet is skipped and workflow falls back to scene_single."""
        from services.generation_controlnet import _apply_2p_pose

        req = FakeRequest()
        ctx = FakeContext(request=req, prompt="1girl, 1boy", character_b_id=123)
        payload: dict = {"_comfy_workflow": "scene_2p"}
        _apply_2p_pose(req, ctx, payload, db=None)

        assert "_pose_image_b64" not in payload
        assert "_pose_name" not in payload
        assert "_controlnet_strength" not in payload
        assert ctx.controlnet_used is None
        # BLOCKER fix: must fall back so {{pose_image}} is never unresolved in ComfyUI
        assert payload["_comfy_workflow"] == "scene_single"

    def test_apply_controlnet_routes_to_2p(self):
        """apply_controlnet should call _apply_2p_pose when character_b_id exists."""
        from services.generation_controlnet import apply_controlnet

        ctx = FakeContext(character_b_id=123)
        payload: dict = {}

        with patch("services.generation_controlnet._apply_2p_pose") as mock_2p:
            apply_controlnet(payload, ctx, db=None)
            mock_2p.assert_called_once()

    def test_apply_controlnet_routes_to_2p_via_req_character_b_id(self):
        """apply_controlnet should call _apply_2p_pose when req.character_b_id is set but ctx.character_b_id is None.

        Covers the case where _prepare_prompt failed and ctx.character_b_id was not populated.
        """
        from services.generation_controlnet import apply_controlnet

        req = FakeRequest(character_b_id=456)
        ctx = FakeContext(request=req, character_b_id=None)  # ctx not populated (prepare_prompt failed)
        payload: dict = {}

        with patch("services.generation_controlnet._apply_2p_pose") as mock_2p:
            apply_controlnet(payload, ctx, db=None)
            mock_2p.assert_called_once()

    def test_apply_controlnet_1p_unchanged(self):
        """apply_controlnet without character_b_id follows existing 1P path."""
        from services.generation_controlnet import apply_controlnet

        ctx = FakeContext(character_b_id=None)
        payload: dict = {}

        with patch("services.generation_controlnet._apply_2p_pose") as mock_2p:
            apply_controlnet(payload, ctx, db=None)
            mock_2p.assert_not_called()


# ── Config Constants ───────────────────────────────────────────────────


class TestConfigConstants:
    """Verify 2P config constants exist."""

    def test_controlnet_2p_strength(self):
        from config import CONTROLNET_2P_STRENGTH

        assert CONTROLNET_2P_STRENGTH == 0.7

    def test_controlnet_2p_default_pose(self):
        from config import CONTROLNET_2P_DEFAULT_POSE

        assert CONTROLNET_2P_DEFAULT_POSE == "standing_side_by_side"
