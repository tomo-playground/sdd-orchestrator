"""
TDD tests for Lab service -- Tag Lab (Area C).

Phase 1: Updated for V3 Prompt Engine integration.
"""

import base64
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from models.lab import LabExperiment
from services.image_generation_core import ImageGenerationResult


def _make_tiny_png_b64() -> str:
    """Create a minimal 4x4 PNG and return its base64 encoding."""
    img = Image.new("RGB", (4, 4), color=(255, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _create_test_group(db_session):
    """Helper to create a test Project and Group."""
    from models import Project
    from models.group import Group

    project = Project(name="Test Project")
    db_session.add(project)
    db_session.flush()

    group = Group(name="Test Group", project_id=project.id)
    db_session.add(group)
    db_session.flush()

    return group


class TestRunExperiment:
    """Test run_experiment() -- single experiment execution with V3 Prompt Engine."""

    @pytest.mark.asyncio
    async def test_run_experiment_success(self, db_session):
        """
        Successful experiment: V3 generates image, WD14 validates, DB record created.

        Phase 1: Uses generate_image_with_v3() instead of direct SD call.
        """

        # Setup: Create a group (required for V3)
        group = _create_test_group(db_session)
        db_session.add(group)
        db_session.commit()

        fake_b64 = _make_tiny_png_b64()
        mock_v3_result = ImageGenerationResult(
            image=fake_b64,
            seed=12345,
            final_prompt="1girl, smile, blue_eyes, masterpiece",
            final_negative_prompt="worst quality",
            loras_applied=[{"name": "test_lora", "weight": 0.7, "source": "style"}],
            warnings=[],
        )

        mock_tags = [
            {"tag": "1girl", "score": 0.95, "category": "general"},
            {"tag": "smile", "score": 0.85, "category": "general"},
            {"tag": "brown_hair", "score": 0.9, "category": "general"},
        ]
        mock_comparison = {
            "matched": ["1girl", "smile"],
            "missing": ["blue_eyes"],
            "extra": ["brown_hair"],
            "skipped": [],
            "partial_matched": [],
        }

        with (
            patch("services.image_generation_core.generate_image_with_v3", return_value=mock_v3_result),
            patch("services.lab.wd14_predict_tags", return_value=mock_tags),
            patch(
                "services.lab.compare_prompt_to_tags",
                return_value=mock_comparison,
            ),
            patch("services.lab.save_experiment_image", return_value=None),
        ):
            from services.lab import run_experiment

            result = await run_experiment(
                db=db_session,
                target_tags=["1girl", "smile", "blue_eyes"],
                group_id=group.id,
                character_id=None,
                negative_prompt="worst quality",
                sd_params={"steps": 20, "cfg_scale": 7},
                seed=12345,
            )

        assert result.status == "completed"
        assert result.match_rate is not None
        assert result.prompt_used is not None
        assert result.final_prompt == mock_v3_result.final_prompt
        assert result.loras_applied == mock_v3_result.loras_applied

        # Verify DB record persisted
        exp = db_session.query(LabExperiment).first()
        assert exp is not None
        assert exp.status == "completed"
        assert exp.group_id == group.id
        assert exp.final_prompt is not None
        assert exp.loras_applied is not None

    @pytest.mark.asyncio
    async def test_run_experiment_sd_failure(self, db_session):
        """
        V3 image generation failure -> experiment status = 'failed'.

        Phase 1: Lab mode catches exceptions and continues with partial result.
        """

        group = _create_test_group(db_session)
        db_session.add(group)
        db_session.commit()

        # Lab mode: returns partial result with warnings instead of raising
        mock_v3_result = ImageGenerationResult(
            image="",
            seed=-1,
            final_prompt="1girl, smile",
            final_negative_prompt="",
            warnings=["SD API failed: Connection refused"],
        )

        with patch("services.image_generation_core.generate_image_with_v3", return_value=mock_v3_result):
            from services.lab import run_experiment

            result = await run_experiment(
                db=db_session,
                target_tags=["1girl", "smile"],
                group_id=group.id,
            )

        # Lab mode: status is "failed" because no image was generated
        assert result.status == "failed"
        exp = db_session.query(LabExperiment).first()
        assert exp is not None
        assert exp.status == "failed"

    @pytest.mark.asyncio
    async def test_run_experiment_v3_exception(self, db_session):
        """
        V3 raises exception -> Lab mode catches and marks failed.

        Phase 1: Lab mode error handling.
        """

        group = _create_test_group(db_session)
        db_session.add(group)
        db_session.commit()

        with patch(
            "services.image_generation_core.generate_image_with_v3",
            side_effect=Exception("V3 composition failed"),
        ):
            from services.lab import run_experiment

            result = await run_experiment(
                db=db_session,
                target_tags=["1girl"],
                group_id=group.id,
            )

        assert result.status == "failed"
        assert result.notes is not None
        assert "V3 composition failed" in result.notes


class TestRunBatch:
    """Test run_batch() -- multiple experiments with V3."""

    @pytest.mark.asyncio
    async def test_batch_creates_multiple_experiments(self, db_session):
        """
        Batch creates N experiments with same tags but different seeds.

        Phase 1: All experiments use the same group_id for consistent Style Profile.
        """

        group = _create_test_group(db_session)
        db_session.add(group)
        db_session.commit()

        with patch("services.lab.run_experiment") as mock_run:
            mock_exp = MagicMock()
            mock_exp.status = "completed"
            mock_exp.id = 1
            mock_exp.batch_id = "test-batch"
            mock_run.return_value = mock_exp

            from services.lab import run_batch

            result = await run_batch(
                db=db_session,
                target_tags=["1girl", "smile"],
                group_id=group.id,
                count=3,
            )

        assert mock_run.call_count == 3
        assert result["total"] == 3
        # Verify group_id was passed to each experiment
        for call in mock_run.call_args_list:
            assert call.kwargs["group_id"] == group.id

    @pytest.mark.asyncio
    async def test_batch_respects_max_size(self, db_session):
        """Batch count is capped at LAB_BATCH_MAX_SIZE."""

        group = _create_test_group(db_session)
        db_session.add(group)
        db_session.commit()

        with (
            patch("services.lab.run_experiment") as mock_run,
            patch("services.lab.LAB_BATCH_MAX_SIZE", 5),
        ):
            mock_exp = MagicMock()
            mock_exp.status = "completed"
            mock_run.return_value = mock_exp

            from services.lab import run_batch

            result = await run_batch(
                db=db_session,
                target_tags=["1girl"],
                group_id=group.id,
                count=100,
            )

        # Capped at the patched value of 5
        assert mock_run.call_count <= 5
        assert result["total"] <= 5


class TestAggregateTagEffectiveness:
    """Test aggregate_tag_effectiveness() -- lab_experiments -> tag stats."""

    def test_aggregate_from_experiments(self, db_session):
        """Aggregate match/use counts from completed experiments."""

        group = _create_test_group(db_session)
        db_session.add(group)
        db_session.flush()

        for i in range(3):
            exp = LabExperiment(
                experiment_type="tag_render",
                status="completed",
                group_id=group.id,
                prompt_used="1girl, smile",
                target_tags=["1girl", "smile"],
                match_rate=0.8 if i < 2 else 0.5,
                wd14_result={
                    "matched": ["1girl", "smile"] if i < 2 else ["1girl"],
                    "missing": [] if i < 2 else ["smile"],
                    "extra": [],
                },
                seed=i,
            )
            db_session.add(exp)
        db_session.commit()

        from services.lab import aggregate_tag_effectiveness

        report = aggregate_tag_effectiveness(db_session)

        assert report["total_experiments"] == 3
        assert len(report["items"]) > 0
        # 1girl: 3/3 matched
        girl_item = next(
            (it for it in report["items"] if it["tag_name"] == "1girl"),
            None,
        )
        assert girl_item is not None
        assert girl_item["use_count"] == 3
        assert girl_item["match_count"] == 3

    def test_aggregate_ignores_failed(self, db_session):
        """Only completed experiments are counted."""

        group = _create_test_group(db_session)
        db_session.add(group)
        db_session.flush()

        exp_failed = LabExperiment(
            experiment_type="tag_render",
            status="failed",
            group_id=group.id,
            prompt_used="1girl",
            target_tags=["1girl"],
            seed=0,
        )
        db_session.add(exp_failed)
        db_session.commit()

        from services.lab import aggregate_tag_effectiveness

        report = aggregate_tag_effectiveness(db_session)

        assert report["total_experiments"] == 0

    def test_aggregate_avg_match_rate(self, db_session):
        """Average match rate is computed from completed experiments."""

        group = _create_test_group(db_session)
        db_session.add(group)
        db_session.flush()

        for rate in [0.8, 0.6, 1.0]:
            exp = LabExperiment(
                experiment_type="tag_render",
                status="completed",
                group_id=group.id,
                prompt_used="1girl",
                target_tags=["1girl"],
                match_rate=rate,
                wd14_result={"matched": ["1girl"], "missing": [], "extra": []},
                seed=0,
            )
            db_session.add(exp)
        db_session.commit()

        from services.lab import aggregate_tag_effectiveness

        report = aggregate_tag_effectiveness(db_session)

        assert report["avg_match_rate"] == pytest.approx(0.8, abs=0.01)


class TestSyncToEngine:
    """Test sync_to_engine() -- upsert into tag_effectiveness table."""

    def test_sync_creates_effectiveness_records(self, db_session):
        """sync_to_engine creates/updates TagEffectiveness records."""
        from models.tag import Tag, TagEffectiveness

        group = _create_test_group(db_session)
        db_session.add(group)
        db_session.flush()

        tag = Tag(name="smile", category="scene", group_name="expression", default_layer=7)
        db_session.add(tag)
        db_session.flush()

        exp = LabExperiment(
            experiment_type="tag_render",
            status="completed",
            group_id=group.id,
            prompt_used="smile",
            target_tags=["smile"],
            match_rate=0.8,
            wd14_result={
                "matched": ["smile"],
                "missing": [],
                "extra": [],
            },
            seed=1,
        )
        db_session.add(exp)
        db_session.commit()

        from services.lab import sync_to_engine

        count = sync_to_engine(db_session)

        assert count >= 1
        te = (
            db_session.query(TagEffectiveness)
            .filter_by(tag_id=tag.id)
            .first()
        )
        assert te is not None
        assert te.use_count == 1
        assert te.match_count == 1
        assert te.effectiveness == pytest.approx(1.0)

    def test_sync_skips_unknown_tags(self, db_session):
        """Tags not in DB are skipped (no TagEffectiveness created)."""

        group = _create_test_group(db_session)
        db_session.add(group)
        db_session.flush()

        exp = LabExperiment(
            experiment_type="tag_render",
            status="completed",
            group_id=group.id,
            prompt_used="nonexistent_tag",
            target_tags=["nonexistent_tag"],
            match_rate=1.0,
            wd14_result={
                "matched": ["nonexistent_tag"],
                "missing": [],
                "extra": [],
            },
            seed=1,
        )
        db_session.add(exp)
        db_session.commit()

        from services.lab import sync_to_engine

        count = sync_to_engine(db_session)

        assert count == 0
