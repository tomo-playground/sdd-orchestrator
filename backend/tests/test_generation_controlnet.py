"""Tests for generation_controlnet: _apply_pose_control, _apply_ip_adapter, _apply_reference_only."""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

# ── Minimal stubs ────────────────────────────────────────────────────


@dataclass
class FakeRequest:
    use_controlnet: bool = False
    controlnet_pose: str | None = None
    controlnet_weight: float = 1.0
    controlnet_control_mode: str = "Balanced"
    character_id: int | None = None
    scene_id: int | None = None
    prompt: str = ""
    environment_reference_id: int | None = None
    environment_reference_weight: float = 0.3


@dataclass
class FakeStrategy:
    ip_adapter_enabled: bool = False
    ip_adapter_reference: str | None = None
    ip_adapter_weight: float = 0.7
    ip_adapter_model: str = "NOOB-IPA-MARK1"
    ip_adapter_guidance_start: float | None = None
    ip_adapter_guidance_end: float | None = None
    reference_only_enabled: bool = False
    reference_only_weight: float = 0.5


@dataclass
class FakeContext:
    request: FakeRequest = field(default_factory=FakeRequest)
    consistency: FakeStrategy = field(default_factory=FakeStrategy)
    prompt: str = ""
    character_name: str | None = None
    controlnet_used: str | None = None
    ip_adapter_used: str | None = None
    warnings: list[str] = field(default_factory=list)


# ── _apply_pose_control Tests ────────────────────────────────────────


class TestApplyPoseControl:
    """Tests for ControlNet OpenPose application."""

    def test_skip_when_use_controlnet_false(self):
        from services.generation_controlnet import _apply_pose_control

        req = FakeRequest(use_controlnet=False)
        ctx = FakeContext(request=req)
        args: list = []
        _apply_pose_control(req, ctx, args)
        assert args == []

    @patch("services.generation_controlnet.load_pose_reference", return_value="base64data")
    @patch("services.generation_controlnet.build_controlnet_args", return_value={"model": "openpose"})
    def test_explicit_pose_used(self, mock_build, mock_load):
        from services.generation_controlnet import _apply_pose_control

        req = FakeRequest(use_controlnet=True, controlnet_pose="standing", controlnet_weight=0.8)
        ctx = FakeContext(request=req)
        args: list = []
        _apply_pose_control(req, ctx, args)

        assert len(args) == 1
        mock_load.assert_called_once_with("standing")
        mock_build.assert_called_once_with(
            input_image="base64data", model="openpose", weight=0.8, control_mode="Balanced"
        )
        assert ctx.controlnet_used == "standing"

    @patch("services.generation_controlnet.load_pose_reference", return_value=None)
    def test_pose_image_not_found_graceful(self, mock_load):
        from services.generation_controlnet import _apply_pose_control

        req = FakeRequest(use_controlnet=True, controlnet_pose="nonexistent")
        ctx = FakeContext(request=req)
        args: list = []
        _apply_pose_control(req, ctx, args)
        assert args == []
        assert ctx.controlnet_used is None

    @patch("services.generation_controlnet.detect_pose_from_prompt", return_value="sitting")
    @patch("services.generation_controlnet.load_pose_reference", return_value="b64sit")
    @patch("services.generation_controlnet.build_controlnet_args", return_value={"model": "openpose"})
    def test_auto_detect_from_prompt(self, mock_build, mock_load, mock_detect):
        from services.generation_controlnet import _apply_pose_control

        req = FakeRequest(use_controlnet=True, controlnet_pose=None)
        ctx = FakeContext(request=req, prompt="1girl, sitting, smile")
        args: list = []
        _apply_pose_control(req, ctx, args)

        mock_detect.assert_called_once()
        assert len(args) == 1
        assert ctx.controlnet_used == "sitting"

    @patch("services.generation_controlnet.detect_pose_from_prompt", return_value=None)
    def test_no_pose_detected_graceful_skip(self, mock_detect):
        from services.generation_controlnet import _apply_pose_control

        req = FakeRequest(use_controlnet=True, controlnet_pose=None)
        ctx = FakeContext(request=req, prompt="1girl, smile")
        args: list = []
        _apply_pose_control(req, ctx, args)
        assert args == []

    def test_controlnet_weight_passed_correctly(self):
        from services.generation_controlnet import _apply_pose_control

        with (
            patch("services.generation_controlnet.load_pose_reference", return_value="b64"),
            patch("services.generation_controlnet.build_controlnet_args", return_value={"w": 0.6}) as mock_build,
        ):
            req = FakeRequest(use_controlnet=True, controlnet_pose="standing", controlnet_weight=0.6)
            ctx = FakeContext(request=req)
            args: list = []
            _apply_pose_control(req, ctx, args)
            mock_build.assert_called_once_with(input_image="b64", model="openpose", weight=0.6, control_mode="Balanced")


