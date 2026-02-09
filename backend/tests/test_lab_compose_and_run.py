"""Tests for lab.py compose_and_run -- must not call V3Builder directly.

WARNING #6: compose_and_run must delegate V3 composition to run_experiment
(which uses generate_image_with_v3), not invoke V3PromptBuilder directly.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.lab import LabExperiment


class TestComposeAndRunDelegation:
    """compose_and_run must not call V3PromptBuilder directly."""

    @pytest.mark.asyncio
    async def test_no_direct_v3_builder_call(self, db_session):
        """compose_and_run should pass tags to run_experiment, not compose."""
        from models import Project
        from models.group import Group

        project = Project(name="Test")
        db_session.add(project)
        db_session.flush()
        group = Group(name="G", project_id=project.id)
        db_session.add(group)
        db_session.flush()

        mock_experiment = MagicMock(spec=LabExperiment)
        mock_experiment.status = "completed"

        with (
            patch("services.lab.run_experiment", new_callable=AsyncMock) as mock_run,
            patch(
                "services.prompt.v3_composition.V3PromptBuilder"
            ) as MockBuilder,
        ):
            mock_run.return_value = mock_experiment

            from services.lab import compose_and_run

            await compose_and_run(
                db=db_session,
                scene_description="happy, classroom, standing",
                group_id=group.id,
                character_id=1,
            )

            # run_experiment should be called
            mock_run.assert_called_once()

            # V3PromptBuilder should NOT be instantiated
            MockBuilder.assert_not_called()

    @pytest.mark.asyncio
    async def test_passes_scene_tags_to_run_experiment(self, db_session):
        """compose_and_run must pass scene_description as tags to run_experiment."""
        from models import Project
        from models.group import Group

        project = Project(name="Test")
        db_session.add(project)
        db_session.flush()
        group = Group(name="G", project_id=project.id)
        db_session.add(group)
        db_session.flush()

        mock_experiment = MagicMock(spec=LabExperiment)

        with patch("services.lab.run_experiment", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_experiment

            from services.lab import compose_and_run

            await compose_and_run(
                db=db_session,
                scene_description="happy, classroom, standing",
                group_id=group.id,
                character_id=1,
            )

            call_kwargs = mock_run.call_args.kwargs
            # target_tags must contain the split scene description tags
            assert "happy" in call_kwargs["target_tags"]
            assert "classroom" in call_kwargs["target_tags"]
            assert "standing" in call_kwargs["target_tags"]
            # character_id must be passed through
            assert call_kwargs["character_id"] == 1
