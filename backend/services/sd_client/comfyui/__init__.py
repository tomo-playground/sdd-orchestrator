"""ComfyUI client — SDClientBase implementation for ComfyUI backend."""

from __future__ import annotations

import base64
import logging
import random
import re

import httpx

from config import (
    COMFYUI_BASE_URL,
    COMFYUI_NETWORK_TIMEOUT,
)
from services.sd_client import SDClientBase
from services.sd_client.comfyui.workflow_loader import inject_variables, load_workflow
from services.sd_client.comfyui.workflow_runner import run_workflow
from services.sd_client.types import SDProgressResult, SDTxt2ImgResult

logger = logging.getLogger(__name__)

# Regex for <lora:NAME:WEIGHT> tags in SD WebUI prompt format
_LORA_TAG_RE = re.compile(r"<lora:([^:]+):([0-9.]+)>")

# Forge/SD WebUI sampler name → ComfyUI sampler_name (case-insensitive key)
_FORGE_TO_COMFY_SAMPLER: dict[str, str] = {
    "euler": "euler",
    "euler a": "euler_ancestral",
    "heun": "heun",
    "dpm2": "dpm_2",
    "dpm2 a": "dpm_2_ancestral",
    "dpm++ 2s a": "dpmpp_2s_ancestral",
    "dpm++ 2m": "dpmpp_2m",
    "dpm++ sde": "dpmpp_sde",
    "dpm++ 2m sde": "dpmpp_2m_sde",
    "dpm++ 3m sde": "dpmpp_3m_sde",
    "ddim": "ddim",
    "lms": "lms",
    "uni_pc": "uni_pc",
    "uni_pc bh2": "uni_pc_bh2",
}


def _map_sampler_to_comfy(sampler_name: str, scheduler: str | None) -> tuple[str, str]:
    """Map Forge sampler/scheduler names to ComfyUI equivalents.

    Forge separates "DPM++ 2M Karras" into sampler="DPM++ 2M", scheduler="Karras".
    ComfyUI uses lowercase underscore sampler names and lowercase scheduler names.
    """
    comfy_sampler = _FORGE_TO_COMFY_SAMPLER.get(sampler_name.lower())
    if comfy_sampler is None:
        logger.warning("Unknown Forge sampler '%s' — falling back to 'euler'", sampler_name)
        comfy_sampler = "euler"
    comfy_scheduler = (scheduler or "normal").lower()
    return comfy_sampler, comfy_scheduler