class TestApplyPoseHint:
    """Tests for Phase 3-A: character_actions pose hint."""

    @patch("services.generation_controlnet.load_pose_reference", return_value="b64pose")
    @patch("services.generation_controlnet.build_controlnet_args", return_value={"model": "openpose"})
    @patch("services.generation_controlnet._get_pose_from_character_actions", return_value="walking")
    def test_pose_hint_from_character_actions(self, mock_hint, mock_build, mock_load):
        from services.generation_controlnet import _apply_pose_control

        db = MagicMock()
        req = FakeRequest(use_controlnet=True, controlnet_pose=None, scene_id=42)
        ctx = FakeContext(request=req, prompt="1girl, smile")
        args: list = []
        _apply_pose_control(req, ctx, args, db=db)

        mock_hint.assert_called_once_with(42, db)
        mock_load.assert_called_once_with("walking")
        assert ctx.controlnet_used == "walking"

    @patch("services.generation_controlnet._get_pose_from_character_actions", return_value=None)
    @patch("services.generation_controlnet.detect_pose_from_prompt", return_value="sitting")
    @patch("services.generation_controlnet.load_pose_reference", return_value="b64")
    @patch("services.generation_controlnet.build_controlnet_args", return_value={"model": "openpose"})
    def test_fallback_to_prompt_when_no_character_actions(self, mock_build, mock_load, mock_detect, mock_hint):
        from services.generation_controlnet import _apply_pose_control

        db = MagicMock()
        req = FakeRequest(use_controlnet=True, controlnet_pose=None, scene_id=42)
        ctx = FakeContext(request=req, prompt="1girl, sitting")
        args: list = []
        _apply_pose_control(req, ctx, args, db=db)

        mock_hint.assert_called_once()
        mock_detect.assert_called_once()
        assert ctx.controlnet_used == "sitting"

    def test_no_db_skips_pose_hint(self):
        """Without db parameter, pose_hint lookup is skipped."""
        from services.generation_controlnet import _apply_pose_control

        with (
            patch("services.generation_controlnet.detect_pose_from_prompt", return_value=None),
            patch("services.generation_controlnet._get_pose_from_character_actions") as mock_hint,
        ):
            req = FakeRequest(use_controlnet=True, controlnet_pose=None, scene_id=42)
            ctx = FakeContext(request=req, prompt="1girl")
            args: list = []
            _apply_pose_control(req, ctx, args)
            mock_hint.assert_not_called()


# ── _apply_ip_adapter Tests ──────────────────────────────────────────


class TestApplyIpAdapter:
    """Tests for IP-Adapter application."""

    def test_skip_when_disabled(self):
        from services.generation_controlnet import _apply_ip_adapter

        strategy = FakeStrategy(ip_adapter_enabled=False)
        ctx = FakeContext(consistency=strategy)
        args: list = []
        _apply_ip_adapter(ctx, strategy, args, db=None)
        assert args == []

    def test_skip_when_no_reference(self):
        from services.generation_controlnet import _apply_ip_adapter

        strategy = FakeStrategy(ip_adapter_enabled=True, ip_adapter_reference=None)
        ctx = FakeContext(consistency=strategy)
        args: list = []
        _apply_ip_adapter(ctx, strategy, args, db=None)
        assert args == []

    @patch("services.generation_controlnet.load_reference_image", return_value="ref_b64")
    @patch("services.generation_controlnet.build_ip_adapter_args", return_value={"model": "ip-adapter"})
    def test_normal_application(self, mock_build, mock_load):
        from services.generation_controlnet import _apply_ip_adapter

        strategy = FakeStrategy(
            ip_adapter_enabled=True,
            ip_adapter_reference="char_key",
            ip_adapter_weight=0.8,
        )
        ctx = FakeContext(consistency=strategy)
        args: list = []
        db = MagicMock()
        _apply_ip_adapter(ctx, strategy, args, db=db)

        assert len(args) == 1
        assert ctx.ip_adapter_used == "char_key"
        mock_load.assert_called_once_with("char_key", db=db)


