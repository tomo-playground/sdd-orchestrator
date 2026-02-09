"""Tests for Style LoRA resolution SSOT.

resolve_style_loras_from_group (image_generation_core) must use
resolve_effective_config cascade, and generation.py must import from
image_generation_core instead of having its own copy.
"""

from unittest.mock import patch


class TestResolveStyleLorasUsesConfigCascade:
    """resolve_style_loras_from_group must use resolve_effective_config."""

    def test_uses_resolve_effective_config(self, db_session):
        """Must call resolve_effective_config for proper Project→Group cascade."""
        from models import Project
        from models.group import Group

        project = Project(name="Test")
        db_session.add(project)
        db_session.flush()
        group = Group(name="G", project_id=project.id)
        db_session.add(group)
        db_session.flush()

        with patch("services.config_resolver.resolve_effective_config") as mock_resolve:
            mock_resolve.return_value = {"values": {"style_profile_id": None}, "sources": {}}

            from services.image_generation_core import resolve_style_loras_from_group

            resolve_style_loras_from_group(group.id, db_session)
            mock_resolve.assert_called_once()


class TestGenerationDelegatesToCore:
    """generation._resolve_style_loras must delegate to image_generation_core."""

    def test_delegates_to_core(self, db_session):
        """_resolve_style_loras should call resolve_style_loras_from_storyboard."""
        with patch(
            "services.image_generation_core.resolve_style_loras_from_storyboard",
            return_value=[{"name": "test", "weight": 0.7, "trigger_words": []}],
        ) as mock_core:
            from services.generation import _resolve_style_loras

            result = _resolve_style_loras(999, db_session)
            mock_core.assert_called_once_with(999, db_session)
            assert result == [{"name": "test", "weight": 0.7, "trigger_words": []}]
