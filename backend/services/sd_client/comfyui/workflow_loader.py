"""ComfyUI workflow loader — JSON load + variable injection + output_node extraction."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

WORKFLOWS_DIR = Path(__file__).parent / "workflows"


def load_workflow(name: str) -> tuple[dict, str]:
    """Load workflow JSON, extract output_node from _meta, remove _meta.

    Returns:
        (workflow_dict, output_node_id) tuple.
    """
    path = WORKFLOWS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Workflow not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    meta = data.pop("_meta", {})
    output_node = meta.get("output_node", "")

    if not output_node:
        # Fallback: find SaveImage node
        for node_id, node in data.items():
            if node.get("class_type") == "SaveImage":
                output_node = node_id
                logger.info("Auto-detected output_node: %s", node_id)
                break

    if not output_node:
        raise ValueError(f"Workflow '{name}' has no output_node in _meta and no SaveImage node found")

    return data, output_node


def inject_variables(workflow: dict, variables: dict[str, str | int | float]) -> dict:
    """Replace {{variable}} placeholders with actual values.

    - Numeric values: replace both `"{{key}}"` (quoted) and `{{key}}` (unquoted).
    - String values: simple replacement.
    """
    raw = json.dumps(workflow)

    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"
        if isinstance(value, (int, float)):
            raw = raw.replace(f'"{placeholder}"', str(value))
            raw = raw.replace(placeholder, str(value))
        else:
            # JSON-escape string values to prevent breakage from " or \ in prompts
            escaped = json.dumps(str(value))[1:-1]  # Strip outer quotes from json.dumps
            raw = raw.replace(placeholder, escaped)

    # Warn about remaining placeholders
    remaining = re.findall(r"\{\{(\w+)\}\}", raw)
    if remaining:
        logger.warning("Unresolved workflow placeholders: %s", remaining)

    return json.loads(raw)
