"""Creative task-type registry — plugin structure for task modules."""

from __future__ import annotations

import importlib
from typing import Any

TASK_REGISTRY: dict[str, dict[str, str]] = {
    "scenario": {
        "label": "Scenario",
        "description": "Create original scenarios and scripts for short-form content",
    },
    "dialogue": {
        "label": "Dialogue",
        "description": "Write natural character dialogues with distinct voices",
    },
    "visual_concept": {
        "label": "Visual Concept",
        "description": "Design visual mood boards and cinematic concepts",
    },
    "character_design": {
        "label": "Character Design",
        "description": "Create unique character profiles with visual tag specifications",
    },
}


def get_task_module(task_type: str) -> Any:
    """Dynamically import a task_type module.

    Raises ModuleNotFoundError if the task_type module doesn't exist.
    """
    if task_type not in TASK_REGISTRY:
        msg = f"Unknown task_type: {task_type}"
        raise ValueError(msg)
    return importlib.import_module(f"services.creative_tasks.{task_type}")


def get_default_criteria(task_type: str) -> dict:
    """Load default evaluation criteria from the task_type module."""
    module = get_task_module(task_type)
    return module.DEFAULT_CRITERIA.copy()