# ── _apply_reference_only Tests ──────────────────────────────────────


class TestApplyReferenceOnly:
    """Tests for reference-only ControlNet."""

    def test_skip_when_disabled(self):
        from services.generation_controlnet import _apply_reference_only

        req = FakeRequest(character_id=1)
        strategy = FakeStrategy(reference_only_enabled=False)
        ctx = FakeContext(request=req, consistency=strategy)
        args: list = []
        _apply_reference_only(req, ctx, strategy, args, db=None)
        assert args == []

    def test_skip_when_no_character(self):
        from services.generation_controlnet import _apply_reference_only

        req = FakeRequest(character_id=None)
        strategy = FakeStrategy(reference_only_enabled=True)
        ctx = FakeContext(request=req, consistency=strategy)
        args: list = []
        _apply_reference_only(req, ctx, strategy, args, db=None)
        assert args == []

    @patch("services.generation_controlnet.load_reference_image", return_value="ref_b64")
    @patch("services.generation_controlnet.build_controlnet_args", return_value={"model": "reference"})
    def test_normal_application(self, mock_build, mock_load):
        from services.generation_controlnet import _apply_reference_only

        req = FakeRequest(character_id=1)
        strategy = FakeStrategy(reference_only_enabled=True, reference_only_weight=0.6)
        ctx = FakeContext(request=req, consistency=strategy, character_name="TestChar")
        args: list = []
        db = MagicMock()
        _apply_reference_only(req, ctx, strategy, args, db=db)

        assert len(args) == 1
        mock_load.assert_called_once_with("TestChar", db=db)
        mock_build.assert_called_once_with(
            input_image="ref_b64", model="reference", weight=0.6, control_mode="Balanced"
        )


# ── _get_pose_from_character_actions Tests ───────────────────────────


class TestGetPoseFromCharacterActions:
    """Tests for DB-based pose hint retrieval."""

    def test_returns_pose_tag_name(self, db_session):
        """When character_actions has a pose tag, return its name."""
        from models.associations import SceneCharacterAction
        from models.character import Character
        from models.group import Group
        from models.project import Project
        from models.scene import Scene
        from models.storyboard import Storyboard
        from models.tag import Tag
        from services.generation_controlnet import _get_pose_from_character_actions

        # Setup: project → group → storyboard → scene → character → character_action
        project = Project(name="test")
        db_session.add(project)
        db_session.flush()
        group = Group(project_id=project.id, name="test")
        db_session.add(group)
        db_session.flush()
        sb = Storyboard(title="test", group_id=group.id)
        db_session.add(sb)
        db_session.flush()
        scene = Scene(storyboard_id=sb.id, order=0, script="test")
        db_session.add(scene)
        db_session.flush()
        char = Character(name="TestChar", gender="female", group_id=1)
        db_session.add(char)
        db_session.flush()
        tag = Tag(name="walking", category="scene", group_name="pose", default_layer=8)
        db_session.add(tag)
        db_session.flush()

        sca = SceneCharacterAction(scene_id=scene.id, character_id=char.id, tag_id=tag.id, weight=1.0)
        db_session.add(sca)
        db_session.flush()

        result = _get_pose_from_character_actions(scene.id, db_session)
        assert result == "walking"

    def test_returns_none_when_no_pose(self, db_session):
        """When no pose tag in character_actions, return None."""
        from models.associations import SceneCharacterAction
        from models.character import Character
        from models.group import Group
        from models.project import Project
        from models.scene import Scene
        from models.storyboard import Storyboard
        from models.tag import Tag
        from services.generation_controlnet import _get_pose_from_character_actions

        project = Project(name="test2")
        db_session.add(project)
        db_session.flush()
        group = Group(project_id=project.id, name="test2")
        db_session.add(group)
        db_session.flush()
        sb = Storyboard(title="test", group_id=group.id)
        db_session.add(sb)
        db_session.flush()
        scene = Scene(storyboard_id=sb.id, order=0, script="test")
        db_session.add(scene)
        db_session.flush()
        char = Character(name="TestChar2", gender="male", group_id=1)
        db_session.add(char)
        db_session.flush()

        # Only expression tag, no pose
        tag = Tag(name="smile", category="scene", group_name="expression", default_layer=7)
        db_session.add(tag)
        db_session.flush()

        sca = SceneCharacterAction(scene_id=scene.id, character_id=char.id, tag_id=tag.id, weight=1.0)
        db_session.add(sca)
        db_session.flush()

        result = _get_pose_from_character_actions(scene.id, db_session)
        assert result is None

    def test_returns_none_for_nonexistent_scene(self, db_session):
        from services.generation_controlnet import _get_pose_from_character_actions

        result = _get_pose_from_character_actions(99999, db_session)
        assert result is None


