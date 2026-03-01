"""video/encoding _classify_filter 단위 테스트."""

from __future__ import annotations

from services.video.encoding import _classify_filter


class TestClassifyFilter:
    def test_zoompan(self):
        assert _classify_filter("[v0_scaled]zoompan=z='1':x='0':y='0':d=75:s=1080x1920:fps=25[v0_kb]") == "KenBurns"

    def test_xfade(self):
        assert _classify_filter("[v0_raw][v1_raw]xfade=transition=fade:duration=0.5[vx0]") == "Transition"

    def test_acrossfade(self):
        assert _classify_filter("[a0][a1]acrossfade=d=0.5[ax0]") == "AudioXfade"

    def test_overlay(self):
        assert _classify_filter("[v0_kb_rgba][sub0]overlay=0:0:format=auto[v0_base]") == "Overlay"

    def test_sidechaincompress(self):
        assert _classify_filter("[music_sc][voice_sc]sidechaincompress=threshold=0.02[ducked]") == "Ducking"

    def test_amix(self):
        assert _classify_filter("[ducked][voice]amix=inputs=2[final_audio]") == "AudioMix"

    def test_scale(self):
        assert _classify_filter("[0:v]scale=1080:1920[v0_scaled]") == "Scale/Crop"

    def test_crop(self):
        assert _classify_filter("[0:v]crop=1080:1920:(iw-ow)/2:0[v0_scaled]") == "Scale/Crop"

    def test_aresample(self):
        assert _classify_filter("[1:a]aresample=44100,adelay=500|500[a0_raw]") == "AudioProc"

    def test_trim(self):
        assert _classify_filter("[v0_graded]trim=duration=3.5,setpts=PTS-STARTPTS[v0_raw]") == "Trim"

    def test_atrim(self):
        assert _classify_filter("[a0]atrim=duration=3.5[a0_trimmed]") == "Trim"

    def test_fade(self):
        assert _classify_filter("[sub0]fade=t=in:st=0:d=0.3:alpha=1[sub0_faded]") == "Fade"

    def test_volume(self):
        assert _classify_filter("[music]volume=0.3[music_v]") == "Volume"

    def test_eq_colorgrade(self):
        assert _classify_filter("[v0_base]eq=saturation=1.15:contrast=1.05,vignette=PI/5[v0_graded]") == "ColorGrade"

    def test_vignette(self):
        assert _classify_filter("[v0]vignette=PI/5[v0_vig]") == "ColorGrade"

    def test_asplit(self):
        assert _classify_filter("[music]asplit=2[m1][m2]") == "AudioSplit"

    def test_null_passthrough(self):
        assert _classify_filter("[v0_kb]null[v0_base]") == "Passthrough"

    def test_unknown_filter(self):
        assert _classify_filter("[v0]deband=1thr=0.02[v0_db]") == "Other"
