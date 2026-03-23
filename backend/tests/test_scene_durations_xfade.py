"""Tests for calculate_scene_durations xfade compensation logic.

Duration formula (with TTS):
  transition_dur + h_pad + tts_duration + t_pad + tts_padding + xfade_tail
  ^^^^^^^^^^^^^^                                                ^^^^^^^^^^
  adelay offset (all scenes)                   acrossfade tail (non-last only)
"""

from services.video.utils import calculate_scene_durations


class _MockScene:
    def __init__(self, duration=3, head_padding=0.0, tail_padding=0.0):
        self.duration = duration
        self.head_padding = head_padding
        self.tail_padding = tail_padding


class TestXfadeCompensation:
    """transition_dur 보상: adelay offset(전체) + acrossfade tail(비마지막)."""

    def test_no_transition_dur_matches_old_behavior(self):
        """transition_dur=0이면 adelay/xfade 보상 모두 0."""
        scenes = [_MockScene(), _MockScene(), _MockScene()]
        result = calculate_scene_durations(scenes, [True, True, True], [4.0, 4.0, 4.0], 1.0, 0.8, 0.0)
        # 0 + 0 + 4 + 0 + 0.8 + 0 = 4.8
        assert result == [4.8, 4.8, 4.8]

    def test_transition_dur_compensates_all_scenes(self):
        """모든 씬에 adelay 보상(+0.5), 비마지막에 xfade tail 보상(+0.5)."""
        scenes = [_MockScene(), _MockScene(), _MockScene()]
        result = calculate_scene_durations(scenes, [True, True, True], [4.0, 4.0, 4.0], 1.0, 0.8, 0.5)
        # Non-last: 0.5 + 0 + 4.0 + 0 + 0.8 + 0.5 = 5.8
        # Last:     0.5 + 0 + 4.0 + 0 + 0.8 + 0.0 = 5.3
        assert result[0] == 5.8
        assert result[1] == 5.8
        assert result[2] == 5.3

    def test_single_scene_adelay_compensation(self):
        """단일 씬에도 adelay offset 보상 적용."""
        scenes = [_MockScene()]
        result = calculate_scene_durations(scenes, [True], [4.0], 1.0, 0.8, 0.5)
        # 0.5 + 0 + 4.0 + 0 + 0.8 + 0 = 5.3
        assert result == [5.3]

    def test_no_tts_scene_ignores_compensation(self):
        """TTS 없는 씬은 보상 무관."""
        scenes = [_MockScene(duration=3), _MockScene(duration=3)]
        result = calculate_scene_durations(scenes, [False, False], [0.0, 0.0], 1.0, 0.8, 0.5)
        assert result == [3.0, 3.0]

    def test_base_duration_wins_if_larger(self):
        """base_duration이 TTS+보상보다 크면 base_duration 유지."""
        scenes = [_MockScene(duration=10), _MockScene(duration=10)]
        result = calculate_scene_durations(scenes, [True, True], [2.0, 2.0], 1.0, 0.8, 0.5)
        # Scene 0: 0.5+0+2+0+0.8+0.5 = 3.8 < 10
        assert result == [10.0, 10.0]

    def test_head_tail_padding_respected(self):
        """agent-designed head/tail padding이 보상과 함께 동작."""
        scenes = [_MockScene(head_padding=0.3, tail_padding=0.5), _MockScene()]
        result = calculate_scene_durations(scenes, [True, True], [3.0, 3.0], 1.0, 0.8, 0.5)
        # Scene 0: 0.5 + 0.3 + 3.0 + 0.5 + 0.8 + 0.5 = 5.6
        # Scene 1: 0.5 + 0   + 3.0 + 0   + 0.8 + 0   = 4.3
        assert abs(result[0] - 5.6) < 0.001
        assert abs(result[1] - 4.3) < 0.001

    def test_speed_multiplier_applied(self):
        """speed_multiplier가 base_duration에만 적용, TTS에는 미적용."""
        scenes = [_MockScene(duration=6), _MockScene(duration=6)]
        result = calculate_scene_durations(scenes, [True, True], [4.0, 4.0], 2.0, 0.4, 0.25)
        # base = 6/2 = 3.0
        # Scene 0: max(3.0, 0.25+0+4.0+0+0.4+0.25) = max(3.0, 4.9) = 4.9
        # Scene 1: max(3.0, 0.25+0+4.0+0+0.4+0.0)  = max(3.0, 4.65) = 4.65
        assert abs(result[0] - 4.9) < 0.001
        assert abs(result[1] - 4.65) < 0.001


