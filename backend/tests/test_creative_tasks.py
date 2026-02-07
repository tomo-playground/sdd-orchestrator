"""TDD tests for Creative Engine task_type registry + task modules."""

from __future__ import annotations

import pytest

from models.creative import CreativeSession
from models.scene import Scene
from models.storyboard import Storyboard

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
        assert hasattr(mod, "send_to_studio")

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
# 2. Scenario — send_to_studio (existing, regression)
# ===========================================================================


class TestScenarioSendToStudio:
    @pytest.mark.asyncio
    async def test_creates_storyboard_and_scenes(self, db_session):
        from services.creative_tasks.scenario import send_to_studio

        session = CreativeSession(
            task_type="scenario",
            objective="Test",
            evaluation_criteria={},
            max_rounds=3,
            status="completed",
            final_output={"title": "My Story", "content": "Scene 1\n\nScene 2\n\nScene 3"},
        )
        db_session.add(session)
        db_session.commit()

        result = await send_to_studio(db=db_session, session_id=session.id)

        assert result["scenes_created"] == 3
        sb = db_session.get(Storyboard, result["storyboard_id"])
        assert sb is not None
        assert sb.title == "My Story"


# ===========================================================================
# 3. Dialogue — send_to_studio
# ===========================================================================


class TestDialogueSendToStudio:
    @pytest.mark.asyncio
    async def test_creates_scenes_from_dialogue_lines(self, db_session):
        from services.creative_tasks.dialogue import send_to_studio

        session = CreativeSession(
            task_type="dialogue",
            objective="Write dialogue",
            evaluation_criteria={},
            max_rounds=3,
            status="completed",
            final_output={
                "title": "Cafe Talk",
                "content": "A: Hello!\nB: Hi there.\nA: How are you?",
            },
        )
        db_session.add(session)
        db_session.commit()

        result = await send_to_studio(db=db_session, session_id=session.id)

        assert result["scenes_created"] == 3
        scenes = (
            db_session.query(Scene).filter(Scene.storyboard_id == result["storyboard_id"]).order_by(Scene.order).all()
        )
        assert scenes[0].script == "A: Hello!"
        assert scenes[1].script == "B: Hi there."

    @pytest.mark.asyncio
    async def test_raises_if_not_finalized(self, db_session):
        from services.creative_tasks.dialogue import send_to_studio

        session = CreativeSession(
            task_type="dialogue",
            objective="No output",
            evaluation_criteria={},
            max_rounds=3,
            status="running",
        )
        db_session.add(session)
        db_session.commit()

        with pytest.raises(ValueError, match="not finalized"):
            await send_to_studio(db=db_session, session_id=session.id)


# ===========================================================================
# 4. Visual Concept — send_to_studio
# ===========================================================================


class TestVisualConceptSendToStudio:
    @pytest.mark.asyncio
    async def test_creates_scenes_from_sections(self, db_session):
        from services.creative_tasks.visual_concept import send_to_studio

        session = CreativeSession(
            task_type="visual_concept",
            objective="Design mood",
            evaluation_criteria={},
            max_rounds=3,
            status="completed",
            final_output={
                "title": "Neon City",
                "content": "Neon-lit street at night\n\nRain-soaked reflections\n\nClose-up of neon sign",
            },
        )
        db_session.add(session)
        db_session.commit()

        result = await send_to_studio(db=db_session, session_id=session.id)

        assert result["scenes_created"] == 3
        scenes = (
            db_session.query(Scene).filter(Scene.storyboard_id == result["storyboard_id"]).order_by(Scene.order).all()
        )
        # visual_concept uses description field, not script
        assert scenes[0].description == "Neon-lit street at night"


# ===========================================================================
# 5. Character Design — send_to_studio
# ===========================================================================


class TestCharacterDesignSendToStudio:
    @pytest.mark.asyncio
    async def test_creates_single_scene(self, db_session):
        from services.creative_tasks.character_design import send_to_studio

        session = CreativeSession(
            task_type="character_design",
            objective="Design a character",
            evaluation_criteria={},
            max_rounds=3,
            status="completed",
            final_output={
                "title": "Hero Design",
                "content": "Tall, silver hair, blue eyes, wears a cape",
            },
        )
        db_session.add(session)
        db_session.commit()

        result = await send_to_studio(db=db_session, session_id=session.id)

        assert result["scenes_created"] == 1
        scenes = db_session.query(Scene).filter(Scene.storyboard_id == result["storyboard_id"]).all()
        assert len(scenes) == 1
        assert "silver hair" in scenes[0].description

    @pytest.mark.asyncio
    async def test_appends_to_existing_storyboard(self, db_session):
        from services.creative_tasks.character_design import send_to_studio

        # Create existing storyboard with a scene
        sb = Storyboard(title="Existing", group_id=1)
        db_session.add(sb)
        db_session.flush()
        db_session.add(Scene(storyboard_id=sb.id, order=0, script="Existing scene"))
        db_session.commit()

        session = CreativeSession(
            task_type="character_design",
            objective="Add char",
            evaluation_criteria={},
            max_rounds=3,
            status="completed",
            final_output={"title": "Villain", "content": "Dark armor, red eyes"},
        )
        db_session.add(session)
        db_session.commit()

        result = await send_to_studio(
            db=db_session,
            session_id=session.id,
            storyboard_id=sb.id,
        )

        assert result["storyboard_id"] == sb.id
        assert result["scenes_created"] == 1
        scenes = (
            db_session.query(Scene)
            .filter(Scene.storyboard_id == sb.id, Scene.deleted_at.is_(None))
            .order_by(Scene.order)
            .all()
        )
        assert len(scenes) == 2
        assert scenes[1].order == 1


# ===========================================================================
# 6. creative_engine._get_criteria uses registry
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


# ===========================================================================
# 8. Router — send_to_studio dynamic dispatch
# ===========================================================================


class TestSendToStudioDynamic:
    @pytest.mark.asyncio
    async def test_send_dialogue_to_studio_via_router(self, client, db_session):
        """POST send-to-studio with a dialogue session uses dialogue module."""
        session = CreativeSession(
            task_type="dialogue",
            objective="Dialogue test",
            evaluation_criteria={},
            max_rounds=3,
            status="completed",
            final_output={"title": "Talk", "content": "A: Hey\nB: Yo"},
        )
        db_session.add(session)
        db_session.commit()

        resp = client.post(
            f"/lab/creative/sessions/{session.id}/send-to-studio",
            json={"group_id": 1},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["scenes_created"] == 2
