"""Tests for ComfyUI workflow loader (SP-022 B-1)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from services.sd_client.comfyui.workflow_loader import (
    inject_variables,
    load_workflow,
)


class TestLoadWorkflow:
    """load_workflow() — JSON load + _meta extraction."""

    def test_load_reference_workflow(self):
        """reference.json loads successfully with output_node from _meta."""
        workflow, output_node = load_workflow("reference")
        assert output_node == "9_save"
        assert "_meta" not in workflow
        assert "1_checkpoint" in workflow

    def test_load_scene_single_workflow(self):
        """scene_single.json loads successfully."""
        workflow, output_node = load_workflow("scene_single")
        assert output_node == "11_save"
        assert "_meta" not in workflow
        assert "1_checkpoint" in workflow
        # 3 LoRA slots in Fat Template
        lora_nodes = [nid for nid, n in workflow.items() if n.get("class_type") == "LoraLoader"]
        assert len(lora_nodes) == 3

    def test_workflow_not_found(self):
        """Non-existent workflow raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Workflow not found"):
            load_workflow("nonexistent_workflow_xyz")

    def test_auto_detect_save_node(self, tmp_path: Path):
        """Fallback: auto-detect SaveImage node when _meta.output_node is missing."""
        import services.sd_client.comfyui.workflow_loader as mod

        wf = {
            "_meta": {"name": "test"},
            "node_a": {"class_type": "KSampler", "inputs": {}},
            "node_b": {"class_type": "SaveImage", "inputs": {"images": ["node_a", 0]}},
        }
        (tmp_path / "auto_detect.json").write_text(json.dumps(wf))

        original_dir = mod.WORKFLOWS_DIR
        mod.WORKFLOWS_DIR = tmp_path
        try:
            workflow, output_node = load_workflow("auto_detect")
            assert output_node == "node_b"
        finally:
            mod.WORKFLOWS_DIR = original_dir

    def test_no_output_node_raises(self, tmp_path: Path):
        """No _meta.output_node and no SaveImage node raises ValueError."""
        import services.sd_client.comfyui.workflow_loader as mod

        wf = {
            "_meta": {"name": "test"},
            "node_a": {"class_type": "KSampler", "inputs": {}},
        }
        (tmp_path / "no_save.json").write_text(json.dumps(wf))

        original_dir = mod.WORKFLOWS_DIR
        mod.WORKFLOWS_DIR = tmp_path
        try:
            with pytest.raises(ValueError, match="no output_node"):
                load_workflow("no_save")
        finally:
            mod.WORKFLOWS_DIR = original_dir


class TestInjectVariables:
    """inject_variables() — placeholder substitution."""

    def test_string_variable(self):
        wf = {"node": {"inputs": {"text": "{{positive}}"}}}
        result = inject_variables(wf, {"positive": "1girl, solo"})
        assert result["node"]["inputs"]["text"] == "1girl, solo"

    def test_number_variable_removes_quotes(self):
        """Numeric values: "{{seed}}" → 42 (no quotes in JSON)."""
        wf = {"node": {"inputs": {"seed": "{{seed}}"}}}
        result = inject_variables(wf, {"seed": 42})
        assert result["node"]["inputs"]["seed"] == 42

    def test_float_variable(self):
        wf = {"node": {"inputs": {"strength": "{{strength}}"}}}
        result = inject_variables(wf, {"strength": 0.7})
        assert result["node"]["inputs"]["strength"] == 0.7

    def test_multiple_variables(self):
        wf = {
            "pos": {"inputs": {"text": "{{positive}}"}},
            "neg": {"inputs": {"text": "{{negative}}"}},
            "sampler": {"inputs": {"seed": "{{seed}}", "steps": "{{steps}}"}},
        }
        result = inject_variables(
            wf,
            {
                "positive": "1girl",
                "negative": "lowres",
                "seed": 123,
                "steps": 28,
            },
        )
        assert result["pos"]["inputs"]["text"] == "1girl"
        assert result["neg"]["inputs"]["text"] == "lowres"
        assert result["sampler"]["inputs"]["seed"] == 123
        assert result["sampler"]["inputs"]["steps"] == 28

    def test_missing_placeholder_warning(self, caplog):
        """Unresolved placeholders log a warning."""
        wf = {"node": {"inputs": {"text": "{{unresolved}}"}}}
        with caplog.at_level(logging.WARNING):
            result = inject_variables(wf, {})
        assert "unresolved" in result["node"]["inputs"]["text"]
        assert any("Unresolved" in r.message for r in caplog.records)
