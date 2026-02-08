"""TDD tests for Creative Engine task_type registry + task modules."""

from __future__ import annotations

import pytest

# ===========================================================================
# 1. Registry (services/creative_tasks/__init__.py)
# ===========================================================================


class TestTaskRegistry:
    def test_registry_has_all_task_types(self):
        from services.creative_tasks import TASK_REGISTRY

        assert "scenario" in TASK_REGISTRY
        assert "dialogue" in TASK_REGISTRY
        assert "visual_concept" in TASK_REGISTRY
        assert "character_design" in TASK_REGISTRY

    def test_registry_items_have_label_and_description(self):
        from services.creative_tasks import TASK_REGISTRY

        for key, meta in TASK_REGISTRY.items():
            assert "label" in meta, f"{key} missing label"
            assert "description" in meta, f"{key} missing description"

    def test_get_task_module_returns_module(self):
        from services.creative_tasks import get_task_module

        mod = get_task_module("scenario")
        assert hasattr(mod, "DEFAULT_CRITERIA")

    def test_get_task_module_unknown_raises(self):
        from services.creative_tasks import get_task_module

        with pytest.raises(ValueError, match="Unknown task_type"):
            get_task_module("nonexistent")

    def test_get_default_criteria_scenario(self):
        from services.creative_tasks import get_default_criteria

        criteria = get_default_criteria("scenario")
        assert "originality" in criteria
        assert "coherence" in criteria
        assert "engagement" in criteria

    def test_get_default_criteria_dialogue(self):
        from services.creative_tasks import get_default_criteria

        criteria = get_default_criteria("dialogue")
        assert "naturalness" in criteria
        assert "character_voice" in criteria
        assert "conflict" in criteria

    def test_get_default_criteria_visual_concept(self):
        from services.creative_tasks import get_default_criteria

        criteria = get_default_criteria("visual_concept")
        assert "originality" in criteria
        assert "sd_feasibility" in criteria
        assert "mood_coherence" in criteria

    def test_get_default_criteria_character_design(self):
        from services.creative_tasks import get_default_criteria

        criteria = get_default_criteria("character_design")
        assert "uniqueness" in criteria
        assert "visual_consistency" in criteria
        assert "tag_expressibility" in criteria

    def test_criteria_weights_sum_to_one(self):
        from services.creative_tasks import TASK_REGISTRY, get_default_criteria

        for task_type in TASK_REGISTRY:
            criteria = get_default_criteria(task_type)
            total = sum(c["weight"] for c in criteria.values())
            assert abs(total - 1.0) < 0.01, f"{task_type} weights sum to {total}"

    def test_get_default_criteria_returns_copy(self):
        from services.creative_tasks import get_default_criteria

        c1 = get_default_criteria("scenario")
        c2 = get_default_criteria("scenario")
        c1["extra"] = "mutated"
        assert "extra" not in c2


