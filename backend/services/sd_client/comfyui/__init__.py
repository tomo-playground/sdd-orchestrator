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
    CONTROLNET_2P_STRENGTH,
)
from services.sd_client import SDClientBase
from services.sd_client.comfyui.workflow_loader import inject_variables, load_workflow
from services.sd_client.comfyui.workflow_runner import run_workflow
from services.sd_client.types import SDProgressResult, SDTxt2ImgResult

logger = logging.getLogger(__name__)

# Regex for <lora:NAME:WEIGHT> tags in SD WebUI prompt format
_LORA_TAG_RE = re.compile(r"<lora:([^:]+):([0-9.]+)>")

# SD WebUI sampler name → ComfyUI sampler_name (case-insensitive key)
_WEBUI_TO_COMFY_SAMPLER: dict[str, str] = {
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
    """Map SD WebUI sampler/scheduler names to ComfyUI equivalents.

    SD WebUI separates "DPM++ 2M Karras" into sampler="DPM++ 2M", scheduler="Karras".
    ComfyUI uses lowercase underscore sampler names and lowercase scheduler names.
    """
    comfy_sampler = _WEBUI_TO_COMFY_SAMPLER.get(sampler_name.lower())
    if comfy_sampler is None:
        logger.warning("Unknown sampler '%s' — falling back to 'euler'", sampler_name)
        comfy_sampler = "euler"
    comfy_scheduler = (scheduler or "karras").lower()  # noobaiXL v-pred: karras default
    return comfy_sampler, comfy_scheduler


def _bypass_lora_node(workflow: dict, node_id: str, node: dict) -> None:
    """Remove a LoRA node from the workflow by reconnecting downstream references.

    LoraLoader has inputs: model=[src, 0], clip=[src, 1]
    Downstream nodes referencing [node_id, 0] → model, [node_id, 1] → clip.
    Redirect them to the LoRA node's own input sources.
    """
    model_src = node["inputs"].get("model")  # e.g., ["1_checkpoint", 0]
    clip_src = node["inputs"].get("clip")  # e.g., ["1_checkpoint", 1]

    for other_id, other_node in workflow.items():
        if other_id == node_id:
            continue
        for key, val in other_node.get("inputs", {}).items():
            if isinstance(val, list) and len(val) == 2 and val[0] == node_id:
                if val[1] == 0 and model_src:
                    other_node["inputs"][key] = model_src
                elif val[1] == 1 and clip_src:
                    other_node["inputs"][key] = clip_src

    # Remove the LoRA node from workflow
    del workflow[node_id]


def _log_workflow_summary(workflow: dict, checkpoint: str) -> None:
    """Log key workflow fields for debugging (post-inject)."""
    summary = {"checkpoint": checkpoint}
    for nid, node in workflow.items():
        ct = node.get("class_type", "")
        inputs = node.get("inputs", {})
        if ct == "CLIPTextEncode" and "text" in inputs:
            text = inputs["text"]
            label = "positive" if "positive" not in summary else "negative"
            summary[label] = text[:80] + "..." if len(text) > 80 else text
        elif ct == "KSampler":
            summary["seed"] = inputs.get("seed")
            summary["steps"] = inputs.get("steps")
            summary["cfg"] = inputs.get("cfg")
            summary["sampler"] = inputs.get("sampler_name")
    logger.info("🔧 [ComfyUI Workflow] %s", summary)


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
        self._loras_fetched: bool = False
        self._uploaded_poses: dict[str, str] = {}  # pose_name → comfy_filename

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
        """Fetch available LoRA names from ComfyUI (cached after first call)."""
        if self._loras_fetched:
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
        self._loras_fetched = True
        return self._available_loras

    async def clear_cache(self) -> None:
        """Clear ComfyUI execution cache to force fresh generation.

        Unloads models to fully reset cached conditioning/latents.
        Models are reloaded on next generation (~2s overhead).
        """
        try:
            await self._http.post("/free", json={"unload_models": True, "free_memory": True})
            logger.info("[ComfyUI] Cache cleared (models unloaded)")
        except Exception as e:
            logger.warning("[ComfyUI] Cache clear failed: %s", e)

    async def close(self) -> None:
        """Shutdown: close the httpx connection pool."""
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    # ── txt2img ──────────────────────────────────────────────

    async def _upload_image(self, image_b64: str, filename: str) -> str:
        """Upload base64 image to ComfyUI /upload/image. Returns uploaded filename.

        Retries up to 3 total attempts (initial + 2 retries with 1s, 2s delays).
        ConnectError propagates immediately (ComfyUI down).
        """
        import asyncio  # noqa: PLC0415

        image_bytes = base64.b64decode(image_b64)
        delays = [1, 2]
        last_exc: Exception | None = None

        for attempt in range(3):
            try:
                files = {"image": (filename, image_bytes, "image/png")}
                resp = await self._http.post("/upload/image", files=files, data={"overwrite": "true"})
                resp.raise_for_status()
                data = resp.json()
                uploaded_name = data.get("name", filename)
                logger.info("📤 [ComfyUI] Uploaded pose image: %s (attempt %d)", uploaded_name, attempt + 1)
                return uploaded_name
            except httpx.ConnectError:
                raise
            except Exception as e:
                last_exc = e
                if attempt < 2:
                    logger.warning("⚠️ [ComfyUI] Upload retry %d for %s: %s", attempt + 1, filename, e)
                    await asyncio.sleep(delays[attempt])

        raise RuntimeError(f"Failed to upload {filename} after 3 attempts: {last_exc}")

    async def _ensure_pose_uploaded(self, pose_name: str, pose_b64: str) -> str:
        """Check pose cache → upload if missing. Returns ComfyUI filename."""
        cached = self._uploaded_poses.get(pose_name)
        if cached:
            return cached
        filename = f"2p_{pose_name}.png"
        uploaded_name = await self._upload_image(pose_b64, filename)
        self._uploaded_poses[pose_name] = uploaded_name
        return uploaded_name

    async def txt2img(self, payload: dict, timeout: float | None = None) -> SDTxt2ImgResult:
        """Convert SD WebUI payload → ComfyUI workflow → execute → SDTxt2ImgResult."""
        workflow_name = payload.get("_comfy_workflow", "scene_single")
        workflow, output_node = load_workflow(workflow_name)

        # Handle 2P pose image upload (pop large base64 data before variable injection)
        pose_b64 = payload.pop("_pose_image_b64", None)
        pose_name = payload.pop("_pose_name", None)

        variables = self._payload_to_variables(payload)

        # Resolve checkpoint early so {{checkpoint}} placeholder is replaced during inject_variables
        checkpoint = self._resolve_checkpoint(payload) or await self._ensure_checkpoint()
        if checkpoint:
            variables["checkpoint"] = checkpoint

        if pose_b64 and pose_name:
            filename = await self._ensure_pose_uploaded(pose_name, pose_b64)
            variables["pose_image"] = filename
            variables["controlnet_strength"] = payload.pop("_controlnet_strength", CONTROLNET_2P_STRENGTH)

        workflow = inject_variables(workflow, variables)

        # Apply LoRA nodes — always call to bypass unused slots (strength=0)
        loras = self._extract_lora_tags(payload.get("prompt", "") + " " + variables.get("positive", ""))
        available_loras = await self._get_available_loras()
        workflow = self._apply_loras_to_workflow(workflow, loras, available_loras)
        if loras:
            logger.info("🎨 [ComfyUI LoRA] Applied %d: %s", len(loras), [(l["name"], l["weight"]) for l in loras])

        # Apply checkpoint: payload takes priority, fall back to auto-detected
        checkpoint = self._resolve_checkpoint(payload) or await self._ensure_checkpoint()
        if checkpoint:
            self._set_checkpoint_in_workflow(workflow, checkpoint)

        # Log final workflow summary for debugging
        _log_workflow_summary(workflow, checkpoint or "unknown")

        # Dump KSampler inputs for white image debugging
        for _nid, _node in workflow.items():
            if _node.get("class_type") == "KSampler":
                logger.info(
                    "🔍 [ComfyUI KSampler] %s", {k: v for k, v in _node["inputs"].items() if k != "latent_image"}
                )

        try:
            image_bytes_list = await run_workflow(self._http, workflow, output_node)
        except Exception:
            if pose_name:
                self._uploaded_poses.pop(pose_name, None)
            raise

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

        neg_prompt = payload.get("negative_prompt", "")

        return {
            "positive": clean_prompt,
            "negative": neg_prompt,
            "seed": seed,
            "width": payload.get("width", 832),
            "height": payload.get("height", 1216),
            "steps": payload.get("steps", 28),
            "cfg": payload.get("cfg_scale", 5.5),  # noobaiXL v-pred: lower cfg recommended
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
                elif node["inputs"].get("lora_name", "").startswith("placeholder"):
                    logger.warning(
                        "LoRA node '%s' has placeholder name and no fallback available — "
                        "bypassing by removing from workflow chain",
                        _node_id,
                    )
                    # Reconnect: point downstream nodes to this node's input source
                    _bypass_lora_node(workflow, _node_id, node)

        return workflow

    @staticmethod
    def _resolve_checkpoint(payload: dict) -> str:
        """Extract checkpoint name from payload."""
        return payload.get("sd_model_checkpoint", "")

    @staticmethod
    def _set_checkpoint_in_workflow(workflow: dict, checkpoint: str) -> None:
        """Set checkpoint in CheckpointLoaderSimple node."""
        for node in workflow.values():
            if node.get("class_type") == "CheckpointLoaderSimple":
                node["inputs"]["ckpt_name"] = checkpoint
                break
