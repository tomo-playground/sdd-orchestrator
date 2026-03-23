"""ComfyUI Workflow Runner — 워크플로우 JSON 로드 + 변수 치환 + API 실행."""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

COMFYUI_URL = "http://localhost:8188"
WORKFLOWS_DIR = Path(__file__).parent / "workflows"
MAX_WAIT_SEC = 120


def load_workflow(name: str) -> dict:
    """워크플로우 JSON 로드. _meta 키는 제거."""
    path = WORKFLOWS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Workflow not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("_meta", None)
    return data


def inject_variables(workflow: dict, variables: dict[str, str | int | float]) -> dict:
    """워크플로우 내 {{variable}} 플레이스홀더를 실제 값으로 치환."""
    raw = json.dumps(workflow)
    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"
        if isinstance(value, (int, float)):
            # 숫자는 따옴표 포함/미포함 모두 치환
            raw = raw.replace(f'"{placeholder}"', str(value))
            raw = raw.replace(placeholder, str(value))
        else:
            raw = raw.replace(placeholder, str(value))
    return json.loads(raw)


def queue_prompt(workflow: dict) -> str:
    """ComfyUI에 워크플로우 큐잉. prompt_id 반환."""
    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    if "error" in result:
        raise RuntimeError(f"ComfyUI error: {result['error']}")
    return result["prompt_id"]


def wait_for_result(prompt_id: str, save_node: str = "8_save") -> list[bytes]:
    """완료 대기 + 이미지 다운로드."""
    for _ in range(MAX_WAIT_SEC):
        time.sleep(1)
        try:
            resp = urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}")
            history = json.loads(resp.read())
            if prompt_id not in history:
                continue
            entry = history[prompt_id]
            if entry.get("status", {}).get("status_str") == "error":
                raise RuntimeError(f"ComfyUI execution error: {entry['status']}")
            outputs = entry.get("outputs", {})
            if save_node in outputs:
                images = []
                for img in outputs[save_node]["images"]:
                    url = (
                        f"{COMFYUI_URL}/view?"
                        f"filename={urllib.parse.quote(img['filename'])}"
                        f"&subfolder={urllib.parse.quote(img.get('subfolder', ''))}"
                        f"&type={img['type']}"
                    )
                    images.append(urllib.request.urlopen(url).read())
                return images
        except (urllib.error.URLError, json.JSONDecodeError):
            continue
    raise TimeoutError(f"ComfyUI timeout ({MAX_WAIT_SEC}s)")


def run_workflow(name: str, variables: dict, save_node: str = "8_save") -> list[bytes]:
    """워크플로우 로드 → 변수 주입 → 실행 → 이미지 반환."""
    workflow = load_workflow(name)
    workflow = inject_variables(workflow, variables)
    prompt_id = queue_prompt(workflow)
    logger.info("Queued workflow '%s' (prompt_id=%s)", name, prompt_id)
    return wait_for_result(prompt_id, save_node)
