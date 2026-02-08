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


# ===========================================================================
# 2. creative_engine._get_criteria uses registry
# ===========================================================================


class TestGetCriteriaFromRegistry:
    def test_scenario_criteria_via_engine(self):
        from services.creative_engine import _get_criteria

        criteria = _get_criteria("scenario")
        assert "originality" in criteria

    def test_dialogue_criteria_via_engine(self):
        from services.creative_engine import _get_criteria

        criteria = _get_criteria("dialogue")
        assert "naturalness" in criteria

    def test_unknown_returns_empty(self):
        from services.creative_engine import _get_criteria

        criteria = _get_criteria("nonexistent_type")
        assert criteria == {}

    @pytest.mark.asyncio
    async def test_create_session_uses_registry_criteria(self, db_session):
        """create_session with dialogue task_type gets dialogue defaults."""
        from services.creative_engine import create_session

        session = await create_session(
            db=db_session,
            task_type="dialogue",
            objective="Test dialogue defaults",
        )

        assert session.evaluation_criteria is not None
        assert "naturalness" in session.evaluation_criteria
        assert "character_voice" in session.evaluation_criteria


# ===========================================================================
# 7. Router — GET /task-types
# ===========================================================================


class TestTaskTypesEndpoint:
    def test_returns_all_task_types(self, client):
        resp = client.get("/lab/creative/task-types")
        assert resp.status_code == 200
        data = resp.json()
        keys = [item["key"] for item in data["items"]]
        assert "scenario" in keys
        assert "dialogue" in keys
        assert "visual_concept" in keys
        assert "character_design" in keys

    def test_each_item_has_label_and_description(self, client):
        resp = client.get("/lab/creative/task-types")
        for item in resp.json()["items"]:
            assert "key" in item
            assert "label" in item
            assert "description" in item


