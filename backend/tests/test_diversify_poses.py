"""Pose/ControlNet 다양성 테스트.

diversify_poses() + _auto_populate_scene_flags() controlnet_pose 매핑 검증.
"""

import pytest

from services.agent.nodes._diversify_utils import diversify_poses


def _make_scenes(poses: list[str], emotions: list[str | None] | None = None) -> list[dict]:
    scenes = []
    for i, pose in enumerate(poses):
        ctx = {"pose": pose}
        if emotions and i < len(emotions) and emotions[i]:
            ctx["emotion"] = emotions[i]
        scenes.append({"context_tags": ctx, "speaker": "speaker_1"})
    return scenes


class TestDiversifyPoses:
    """diversify_poses() — pose 단조로움 교정."""

    def test_dominant_standing_gets_corrected(self):
        """50% 초과 standing → emotion 기반 교정."""
        scenes = _make_scenes(
            poses=["standing"] * 5,
            emotions=["sad", "excited", "nervous", "proud", "calm"],
        )
        diversify_poses(scenes)
        poses = [s["context_tags"]["pose"] for s in scenes]
        assert poses.count("standing") < 3, f"standing이 {poses.count('standing')}/5로 과다"

    def test_emotion_to_pose_mapping(self):
        """emotion → pose 매핑이 정확한지."""
        scenes = _make_scenes(
            poses=["standing"] * 5,
            emotions=["sad", "excited", "nervous", "proud", "embarrassed"],
        )
        diversify_poses(scenes)
        ctx = [s["context_tags"] for s in scenes]
        assert ctx[0]["pose"] == "sitting"  # sad → sitting
        assert ctx[1]["pose"] == "arms_up"  # excited → arms_up
        assert ctx[2]["pose"] == "leaning_forward"  # nervous → leaning_forward
        assert ctx[3]["pose"] == "hands_on_hips"  # proud → hands_on_hips
        assert ctx[4]["pose"] == "hand_on_face"  # embarrassed → hand_on_face

    def test_diverse_poses_no_change(self):
        """이미 다양하면 교정 안 함."""
        scenes = _make_scenes(
            poses=["standing", "sitting", "arms_crossed", "leaning_forward"],
            emotions=["happy", "sad", "angry", "nervous"],
        )
        original = [s["context_tags"]["pose"] for s in scenes]
        diversify_poses(scenes)
        result = [s["context_tags"]["pose"] for s in scenes]
        assert original == result

    def test_few_scenes_skipped(self):
        """3씬 미만이면 건너뜀."""
        scenes = _make_scenes(
            poses=["standing", "standing"],
            emotions=["sad", "happy"],
        )
        diversify_poses(scenes)
        assert scenes[0]["context_tags"]["pose"] == "standing"

    def test_no_emotion_no_change(self):
        """emotion 없으면 교정하지 않음."""
        scenes = _make_scenes(poses=["standing"] * 4)
        diversify_poses(scenes)
        poses = [s["context_tags"]["pose"] for s in scenes]
        assert poses.count("standing") == 4

    def test_consecutive_same_pose_avoided(self):
        """연속 동일 pose 방지."""
        scenes = _make_scenes(
            poses=["standing"] * 6,
            emotions=["calm", "calm", "calm", "calm", "calm", "calm"],
        )
        diversify_poses(scenes)
        poses = [s["context_tags"]["pose"] for s in scenes]
        # 연속 3개 이상 동일하지 않아야 함
        for i in range(2, len(poses)):
            if poses[i] == poses[i - 1] == poses[i - 2]:
                pytest.fail(f"연속 3개 동일: {poses[i]} at index {i - 2}~{i}")

    def test_narrator_excluded(self):
        """Narrator 씬은 교정 대상에서 제외."""
        scenes = [
            {"context_tags": {"pose": "standing", "emotion": "sad"}, "speaker": "narrator"},
            {"context_tags": {"pose": "standing", "emotion": "sad"}, "speaker": "speaker_1"},
            {"context_tags": {"pose": "standing", "emotion": "excited"}, "speaker": "speaker_1"},
            {"context_tags": {"pose": "standing", "emotion": "nervous"}, "speaker": "speaker_1"},
        ]
        diversify_poses(scenes)
        # Narrator는 standing 유지
        assert scenes[0]["context_tags"]["pose"] == "standing"


class TestControlnetPoseMapping:
    """_auto_populate_scene_flags() — context_tags.pose → controlnet_pose 매핑."""

    def test_standing_default_overridden_by_context_pose(self):
        """controlnet_pose=standing(기본값)이면 context_tags.pose에서 재할당."""
        from config import DEFAULT_POSE_TAG
        from services.agent.nodes.finalize import _auto_populate_scene_flags

        scenes = [
            {
                "context_tags": {"pose": "hands_on_hips", "gaze": "looking_at_viewer"},
                "speaker": "speaker_1",
                "controlnet_pose": DEFAULT_POSE_TAG,
            },
        ]
        _auto_populate_scene_flags(scenes, character_id=1, character_b_id=None)
        # standing_hands_on_hips 에셋이 있으면 매칭, 없으면 standing 유지
        assert scenes[0]["controlnet_pose"] is not None

    def test_empty_controlnet_pose_gets_assigned(self):
        """controlnet_pose 비어있으면 context_tags.pose에서 할당."""
        from services.agent.nodes.finalize import _auto_populate_scene_flags

        scenes = [
            {
                "context_tags": {"pose": "sitting", "gaze": "looking_down"},
                "speaker": "speaker_1",
            },
        ]
        _auto_populate_scene_flags(scenes, character_id=1, character_b_id=None)
        assert scenes[0].get("controlnet_pose") is not None

    def test_list_pose_handled(self):
        """context_tags.pose가 리스트여도 에러 없이 처리."""
        from services.agent.nodes.finalize import _auto_populate_scene_flags

        scenes = [
            {
                "context_tags": {"pose": ["standing", "arms_crossed"], "gaze": "looking_at_viewer"},
                "speaker": "speaker_1",
            },
        ]
        _auto_populate_scene_flags(scenes, character_id=1, character_b_id=None)
        assert scenes[0].get("controlnet_pose") is not None

    def test_empty_list_pose_fallback(self):
        """context_tags.pose가 빈 리스트면 DEFAULT_POSE_TAG fallback."""
        from config import DEFAULT_POSE_TAG
        from services.agent.nodes.finalize import _auto_populate_scene_flags

        scenes = [
            {
                "context_tags": {"pose": [], "gaze": "looking_at_viewer"},
                "speaker": "speaker_1",
            },
        ]
        _auto_populate_scene_flags(scenes, character_id=1, character_b_id=None)
        assert scenes[0].get("controlnet_pose") == DEFAULT_POSE_TAG

    def test_narrator_no_controlnet(self):
        """Narrator 씬은 use_controlnet=False."""
        from services.agent.nodes.finalize import _auto_populate_scene_flags

        scenes = [
            {
                "context_tags": {"pose": "standing", "gaze": "looking_at_viewer"},
                "speaker": "narrator",
            },
        ]
        _auto_populate_scene_flags(scenes, character_id=1, character_b_id=None)
        assert scenes[0].get("use_controlnet") is False