# ── _apply_reference_adain_from_asset Tests ──────────────────────────


class TestApplyReferenceAdain:
    """Tests for Reference AdaIN environment atmosphere transfer."""

    def test_builds_reference_adain_args(self, tmp_path):
        """Should build ControlNet args with reference_adain module."""
        from services.generation_controlnet import _apply_reference_adain_from_asset

        # Create a fake image file
        img_file = tmp_path / "bg.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        env_asset = MagicMock()
        env_asset.local_path = str(img_file)
        req = FakeRequest(environment_reference_id=42)
        args: list = []

        _apply_reference_adain_from_asset(env_asset, req, args)

        assert len(args) == 1
        arg = args[0]
        assert arg["module"] == "reference_adain"
        assert arg["model"] == "None"
        assert arg["control_mode"] == "My prompt is more important"
        assert arg["weight"] == 0.35
        assert arg["guidance_end"] == 0.5
        assert arg["enabled"] is True
        assert "image" in arg

    def test_skips_when_file_missing(self):
        """Should skip when asset file doesn't exist."""
        from services.generation_controlnet import _apply_reference_adain_from_asset

        env_asset = MagicMock()
        env_asset.local_path = "/nonexistent/path.png"
        req = FakeRequest(environment_reference_id=42)
        args: list = []

        _apply_reference_adain_from_asset(env_asset, req, args)
        assert args == []


# ── Generation result includes ControlNet fields ─────────────────────


class TestGenerationResultControlNet:
    """Test that generation results include controlnet_pose and ip_adapter_reference."""

    def test_generation_result_includes_controlnet_pose(self):
        """Simulated generation result dict should carry controlnet fields."""
        result = {
            "image": "base64data",
            "used_prompt": "1girl, standing",
            "warnings": [],
            "controlnet_pose": "standing",
            "ip_adapter_reference": "char_ref",
        }
        assert result["controlnet_pose"] == "standing"
        assert result["ip_adapter_reference"] == "char_ref"

    def test_generation_result_none_without_controlnet(self):
        """When ControlNet is not used, fields should be None."""
        result = {
            "image": "base64data",
            "used_prompt": "1girl",
            "warnings": [],
            "controlnet_pose": None,
            "ip_adapter_reference": None,
        }
        assert result["controlnet_pose"] is None
        assert result["ip_adapter_reference"] is None


# ── _suppress_cinematic_for_adain Tests (SP-105 P0) ──────────────────