class ComfyUIClient(SDClientBase):
    """ComfyUI backend client.

    Uses instance-level httpx.AsyncClient for connection reuse.
    """

    def __init__(self, base_url: str | None = None):
        self._base_url = (base_url or COMFYUI_BASE_URL).rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=COMFYUI_NETWORK_TIMEOUT,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        self._current_checkpoint: str = ""
        self._available_checkpoints: list[str] = []
        self._available_loras: list[str] = []

    async def _ensure_checkpoint(self) -> str:
        """Ensure _current_checkpoint is set. Fetch from ComfyUI if empty."""
        if self._current_checkpoint:
            return self._current_checkpoint
        if not self._available_checkpoints:
            try:
                resp = await self._http.get("/object_info/CheckpointLoaderSimple")
                resp.raise_for_status()
                data = resp.json()
                self._available_checkpoints = (
                    data.get("CheckpointLoaderSimple", {})
                    .get("input", {})
                    .get("required", {})
                    .get("ckpt_name", [[]])[0]
                )
            except Exception as e:
                logger.warning("Failed to fetch checkpoints: %s", e)
        if self._available_checkpoints:
            self._current_checkpoint = self._available_checkpoints[0]
            logger.info("Auto-selected checkpoint: %s", self._current_checkpoint)
        return self._current_checkpoint

    async def _get_available_loras(self) -> list[str]:
        """Fetch available LoRA names from ComfyUI."""
        if self._available_loras:
            return self._available_loras
        try:
            resp = await self._http.get("/object_info/LoraLoader")
            resp.raise_for_status()
            data = resp.json()
            self._available_loras = (
                data.get("LoraLoader", {}).get("input", {}).get("required", {}).get("lora_name", [[]])[0]
            )
        except Exception as e:
            logger.warning("Failed to fetch LoRAs: %s", e)
        return self._available_loras

    async def close(self) -> None:
        """Shutdown: close the httpx connection pool."""
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    # ── txt2img ──────────────────────────────────────────────

    async def txt2img(self, payload: dict, timeout: float | None = None) -> SDTxt2ImgResult:
        """Convert SD WebUI payload → ComfyUI workflow → execute → SDTxt2ImgResult."""
        workflow_name = payload.get("_comfy_workflow", "scene_single")
        workflow, output_node = load_workflow(workflow_name)

        variables = self._payload_to_variables(payload)
        workflow = inject_variables(workflow, variables)

        # Apply LoRA nodes — always call to bypass unused slots (strength=0)
        loras = self._extract_lora_tags(payload.get("prompt", "") + " " + variables.get("positive", ""))
        available_loras = await self._get_available_loras()
        workflow = self._apply_loras_to_workflow(workflow, loras, available_loras)

        # Apply checkpoint: override_settings takes priority, fall back to auto-detected
        checkpoint = self._resolve_checkpoint(payload) or await self._ensure_checkpoint()
        if checkpoint:
            self._set_checkpoint_in_workflow(workflow, checkpoint)

        image_bytes_list = await run_workflow(self._http, workflow, output_node)

        images_b64 = [base64.b64encode(img).decode("ascii") for img in image_bytes_list]

        return SDTxt2ImgResult(
            images=images_b64,
            info={"comfyui": True, "workflow": workflow_name},
            seed=variables.get("seed"),
        )

    # ── get/set options ──────────────────────────────────────

    async def get_options(self) -> dict:
        """Return internal checkpoint state (ComfyUI has no global options API)."""
        return {"sd_model_checkpoint": self._current_checkpoint}

    async def set_options(self, options: dict, timeout: float | None = None) -> dict:
        """Store checkpoint name for next txt2img call."""
        if "sd_model_checkpoint" in options:
            self._current_checkpoint = options["sd_model_checkpoint"]
        return {"status": "ok"}

    # ── model/LoRA listing ───────────────────────────────────

    async def get_models(self) -> list[dict]:
        """List available checkpoints via /object_info/CheckpointLoaderSimple."""
        try:
            resp = await self._http.get("/object_info/CheckpointLoaderSimple")
            resp.raise_for_status()
            data = resp.json()
            choices = (
                data.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
            )
            return [{"title": name, "model_name": name.rsplit(".", 1)[0]} for name in choices]
        except Exception as e:
            logger.warning("Failed to get ComfyUI models: %s", e)
            return []

    async def get_loras(self) -> list[dict]:
        """List available LoRAs via /object_info/LoraLoader."""
        try:
            resp = await self._http.get("/object_info/LoraLoader")
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("LoraLoader", {}).get("input", {}).get("required", {}).get("lora_name", [[]])[0]
            return [{"name": name, "alias": name.rsplit(".", 1)[0]} for name in choices]
        except Exception as e:
            logger.warning("Failed to get ComfyUI LoRAs: %s", e)
            return []

    # ── progress ─────────────────────────────────────────────

    async def get_progress(self) -> SDProgressResult:
        """Approximate progress from ComfyUI queue status."""
        try:
            resp = await self._http.get("/prompt")
            resp.raise_for_status()
            data = resp.json()
            queue_remaining = data.get("exec_info", {}).get("queue_remaining", 0)
            if not isinstance(queue_remaining, int):
                queue_remaining = 0
            progress = 0.0 if queue_remaining > 0 else 1.0
            return SDProgressResult(progress=progress, textinfo=f"queue: {queue_remaining}")
        except Exception:
            return SDProgressResult()

    # ── ControlNet ───────────────────────────────────────────

    async def controlnet_detect(self, payload: dict) -> dict:
        """Not supported — ComfyUI uses workflow nodes for detection."""
        raise NotImplementedError("ComfyUI uses workflow nodes for detection, not a separate API")

    async def check_controlnet(self) -> bool:
        """Check if ControlNet nodes are available."""
        try:
            resp = await self._http.get("/object_info")
            resp.raise_for_status()
            data = resp.json()
            return "ControlNetLoader" in data or "ControlNetApplyAdvanced" in data
        except Exception:
            return False

    async def get_controlnet_models(self) -> list[str]:
        """List available ControlNet models."""
        try:
            resp = await self._http.get("/object_info/ControlNetLoader")
            resp.raise_for_status()
            data = resp.json()
            choices = (
                data.get("ControlNetLoader", {}).get("input", {}).get("required", {}).get("control_net_name", [[]])[0]
            )
            return list(choices)
        except Exception as e:
            logger.warning("Failed to get ComfyUI ControlNet models: %s", e)
            return []

    # ── Health check ─────────────────────────────────────────

    async def health_check(self) -> dict[str, bool]:
        """Verify ComfyUI connectivity and required custom nodes."""
        result: dict[str, bool] = {"connected": False, "DynamicThresholdingFull": False}
        try:
            resp = await self._http.get("/object_info")
            resp.raise_for_status()
            data = resp.json()
            result["connected"] = True
            result["DynamicThresholdingFull"] = "DynamicThresholdingFull" in data
            for node_type in ("KSampler", "LoraLoader", "CheckpointLoaderSimple"):
                result[node_type] = node_type in data
        except Exception as e:
            logger.warning("ComfyUI health check failed: %s", e)
        return result

    # ── Private helpers ──────────────────────────────────────

    @staticmethod
    def _payload_to_variables(payload: dict) -> dict:
        """Convert SD WebUI txt2img payload to ComfyUI workflow variables."""
        prompt_text = payload.get("prompt", "")
        # Strip LoRA tags from prompt (they'll be applied as workflow nodes)
        clean_prompt = _LORA_TAG_RE.sub("", prompt_text).strip().strip(",").strip()

        seed = payload.get("seed", -1)
        if seed == -1:
            seed = random.randint(0, 2**32 - 1)

        comfy_sampler, comfy_scheduler = _map_sampler_to_comfy(
            payload.get("sampler_name", "euler"),
            payload.get("scheduler"),
        )

        return {
            "positive": clean_prompt,
            "negative": payload.get("negative_prompt", ""),
            "seed": seed,
            "width": payload.get("width", 832),
            "height": payload.get("height", 1216),
            "steps": payload.get("steps", 28),
            "cfg": payload.get("cfg_scale", 7.0),
            "sampler_name": comfy_sampler,
            "scheduler": comfy_scheduler,
        }

    @staticmethod
    def _extract_lora_tags(prompt: str) -> list[dict[str, str | float]]:
        """Extract LoRA tags from prompt string.

        Returns list of {"name": "lora_file.safetensors", "weight": 0.7}.
        """
        results = []
        for m in _LORA_TAG_RE.finditer(prompt):
            name = m.group(1)
            if not name.endswith((".safetensors", ".ckpt", ".pt")):
                name = f"{name}.safetensors"
            results.append({"name": name, "weight": float(m.group(2))})
        return results

    @staticmethod
    def _apply_loras_to_workflow(workflow: dict, loras: list[dict], available_loras: list[str] | None = None) -> dict:
        """Set LoRA parameters in existing workflow LoraLoader nodes.

        Fat Template strategy: workflow has pre-placed LoraLoader nodes.
        Unused slots get strength_model=0 / strength_clip=0 with a valid lora_name.
        """
        lora_nodes = sorted(
            [(nid, node) for nid, node in workflow.items() if node.get("class_type") == "LoraLoader"],
            key=lambda x: x[0],
        )

        # Determine a valid fallback LoRA name for bypass slots
        fallback_lora = ""
        if loras:
            fallback_lora = loras[0]["name"]
        elif available_loras:
            fallback_lora = available_loras[0]

        for i, (_node_id, node) in enumerate(lora_nodes):
            if i < len(loras):
                lora = loras[i]
                node["inputs"]["lora_name"] = lora["name"]
                node["inputs"]["strength_model"] = lora["weight"]
                node["inputs"]["strength_clip"] = lora["weight"]
            else:
                # Bypass: zero strength + valid lora_name to pass ComfyUI validation
                node["inputs"]["strength_model"] = 0
                node["inputs"]["strength_clip"] = 0
                if fallback_lora:
                    node["inputs"]["lora_name"] = fallback_lora

        return workflow

    @staticmethod
    def _resolve_checkpoint(payload: dict) -> str:
        """Extract checkpoint name from SD WebUI override_settings."""
        overrides = payload.get("override_settings", {})
        return overrides.get("sd_model_checkpoint", "")

    @staticmethod
    def _set_checkpoint_in_workflow(workflow: dict, checkpoint: str) -> None:
        """Set checkpoint in CheckpointLoaderSimple node."""
        for node in workflow.values():
            if node.get("class_type") == "CheckpointLoaderSimple":
                node["inputs"]["ckpt_name"] = checkpoint
                break
