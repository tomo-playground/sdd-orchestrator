"""
TDD tests for image_generation_core -- unified Prompt Engine + SD integration.

Phase 1: Lab + Studio unified image generation.
"""

import base64
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from PIL import Image

from services.image_generation_core import (
    ImageGenerationResult,
    compose_scene_with_style,
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
            style_profile_id=profile.id,
        )
        db_session.add(group)
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
            group_id=1,
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
        assert any("SD API failed" in w for w in result.warnings)

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


class TestComposeSceneWithStyle:
    """Test compose_scene_with_style() -- shared SSOT for Studio + Creative Lab."""

    def test_calls_style_profile_then_v3(self):
        """Must call apply_style_profile_to_prompt(skip_loras=True) then V3 compose."""
        mock_db = MagicMock()
        # Character query returns mock (no scene_negative_prompt → no merge)
        mock_char = MagicMock()
        mock_char.id = 10
        mock_char.scene_negative_prompt = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_char

        with (
            patch("services.image_generation_core.PromptBuilder") as MockBuilder,
            patch("services.generation.apply_style_profile_to_prompt") as mock_apply,
        ):
            mock_apply.return_value = ("high_quality, 1girl, smile", "lowres, bad anatomy")
            mock_instance = MagicMock()
            mock_instance.compose_for_character.return_value = "masterpiece, best_quality, high_quality, 1girl"
            mock_instance.find_unknown_tags.return_value = []
            MockBuilder.return_value = mock_instance

            composed, negative, warnings = compose_scene_with_style(
                raw_prompt="1girl, smile",
                negative_prompt="lowres",
                character_id=10,
                storyboard_id=42,
                style_loras=[{"name": "flat_color", "weight": 0.76}],
                db=mock_db,
            )

            # 1. Style profile called with skip_loras=True
            mock_apply.assert_called_once()
            call_kwargs = mock_apply.call_args
            assert call_kwargs[0][2] == 42  # storyboard_id
            assert call_kwargs[1]["skip_loras"] is True

            # 2. V3 compose_for_character called with styled prompt tags
            mock_instance.compose_for_character.assert_called_once()

            assert composed == "masterpiece, best_quality, high_quality, 1girl"
            assert "bad anatomy" in negative
            assert warnings == []

    def test_no_character_uses_generic_compose(self):
        """When character_id is None, must use builder.compose (not compose_for_character)."""
        mock_db = MagicMock()

        with (
            patch("services.image_generation_core.PromptBuilder") as MockBuilder,
            patch("services.generation.apply_style_profile_to_prompt") as mock_apply,
        ):
            mock_apply.return_value = ("no_humans, sunset", "lowres")
            mock_instance = MagicMock()
            mock_instance.compose.return_value = "no_humans, sunset, masterpiece"
            mock_instance.find_unknown_tags.return_value = []
            MockBuilder.return_value = mock_instance

            composed, _, _warnings = compose_scene_with_style(
                raw_prompt="no_humans, sunset",
                negative_prompt="lowres",
                character_id=None,
                storyboard_id=42,
                style_loras=[],
                db=mock_db,
            )

            mock_instance.compose.assert_called_once()
            mock_instance.compose_for_character.assert_not_called()
            assert "sunset" in composed

    def test_negative_prompt_dedup(self):
        """Duplicate tokens in negative prompt must be removed."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with (
            patch("services.image_generation_core.PromptBuilder") as MockBuilder,
            patch("services.generation.apply_style_profile_to_prompt") as mock_apply,
        ):
            # Style profile returns negative with duplicates
            mock_apply.return_value = (
                "1girl, smile",
                "lowres, bad anatomy, lowres, worst quality, bad anatomy",
            )
            mock_instance = MagicMock()
            mock_instance.compose_for_character.return_value = "1girl, smile"
            mock_instance.find_unknown_tags.return_value = []
            MockBuilder.return_value = mock_instance

            _, negative, _warnings = compose_scene_with_style(
                raw_prompt="1girl, smile",
                negative_prompt="lowres",
                character_id=10,
                storyboard_id=42,
                style_loras=[],
                db=mock_db,
            )

            # Duplicates removed, each token appears exactly once
            tokens = [t.strip() for t in negative.split(",")]
            assert tokens == ["lowres", "bad anatomy", "worst quality"]

    def test_unknown_tags_warning(self):
        """Non-Danbooru tags must be reported in warnings."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with (
            patch("services.image_generation_core.PromptBuilder") as MockBuilder,
            patch("services.generation.apply_style_profile_to_prompt") as mock_apply,
        ):
            mock_apply.return_value = ("1girl, vibrant_colors", "lowres")
            mock_instance = MagicMock()
            mock_instance.compose_for_character.return_value = "1girl, vibrant_colors"
            mock_instance.find_unknown_tags.return_value = ["vibrant_colors"]
            MockBuilder.return_value = mock_instance

            _, _, warnings = compose_scene_with_style(
                raw_prompt="1girl, vibrant_colors",
                negative_prompt="lowres",
                character_id=10,
                storyboard_id=42,
                style_loras=[],
                db=mock_db,
            )

            assert len(warnings) == 1
            assert "Non-Danbooru tags detected" in warnings[0]
            assert "vibrant_colors" in warnings[0]

    def test_character_scene_negative_prompt_merged(self):
        """Character scene_negative_prompt must be merged into negative."""
        mock_db = MagicMock()
        mock_char = MagicMock()
        mock_char.scene_negative_prompt = "nsfw, revealing_clothes"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_char

        with (
            patch("services.image_generation_core.PromptBuilder") as MockBuilder,
            patch("services.generation.apply_style_profile_to_prompt") as mock_apply,
        ):
            mock_apply.return_value = ("1girl, smile", "lowres, bad anatomy")
            mock_instance = MagicMock()
            mock_instance.compose_for_character.return_value = "1girl, smile"
            mock_instance.find_unknown_tags.return_value = []
            MockBuilder.return_value = mock_instance

            _, negative, _ = compose_scene_with_style(
                raw_prompt="1girl, smile",
                negative_prompt="lowres",
                character_id=10,
                storyboard_id=42,
                style_loras=[],
                db=mock_db,
            )

            assert "nsfw" in negative
            assert "revealing_clothes" in negative
            assert "lowres" in negative
            assert "bad anatomy" in negative

    def test_common_negative_prompts_merged(self):
        """Character common_negative_prompts (list[str]) must be merged into negative."""
        mock_db = MagicMock()
        mock_char = MagicMock()
        mock_char.scene_negative_prompt = None
        mock_char.common_negative_prompts = ["verybadimagenegative_v1.3", "easynegative"]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_char

        with (
            patch("services.image_generation_core.PromptBuilder") as MockBuilder,
            patch("services.generation.apply_style_profile_to_prompt") as mock_apply,
        ):
            mock_apply.return_value = ("1girl, smile", "lowres")
            mock_instance = MagicMock()
            mock_instance.compose_for_character.return_value = "1girl, smile"
            mock_instance.find_unknown_tags.return_value = []
            MockBuilder.return_value = mock_instance

            _, negative, _ = compose_scene_with_style(
                raw_prompt="1girl, smile",
                negative_prompt="lowres",
                character_id=10,
                storyboard_id=42,
                style_loras=[],
                db=mock_db,
            )

            assert "verybadimagenegative_v1.3" in negative
            assert "easynegative" in negative
            assert "lowres" in negative

    def test_char_b_custom_negative_merged(self):
        """Multi-char scene: char_b's scene_negative_prompt must be merged."""
        mock_db = MagicMock()

        mock_char_a = MagicMock()
        mock_char_a.id = 10
        mock_char_a.scene_negative_prompt = "nsfw"
        mock_char_a.common_negative_prompts = None

        mock_char_b = MagicMock()
        mock_char_b.id = 20
        mock_char_b.scene_negative_prompt = "muscular, facial_hair"
        mock_char_b.common_negative_prompts = None

        # DB query chain: first call → char_a, second → char_b
        chars_by_call = iter([mock_char_a, mock_char_b])
        mock_db.query.return_value.filter.return_value.first.side_effect = lambda: next(chars_by_call)

        with (
            patch("services.image_generation_core.PromptBuilder") as MockBuilder,
            patch("services.generation.apply_style_profile_to_prompt") as mock_apply,
            patch("services.prompt.multi_character.MultiCharacterComposer") as MockComposer,
            patch("services.style_context.resolve_style_context", return_value=None),
        ):
            mock_apply.return_value = ("1boy, 1girl", "lowres")
            mock_instance = MagicMock()
            mock_instance.find_unknown_tags.return_value = []
            mock_instance.warnings = []
            MockBuilder.return_value = mock_instance
            mock_composer_instance = MagicMock()
            mock_composer_instance.compose.return_value = "1boy, 1girl"
            MockComposer.return_value = mock_composer_instance

            _, negative, _ = compose_scene_with_style(
                raw_prompt="1boy, 1girl",
                negative_prompt="lowres",
                character_id=10,
                storyboard_id=42,
                style_loras=[],
                db=mock_db,
                character_b_id=20,
            )

            assert "nsfw" in negative
            assert "muscular" in negative
            assert "facial_hair" in negative
            assert "lowres" in negative