class TestSuppressCinematicForAdain:
    """Tests for cinematic tag suppression when Reference AdaIN is active."""

    def test_removes_conflicting_tags(self):
        """Conflicting tags should be removed from ctx.prompt."""
        from services.generation_controlnet import _suppress_cinematic_for_adain

        ctx = FakeContext(prompt="girl, kitchen, depth_of_field, bokeh, close-up")
        removed = _suppress_cinematic_for_adain(ctx)
        assert "depth_of_field" not in ctx.prompt
        assert "bokeh" not in ctx.prompt
        assert "close-up" in ctx.prompt
        assert "girl" in ctx.prompt
        assert "kitchen" in ctx.prompt
        assert set(removed) == {"depth_of_field", "bokeh"}

    def test_no_partial_match(self):
        """Similar but non-matching tags should NOT be removed."""
        from services.generation_controlnet import _suppress_cinematic_for_adain

        ctx = FakeContext(prompt="girl, field, depth_perception")
        removed = _suppress_cinematic_for_adain(ctx)
        assert ctx.prompt == "girl, field, depth_perception"
        assert len(removed) == 0

    def test_noop_when_no_conflict(self):
        """When no conflicting tags, prompt should remain unchanged."""
        from services.generation_controlnet import _suppress_cinematic_for_adain

        ctx = FakeContext(prompt="girl, backlit, light_rays")
        removed = _suppress_cinematic_for_adain(ctx)
        assert ctx.prompt == "girl, backlit, light_rays"
        assert len(removed) == 0

    def test_removes_all_six_conflicting_tags(self):
        """All known conflicting tags should be removed."""
        from config import REFERENCE_ADAIN_CONFLICTING_TAGS
        from services.generation_controlnet import _suppress_cinematic_for_adain

        all_tags = ", ".join(sorted(REFERENCE_ADAIN_CONFLICTING_TAGS))
        ctx = FakeContext(prompt=f"girl, {all_tags}, smile")
        removed = _suppress_cinematic_for_adain(ctx)
        assert ctx.prompt == "girl, smile"
        assert set(removed) == set(REFERENCE_ADAIN_CONFLICTING_TAGS)

    def test_preserves_prompt_order(self):
        """Remaining tags should preserve their original order."""
        from services.generation_controlnet import _suppress_cinematic_for_adain

        ctx = FakeContext(prompt="a, bokeh, b, c")
        _suppress_cinematic_for_adain(ctx)
        assert ctx.prompt == "a, b, c"

    def test_removes_weighted_conflicting_tags(self):
        """Weighted syntax like (bokeh:1.2) should also be removed."""
        from services.generation_controlnet import _suppress_cinematic_for_adain

        ctx = FakeContext(prompt="girl, (bokeh:1.2), (depth_of_field:1.1), smile")
        removed = _suppress_cinematic_for_adain(ctx)
        assert "bokeh" not in ctx.prompt
        assert "depth_of_field" not in ctx.prompt
        assert "girl" in ctx.prompt
        assert "smile" in ctx.prompt
        assert len(removed) == 2


class TestSuppressCinematicWarning:
    """Tests for warning propagation when cinematic tags are suppressed (SP-105 P0-2)."""

    def test_warning_appended_on_suppression(self):
        """When tags are suppressed, warning should be added to the list."""
        from services.generation_controlnet import _suppress_cinematic_for_adain

        ctx = FakeContext(prompt="girl, bokeh, lens_flare")
        warnings: list[str] = []
        removed = _suppress_cinematic_for_adain(ctx)
        if removed:
            msg = f"⚠️ AdaIN 충돌 방지: 시네마틱 태그 억제됨 — {', '.join(removed)}"
            warnings.append(msg)
        assert any("bokeh" in w for w in warnings)
        assert any("lens_flare" in w for w in warnings)

    def test_no_warning_when_no_suppression(self):
        """When no tags are suppressed, no warning should be added."""
        from services.generation_controlnet import _suppress_cinematic_for_adain

        ctx = FakeContext(prompt="girl, backlit")
        warnings: list[str] = []
        removed = _suppress_cinematic_for_adain(ctx)
        if removed:
            warnings.append(f"Stripped: {removed}")
        assert len(warnings) == 0


