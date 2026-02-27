"""Tests for calculate_scene_durations xfade compensation logic."""

from services.video.utils import calculate_scene_durations


class _MockScene:
    def __init__(self, duration=3, head_padding=0.0, tail_padding=0.0):
        self.duration = duration
        self.head_padding = head_padding
        self.tail_padding = tail_padding


class TestXfadeCompensation:
    """transition_dur 보상: 비마지막 씬은 +transition_dur, 마지막 씬은 보상 없음."""

    def test_no_transition_dur_matches_old_behavior(self):
        """transition_dur=0 (기본값)이면 기존 동작과 동일."""
        scenes = [_MockScene(), _MockScene(), _MockScene()]
        result = calculate_scene_durations(scenes, [True, True, True], [4.0, 4.0, 4.0], 1.0, 0.8, 0.0)
        # h_pad(0) + tts(4) + t_pad(0) + padding(0.8) = 4.8 for all
        assert result == [4.8, 4.8, 4.8]

    def test_transition_dur_compensates_non_last_scenes(self):
        """비마지막 씬에 transition_dur만큼 추가."""
        scenes = [_MockScene(), _MockScene(), _MockScene()]
        result = calculate_scene_durations(scenes, [True, True, True], [4.0, 4.0, 4.0], 1.0, 0.8, 0.5)
        # Non-last: 0 + 4.0 + 0 + 0.8 + 0.5 = 5.3
        # Last:     0 + 4.0 + 0 + 0.8 + 0.0 = 4.8
        assert result[0] == 5.3
        assert result[1] == 5.3
        assert result[2] == 4.8

    def test_single_scene_no_compensation(self):
        """단일 씬이면 보상 없음 (마지막 씬이자 유일한 씬)."""
        scenes = [_MockScene()]
        result = calculate_scene_durations(scenes, [True], [4.0], 1.0, 0.8, 0.5)
        assert result == [4.8]

    def test_no_tts_scene_ignores_compensation(self):
        """TTS 없는 씬은 xfade 보상 무관."""
        scenes = [_MockScene(duration=3), _MockScene(duration=3)]
        result = calculate_scene_durations(scenes, [False, False], [0.0, 0.0], 1.0, 0.8, 0.5)
        assert result == [3.0, 3.0]

    def test_base_duration_wins_if_larger(self):
        """base_duration이 TTS+보상보다 크면 base_duration 유지."""
        scenes = [_MockScene(duration=10), _MockScene(duration=10)]
        result = calculate_scene_durations(scenes, [True, True], [2.0, 2.0], 1.0, 0.8, 0.5)
        # TTS total for scene 0: 0+2+0+0.8+0.5 = 3.3 < 10
        assert result == [10.0, 10.0]

    def test_head_tail_padding_respected(self):
        """agent-designed head/tail padding이 보상과 함께 동작."""
        scenes = [_MockScene(head_padding=0.3, tail_padding=0.5), _MockScene()]
        result = calculate_scene_durations(scenes, [True, True], [3.0, 3.0], 1.0, 0.8, 0.5)
        # Scene 0: 0.3 + 3.0 + 0.5 + 0.8 + 0.5 = 5.1
        # Scene 1 (last): 0 + 3.0 + 0 + 0.8 + 0.0 = 3.8
        assert abs(result[0] - 5.1) < 0.001
        assert abs(result[1] - 3.8) < 0.001

    def test_speed_multiplier_applied(self):
        """speed_multiplier가 base_duration에만 적용, TTS에는 미적용."""
        scenes = [_MockScene(duration=6), _MockScene(duration=6)]
        result = calculate_scene_durations(scenes, [True, True], [4.0, 4.0], 2.0, 0.4, 0.25)
        # base = 6/2 = 3.0
        # Scene 0: max(3.0, 0+4.0+0+0.4+0.25) = max(3.0, 4.65) = 4.65
        # Scene 1: max(3.0, 0+4.0+0+0.4+0.0)  = max(3.0, 4.4) = 4.4
        assert abs(result[0] - 4.65) < 0.001
        assert abs(result[1] - 4.4) < 0.001
