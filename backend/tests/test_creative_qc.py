"""Unit tests for _check_environment_consistency in creative_qc."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.creative_qc import _check_environment_consistency


def _scene(speaker: str, environment=None) -> dict:
    """Helper to build a minimal scene dict."""
    s: dict = {"speaker": speaker}
    if environment is not None:
        s["environment"] = environment
    return s


# -- 1. All scenes same environment (no issues) --


class TestSameEnvironment:
    def test_all_scenes_same_env_list(self):
        """A-B-A 대화, 모두 동일 환경(list) -> issues 빈 리스트."""
        scenes = [
            _scene("speaker_1", ["bedroom"]),
            _scene("speaker_2", ["bedroom"]),
            _scene("speaker_1", ["bedroom"]),
        ]
        assert _check_environment_consistency(scenes) == []

    def test_all_scenes_same_env_str(self):
        """동일 환경이 str 형태여도 일치 -> issues 빈 리스트."""
        scenes = [
            _scene("speaker_1", "office"),
            _scene("speaker_2", "office"),
        ]
        assert _check_environment_consistency(scenes) == []


# -- 2. Mismatch in A-B dialogue --


class TestMismatchDetection:
    def test_two_scenes_different_env(self):
        """A->B 대화에서 환경 다름 (bedroom vs office) -> issues 1건."""
        scenes = [
            _scene("speaker_1", ["bedroom"]),
            _scene("speaker_2", ["office"]),
        ]
        issues = _check_environment_consistency(scenes)
        assert len(issues) == 1
        assert "inconsistent environments" in issues[0]
        assert "bedroom" in issues[0]
        assert "office" in issues[0]

    def test_three_scenes_ab_mismatch(self):
        """A->B->A 대화에서 B만 다른 환경 -> issues 1건 (그룹 전체)."""
        scenes = [
            _scene("speaker_1", ["park"]),
            _scene("speaker_2", ["school"]),
            _scene("speaker_1", ["park"]),
        ]
        issues = _check_environment_consistency(scenes)
        assert len(issues) == 1
        assert "park" in issues[0]
        assert "school" in issues[0]


# -- 3. Narrator breaks dialogue group --


class TestNarratorBreaksGroup:
    def test_narrator_splits_groups(self):
        """A->Narrator->B 는 별도 그룹 -> 불일치 미검출."""
        scenes = [
            _scene("speaker_1", ["bedroom"]),
            _scene("narrator", ["bedroom"]),
            _scene("speaker_2", ["office"]),
        ]
        # A 단독(그룹 안 됨), Narrator 단독, B 단독 -> 그룹 없음 -> 이슈 없음
        assert _check_environment_consistency(scenes) == []

    def test_narrator_in_middle_of_dialogue(self):
        """A->B->Narrator->A->B: 두 그룹 (A-B) + (A-B), 각각 일관이면 OK."""
        scenes = [
            _scene("speaker_1", ["park"]),
            _scene("speaker_2", ["park"]),
            _scene("narrator", ["studio"]),
            _scene("speaker_1", ["cafe"]),
            _scene("speaker_2", ["cafe"]),
        ]
        assert _check_environment_consistency(scenes) == []

    def test_narrator_splits_but_second_group_inconsistent(self):
        """Narrator 이후 두 번째 그룹에서 불일치 -> issues 1건."""
        scenes = [
            _scene("speaker_1", ["park"]),
            _scene("speaker_2", ["park"]),
            _scene("narrator", ["studio"]),
            _scene("speaker_1", ["cafe"]),
            _scene("speaker_2", ["library"]),
        ]
        issues = _check_environment_consistency(scenes)
        assert len(issues) == 1
        assert "cafe" in issues[0]
        assert "library" in issues[0]


# -- 4. Single scene --


class TestSingleScene:
    def test_single_scene_no_issues(self):
        """단일 씬 -> issues 빈 리스트."""
        scenes = [_scene("speaker_1", ["bedroom"])]
        assert _check_environment_consistency(scenes) == []

    def test_empty_list(self):
        """빈 리스트 -> issues 빈 리스트."""
        assert _check_environment_consistency([]) == []


# -- 5. Scenes without environment --


class TestNoEnvironment:
    def test_none_environment_excluded(self):
        """environment가 None인 씬은 비교에서 제외."""
        scenes = [
            _scene("speaker_1", None),
            _scene("speaker_2", ["office"]),
        ]
        # 그룹 [0,1]이 형성되지만, scene 0의 env가 None -> env_sets에서 제외
        # unique_envs = {frozenset({"office"})} -> 1개 -> 불일치 아님
        assert _check_environment_consistency(scenes) == []

    def test_empty_list_environment_excluded(self):
        """environment가 빈 리스트인 씬은 비교에서 제외."""
        scenes = [
            _scene("speaker_1", []),
            _scene("speaker_2", ["park"]),
        ]
        assert _check_environment_consistency(scenes) == []

    def test_both_none_environment(self):
        """양쪽 모두 environment가 None -> 비교할 환경 없음 -> 이슈 없음."""
        scenes = [
            _scene("speaker_1", None),
            _scene("speaker_2", None),
        ]
        assert _check_environment_consistency(scenes) == []

    def test_missing_environment_key(self):
        """environment 키 자체가 없는 경우에도 안전하게 처리."""
        scenes = [
            {"speaker": "speaker_1"},
            {"speaker": "speaker_2", "environment": ["office"]},
        ]
        assert _check_environment_consistency(scenes) == []


# -- 6. Three or more different environments --


class TestMultipleDifferentEnvs:
    def test_three_different_envs_in_group(self):
        """3개 이상 다른 환경 -> issues에 모든 씬 환경 포함."""
        scenes = [
            _scene("speaker_1", ["bedroom"]),
            _scene("speaker_2", ["office"]),
            _scene("speaker_1", ["park"]),
        ]
        issues = _check_environment_consistency(scenes)
        assert len(issues) == 1
        assert "bedroom" in issues[0]
        assert "office" in issues[0]
        assert "park" in issues[0]

    def test_four_scenes_four_envs(self):
        """4씬 모두 다른 환경 -> issues 1건, 4개 환경 모두 언급."""
        scenes = [
            _scene("speaker_1", ["classroom"]),
            _scene("speaker_2", ["gym"]),
            _scene("speaker_1", ["library"]),
            _scene("speaker_2", ["cafeteria"]),
        ]
        issues = _check_environment_consistency(scenes)
        assert len(issues) == 1
        for env in ["classroom", "gym", "library", "cafeteria"]:
            assert env in issues[0]


# -- 7. String vs list environment --


class TestEnvStringVsList:
    def test_string_environment(self):
        """environment가 문자열(str) -> list로 변환하여 비교."""
        scenes = [
            _scene("speaker_1", "bedroom"),
            _scene("speaker_2", "office"),
        ]
        issues = _check_environment_consistency(scenes)
        assert len(issues) == 1
        assert "bedroom" in issues[0]
        assert "office" in issues[0]

    def test_mixed_string_and_list(self):
        """한 씬은 str, 다른 씬은 list -> 동일 환경이면 일치."""
        scenes = [
            _scene("speaker_1", "park"),
            _scene("speaker_2", ["park"]),
        ]
        assert _check_environment_consistency(scenes) == []

    def test_mixed_string_and_list_mismatch(self):
        """str vs list 혼합, 내용이 다르면 불일치."""
        scenes = [
            _scene("speaker_1", "park"),
            _scene("speaker_2", ["school"]),
        ]
        issues = _check_environment_consistency(scenes)
        assert len(issues) == 1

    def test_multi_element_list_env(self):
        """다중 요소 리스트 환경: 요소 집합이 다르면 불일치."""
        scenes = [
            _scene("speaker_1", ["bedroom", "night"]),
            _scene("speaker_2", ["bedroom", "day"]),
        ]
        issues = _check_environment_consistency(scenes)
        assert len(issues) == 1

    def test_multi_element_list_env_same(self):
        """다중 요소 리스트 환경: 집합이 동일하면 일치 (순서 무관)."""
        scenes = [
            _scene("speaker_1", ["bedroom", "night"]),
            _scene("speaker_2", ["night", "bedroom"]),
        ]
        assert _check_environment_consistency(scenes) == []