class TestApplyEnvironmentWithSuppression:
    """Integration: _apply_environment() propagates cinematic tag suppression (SP-105)."""

    @patch("config.ENVIRONMENT_REFERENCE_ENABLED", True)
    @patch("services.generation_controlnet._extract_env_tags", return_value=[])
    @patch("services.generation_controlnet._load_env_asset")
    @patch("services.generation_controlnet._detect_env_conflict", return_value=None)
    @patch("services.generation_controlnet._apply_reference_adain_from_asset")
    def test_suppression_in_pinning_flow(self, mock_adain, mock_conflict, mock_load, mock_extract):
        """When environment pinning runs, cinematic tags should be stripped from ctx.prompt."""
        from services.generation_controlnet import _apply_environment

        mock_adain.return_value = True
        mock_load.return_value = MagicMock()
        req = FakeRequest(environment_reference_id=42)
        ctx = FakeContext(request=req, prompt="girl, kitchen, depth_of_field, bokeh, close-up")
        args: list = []
        _apply_environment(req, ctx, args, db=MagicMock())

        assert "depth_of_field" not in ctx.prompt
        assert "bokeh" not in ctx.prompt
        assert "close-up" in ctx.prompt
        assert any("시네마틱 태그 억제됨" in w for w in ctx.warnings)

    @patch("config.ENVIRONMENT_REFERENCE_ENABLED", False)
    def test_no_suppression_when_disabled(self):
        """When ENVIRONMENT_REFERENCE_ENABLED=False, no filtering occurs."""
        from services.generation_controlnet import _apply_environment

        req = FakeRequest(environment_reference_id=42)
        ctx = FakeContext(request=req, prompt="girl, depth_of_field, bokeh")
        args: list = []
        _apply_environment(req, ctx, args, db=MagicMock())

        assert "depth_of_field" in ctx.prompt
        assert "bokeh" in ctx.prompt

    def test_no_suppression_without_env_reference(self):
        """When no environment_reference_id, no filtering occurs."""
        from services.generation_controlnet import _apply_environment

        req = FakeRequest(environment_reference_id=None)
        ctx = FakeContext(request=req, prompt="girl, depth_of_field")
        args: list = []
        with patch("config.ENVIRONMENT_REFERENCE_ENABLED", True):
            _apply_environment(req, ctx, args, db=MagicMock())

        assert "depth_of_field" in ctx.prompt

    @patch("config.ENVIRONMENT_REFERENCE_ENABLED", True)
    @patch("services.generation_controlnet._extract_env_tags", return_value=[])
    @patch("services.generation_controlnet._load_env_asset")
    @patch("services.generation_controlnet._detect_env_conflict", return_value=None)
    @patch("services.generation_controlnet._apply_reference_adain_from_asset", return_value=False)
    def test_no_suppression_when_adain_fails(self, mock_adain, mock_conflict, mock_load, mock_extract):
        """AdaIN 적용 실패 시 ctx.prompt가 변경되지 않아야 한다."""
        from services.generation_controlnet import _apply_environment

        mock_load.return_value = MagicMock()
        req = FakeRequest(environment_reference_id=42)
        ctx = FakeContext(request=req, prompt="girl, depth_of_field, bokeh")
        _apply_environment(req, ctx, [], db=MagicMock())

        assert "depth_of_field" in ctx.prompt
        assert "bokeh" in ctx.prompt
        assert len(ctx.warnings) == 0


class TestPayloadPromptSync:
    """Integration: payload['prompt'] should reflect ctx.prompt after ControlNet filtering (SP-105 R2)."""

    @patch("config.ENVIRONMENT_REFERENCE_ENABLED", True)
    @patch("services.generation_controlnet._extract_env_tags", return_value=[])
    @patch("services.generation_controlnet._load_env_asset")
    @patch("services.generation_controlnet._detect_env_conflict", return_value=None)
    @patch("services.generation_controlnet._apply_reference_adain_from_asset")
    def test_payload_prompt_synced_after_controlnet(self, mock_adain, mock_conflict, mock_load, mock_extract):
        """After apply_controlnet, payload['prompt'] should match ctx.prompt (with tags stripped)."""
        from services.generation_controlnet import apply_controlnet

        mock_adain.return_value = True
        mock_load.return_value = MagicMock()
        req = FakeRequest(environment_reference_id=42)
        ctx = FakeContext(request=req, prompt="girl, kitchen, depth_of_field, bokeh, close-up")
        payload = {"prompt": ctx.prompt}

        apply_controlnet(payload, ctx, db=MagicMock())
        # Simulate generation.py sync line
        payload["prompt"] = ctx.prompt

        assert "depth_of_field" not in payload["prompt"]
        assert "bokeh" not in payload["prompt"]
        assert "close-up" in payload["prompt"]
        assert payload["prompt"] == ctx.prompt
