"""
TDD tests for image_generation_core -- unified V3 Prompt Engine + SD integration.

Phase 1: Lab + Studio unified image generation.
"""

import base64
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from services.image_generation_core import (
    ImageGenerationResult,
    generate_image_with_v3,
    resolve_style_loras_from_group,
    resolve_style_loras_from_storyboard,
)


def _make_tiny_png_b64() -> str:
    """Create a minimal 4x4 PNG and return its base64 encoding."""
    img = Image.new("RGB", (4, 4), color=(255, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


class TestGenerateImageWithV3:
    """Test generate_image_with_v3() -- unified Lab + Studio image generation."""

    @pytest.mark.asyncio
    async def test_generate_with_character_and_group(self, db_session):
        """Generate image with character LoRA + Style Profile from Group."""
        from models import Character, LoRA, Project, StyleProfile
        from models.group import Group
        from models.group_config import GroupConfig

        # Setup: Project → Group with Style Profile
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        lora = LoRA(
            name="test_style_lora",
                        trigger_words=["anime", "vibrant"],
            lora_type="style",
        )
        db_session.add(lora)
        db_session.flush()

        profile = StyleProfile(
            name="Test Profile",
            loras=[{"lora_id": lora.id, "weight": 0.8}],
            default_positive="masterpiece, best quality",
            default_negative="worst quality",
        )
        db_session.add(profile)
        db_session.flush()

        group = Group(
            name="Test Group",
            project_id=project.id,
        )
        db_session.add(group)
        db_session.flush()

        group_config = GroupConfig(
            group_id=group.id,
            style_profile_id=profile.id,
        )
        db_session.add(group_config)
        db_session.flush()

        char_lora = LoRA(
            name="test_char_lora",
            trigger_words=["test_char"],
            lora_type="character",
        )
        db_session.add(char_lora)
        db_session.flush()

        character = Character(
            name="Test Char",
            project_id=project.id,
            loras=[{"lora_id": char_lora.id, "weight": 1.0}],
        )
        db_session.add(character)
        db_session.commit()

        fake_b64 = _make_tiny_png_b64()
        mock_sd_response = MagicMock()
        mock_sd_response.status_code = 200
        mock_sd_response.json.return_value = {
            "images": [fake_b64],
            "info": '{"seed": 12345}',
        }

        with patch("services.image_generation_core.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_sd_response)
            mock_client_cls.return_value = mock_client

            result = await generate_image_with_v3(
                db=db_session,
                prompt=["1girl", "smile"],
                character_id=character.id,
                group_id=group.id,
                sd_params={"steps": 20, "cfg_scale": 7},
                mode="lab",
            )

        assert isinstance(result, ImageGenerationResult)
        assert result.image == fake_b64
        assert result.seed == 12345
        assert result.final_prompt is not None
        assert len(result.loras_applied) >= 1  # At least character LoRA

    @pytest.mark.asyncio
    async def test_generate_lab_mode_continues_on_error(self, db_session):
        """Lab mode: SD API failure -> return partial result with warnings."""
        from models import Project
        from models.group import Group

        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        group = Group(name="Test Group", project_id=project.id)
        db_session.add(group)
        db_session.commit()

        with patch("services.image_generation_core.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client_cls.return_value = mock_client

            result = await generate_image_with_v3(
                db=db_session,
                prompt=["1girl"],
                group_id=group.id,
                mode="lab",
            )

        # Lab mode: returns partial result instead of raising
        assert isinstance(result, ImageGenerationResult)
        assert result.image == ""
        assert result.seed == -1
        assert len(result.warnings) > 0
        assert "SD API failed" in result.warnings[0]

    @pytest.mark.asyncio
    async def test_generate_studio_mode_raises_on_error(self, db_session):
        """Studio mode: SD API failure -> raises exception."""
        from models import Project
        from models.group import Group

        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        group = Group(name="Test Group", project_id=project.id)
        db_session.add(group)
        db_session.commit()

        with patch("services.image_generation_core.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client_cls.return_value = mock_client

            with pytest.raises(Exception, match="Connection refused"):
                await generate_image_with_v3(
                    db=db_session,
                    prompt=["1girl"],
                    group_id=group.id,
                    mode="studio",
                )

    @pytest.mark.asyncio
    async def test_generate_without_character(self, db_session):
        """Generate without character LoRA (narrator experiment)."""
        from models import Project
        from models.group import Group

        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        group = Group(name="Test Group", project_id=project.id)
        db_session.add(group)
        db_session.commit()

        fake_b64 = _make_tiny_png_b64()
        mock_sd_response = MagicMock()
        mock_sd_response.status_code = 200
        mock_sd_response.json.return_value = {
            "images": [fake_b64],
            "info": '{"seed": 99}',
        }

        with patch("services.image_generation_core.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_sd_response)
            mock_client_cls.return_value = mock_client

            result = await generate_image_with_v3(
                db=db_session,
                prompt="landscape, sunset",
                character_id=None,
                group_id=group.id,
                mode="lab",
            )

        assert result.image == fake_b64
        assert result.seed == 99
        # No character LoRA, but prompt should still work
        assert result.final_prompt is not None


class TestResolveStyleLorasFromGroup:
    """Test resolve_style_loras_from_group() -- Group Config → Style LoRAs."""

    def test_resolve_loras_from_group_config(self, db_session):
        """Group with Style Profile → LoRAs resolved."""
        from models import LoRA, Project, StyleProfile
        from models.group import Group
        from models.group_config import GroupConfig

        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        lora = LoRA(
            name="anime_style",
            trigger_words=["anime"],
            lora_type="style",
        )
        db_session.add(lora)
        db_session.flush()

        profile = StyleProfile(
            name="Anime Profile",
            loras=[{"lora_id": lora.id, "weight": 0.7}],
        )
        db_session.add(profile)
        db_session.flush()

        group = Group(
            name="Test Group",
            project_id=project.id,
        )
        db_session.add(group)
        db_session.flush()

        group_config = GroupConfig(
            group_id=group.id,
            style_profile_id=profile.id,
        )
        db_session.add(group_config)
        db_session.commit()

        loras = resolve_style_loras_from_group(group.id, db_session)

        assert len(loras) == 1
        assert loras[0]["name"] == "anime_style"
        assert loras[0]["weight"] == 0.7
        assert "anime" in loras[0]["trigger_words"]

    def test_resolve_no_config(self, db_session):
        """Group without config → empty list."""
        from models import Project
        from models.group import Group

        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        group = Group(name="Empty Group", project_id=project.id)
        db_session.add(group)
        db_session.commit()

        loras = resolve_style_loras_from_group(group.id, db_session)

        assert loras == []


class TestResolveStyleLorasFromStoryboard:
    """Test resolve_style_loras_from_storyboard() -- Storyboard → Group → LoRAs."""

    def test_resolve_via_storyboard(self, db_session):
        """Storyboard → Group → Style Profile → LoRAs."""
        from models import LoRA, Project, Storyboard, StyleProfile
        from models.group import Group
        from models.group_config import GroupConfig

        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        lora = LoRA(
            name="comic_style",
            trigger_words=["comic"],
            lora_type="style",
        )
        db_session.add(lora)
        db_session.flush()

        profile = StyleProfile(
            name="Comic Profile",
            loras=[{"lora_id": lora.id, "weight": 0.9}],
        )
        db_session.add(profile)
        db_session.flush()

        group = Group(
            name="Comic Group",
            project_id=project.id,
        )
        db_session.add(group)
        db_session.flush()

        group_config = GroupConfig(
            group_id=group.id,
            style_profile_id=profile.id,
        )
        db_session.add(group_config)
        db_session.flush()

        storyboard = Storyboard(
            title="Test Storyboard",
            group_id=group.id,
        )
        db_session.add(storyboard)
        db_session.commit()

        loras = resolve_style_loras_from_storyboard(storyboard.id, db_session)

        assert len(loras) == 1
        assert loras[0]["name"] == "comic_style"
        assert loras[0]["weight"] == 0.9

    def test_resolve_storyboard_no_config(self, db_session):
        """Storyboard with Group but no Style Profile → empty list."""
        from models import Project, Storyboard
        from models.group import Group

        project = Project(name="Test Project")
        db_session.add(project)
        db_session.flush()

        group = Group(name="Empty Group", project_id=project.id)
        db_session.add(group)
        db_session.flush()

        storyboard = Storyboard(
            title="Orphan Storyboard",
            group_id=group.id,
        )
        db_session.add(storyboard)
        db_session.commit()

        loras = resolve_style_loras_from_storyboard(storyboard.id, db_session)

        assert loras == []