class TestEnsureCorrectCheckpoint:
    """Test _ensure_correct_checkpoint() — SD WebUI checkpoint auto-switch."""

    @pytest.mark.asyncio
    async def test_skip_when_checkpoint_already_matches(self):
        """No POST when current checkpoint already matches."""
        from services.image_generation_core import _ensure_correct_checkpoint

        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {"sd_model_checkpoint": "realisticVisionV60.safetensors"}

        with patch("services.image_generation_core.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_get_resp
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await _ensure_correct_checkpoint("realisticVisionV60")

            mock_client.get.assert_called_once()
            mock_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_switch_when_checkpoint_differs(self):
        """POST to switch checkpoint when current model is different."""
        from services.image_generation_core import _ensure_correct_checkpoint

        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {"sd_model_checkpoint": "animeModel_v3.safetensors"}

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200

        with patch("services.image_generation_core.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_get_resp
            mock_client.post.return_value = mock_post_resp
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await _ensure_correct_checkpoint("realisticVisionV60")

            mock_client.post.assert_called_once()
            call_kwargs = mock_client.post.call_args
            assert call_kwargs[1]["json"]["sd_model_checkpoint"] == "realisticVisionV60"

    @pytest.mark.asyncio
    async def test_non_blocking_on_failure(self):
        """Connection error must not raise — just log warning."""
        from services.image_generation_core import _ensure_correct_checkpoint

        with patch("services.image_generation_core.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("SD WebUI offline")
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            # Must not raise
            await _ensure_correct_checkpoint("realisticVisionV60")


class TestComposeWarningsMerge:
    """Test that builder.warnings are merged into compose_scene_with_style return."""

    def test_builder_warnings_propagated(self):
        """LoRA compatibility warnings from builder must appear in returned warnings."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with (
            patch("services.image_generation_core.PromptBuilder") as MockBuilder,
            patch("services.generation.apply_style_profile_to_prompt") as mock_apply,
            patch("services.style_context.resolve_style_context", return_value=None),
        ):
            mock_apply.return_value = ("1girl, smile", "lowres")
            mock_instance = MagicMock()
            mock_instance.compose.return_value = "1girl, smile"
            mock_instance.find_unknown_tags.return_value = []
            mock_instance.warnings = ["LoRA 'char_lora' (base: SDXL) may be incompatible with checkpoint (base: SD1.5)"]
            MockBuilder.return_value = mock_instance

            _, _, warnings = compose_scene_with_style(
                raw_prompt="1girl, smile",
                negative_prompt="lowres",
                character_id=None,
                storyboard_id=42,
                style_loras=[],
                db=mock_db,
            )

            assert len(warnings) == 1
            assert "incompatible" in warnings[0]
            assert "char_lora" in warnings[0]


class TestComposeNegativeOrder:
    """_compose_negative should place default_negative before user input."""

    def test_default_negative_comes_first(self):
        """default_negative should precede user negative prompt."""
        from services.generation_style import _compose_negative

        class FakeCtx:
            negative_embeddings = []
            default_negative = "EasyNegative"

        result = _compose_negative(FakeCtx(), "blurry, lowres")
        tokens = [t.strip() for t in result.split(",")]
        assert tokens[0] == "EasyNegative"

    def test_embeddings_between_default_and_user(self):
        """Order: default_negative > embeddings > user negative."""
        from services.generation_style import _compose_negative

        class FakeCtx:
            negative_embeddings = ["embedding:negV2"]
            default_negative = "EasyNegative"

        result = _compose_negative(FakeCtx(), "blurry")
        tokens = [t.strip() for t in result.split(",")]
        assert tokens.index("EasyNegative") < tokens.index("embedding:negV2")
        assert tokens.index("embedding:negV2") < tokens.index("blurry")

    def test_empty_user_negative(self):
        """No user negative → only default + embeddings."""
        from services.generation_style import _compose_negative

        class FakeCtx:
            negative_embeddings = ["embedding:negV2"]
            default_negative = "lowres"

        result = _compose_negative(FakeCtx(), "")
        assert "lowres" in result
        assert "embedding:negV2" in result


class TestResolveStyleLorasFromGroup:
    """Test resolve_style_loras_from_group() -- Group Config → Style LoRAs."""

    def test_resolve_loras_from_group(self, db_session):
        """Group with Style Profile → LoRAs resolved."""
        from models import LoRA, Project, StyleProfile
        from models.group import Group

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
            style_profile_id=profile.id,
        )
        db_session.add(group)
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
            style_profile_id=profile.id,
        )
        db_session.add(group)
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