class TestBuildAudioFiltersHeadPadding:
    """build_audio_filters()에서 head_padding이 adelay에 반영되는지 검증."""

    def test_head_padding_adds_to_adelay(self):
        """h_pad=0.3, transition_dur=0.5 -> adelay=(0.5+0.3)*1000=800ms."""
        from unittest.mock import MagicMock

        from services.video.filters import build_audio_filters

        builder = MagicMock()
        builder.transition_dur = 0.5
        builder.request.scenes = [MagicMock(head_padding=0.3, tail_padding=0.5)]
        builder.scene_durations = [5.0]
        builder.num_scenes = 1
        builder.filters = []

        build_audio_filters(builder)
        assert len(builder.filters) == 1
        assert "adelay=800|800" in builder.filters[0]

    def test_zero_padding_uses_transition_only(self):
        """h_pad=0, transition_dur=0.5 -> adelay=500ms."""
        from unittest.mock import MagicMock

        from services.video.filters import build_audio_filters

        builder = MagicMock()
        builder.transition_dur = 0.5
        builder.request.scenes = [MagicMock(head_padding=0.0, tail_padding=0.0)]
        builder.scene_durations = [5.0]
        builder.num_scenes = 1
        builder.filters = []

        build_audio_filters(builder)
        assert "adelay=500|500" in builder.filters[0]

    def test_none_padding_defaults_to_zero(self):
        """h_pad=None -> 0.0으로 처리."""
        from unittest.mock import MagicMock

        from services.video.filters import build_audio_filters

        builder = MagicMock()
        builder.transition_dur = 0.5
        builder.request.scenes = [MagicMock(head_padding=None, tail_padding=None)]
        builder.scene_durations = [5.0]
        builder.num_scenes = 1
        builder.filters = []

        build_audio_filters(builder)
        assert "adelay=500|500" in builder.filters[0]


class TestLastSceneTTSClipPrevention:
    """마지막 씬 TTS 잘림 방지 regression 테스트."""

    def test_last_scene_has_enough_room_for_tts(self):
        """마지막 씬 duration이 adelay + TTS + padding을 수용해야 함.

        adelay = transition_dur + h_pad 이므로,
        clip_dur >= transition_dur + h_pad + tts + t_pad + tts_padding
        """
        transition_dur = 0.5
        tts_padding = 0.8
        tts_dur = 4.0
        scenes = [_MockScene(), _MockScene()]
        result = calculate_scene_durations(
            scenes,
            [True, True],
            [tts_dur, tts_dur],
            1.0,
            tts_padding,
            transition_dur,
        )
        last_dur = result[-1]
        adelay = transition_dur  # h_pad=0
        available = last_dur - adelay
        # TTS + padding must fit within available window
        needed = tts_dur + tts_padding
        assert available >= needed, f"Last scene clip room ({available:.2f}s) < TTS+padding ({needed:.2f}s)"

    def test_last_scene_with_long_tts(self):
        """긴 TTS(6초)에서도 마지막 씬이 잘리지 않아야 함."""
        transition_dur = 0.5
        tts_padding = 0.8
        scenes = [_MockScene(), _MockScene(), _MockScene()]
        tts = [3.0, 5.0, 6.0]
        result = calculate_scene_durations(
            scenes,
            [True, True, True],
            tts,
            1.0,
            tts_padding,
            transition_dur,
        )
        for i, (dur, tts_d) in enumerate(zip(result, tts)):
            adelay = transition_dur
            available = dur - adelay
            needed = tts_d + tts_padding
            assert available >= needed, f"Scene {i}: clip room ({available:.2f}s) < TTS+padding ({needed:.2f}s)"

    def test_last_scene_with_tail_padding(self):
        """tail_padding이 있는 마지막 씬도 충분한 여유."""
        transition_dur = 0.5
        tts_padding = 0.8
        scenes = [_MockScene(tail_padding=0.5), _MockScene(tail_padding=1.0)]
        tts = [3.0, 4.0]
        result = calculate_scene_durations(
            scenes,
            [True, True],
            tts,
            1.0,
            tts_padding,
            transition_dur,
        )
        last_dur = result[-1]
        adelay = transition_dur
        available = last_dur - adelay
        needed = tts[1] + 1.0 + tts_padding  # tts + tail_pad + tts_padding
        assert available >= needed

    def test_effective_padding_not_consumed_by_adelay(self):
        """tts_padding(0.8s)이 adelay에 의해 잠식되지 않는지 직접 검증.

        이전 버그: 마지막 씬 유효 패딩 = 0.8 - 0.5 = 0.3s (부족)
        수정 후:   마지막 씬 유효 패딩 = 0.8s 전체 보존
        """
        transition_dur = 0.5
        tts_padding = 0.8
        tts_dur = 4.0
        scenes = [_MockScene()]
        result = calculate_scene_durations(
            scenes,
            [True],
            [tts_dur],
            1.0,
            tts_padding,
            transition_dur,
        )
        clip_dur = result[0]
        adelay = transition_dur
        # effective padding = clip_dur - adelay - tts_dur
        effective_padding = clip_dur - adelay - tts_dur
        assert abs(effective_padding - tts_padding) < 0.001, (
            f"Effective padding ({effective_padding:.2f}s) != tts_padding ({tts_padding:.2f}s)"
        )
