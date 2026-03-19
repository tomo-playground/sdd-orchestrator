"""Dialogue 구조 Speaker B 누락 + 비율 불균형 수정 테스트.

Review, Revise, ensure_dialogue_speakers 3개 모듈의 Dialogue speaker 검증을 테스트한다.
"""

from __future__ import annotations

from services.agent.nodes.review import _validate_scenes
from services.agent.nodes.revise import (
    _DIALOGUE_MISSING_SPEAKER_RE,
    _try_rule_fix,
)
from services.script.scene_postprocess import ensure_dialogue_speakers

# ── Helpers ──────────────────────────────────────────────────────


def _make_scene(speaker: str = "A", script: str = "테스트 대사입니다", **kwargs) -> dict:
    return {
        "speaker": speaker,
        "script": script,
        "duration": 3,
        "image_prompt": "1girl, solo",
        **kwargs,
    }


# ── TestReviewDialogueSpeakerValidation ──────────────────────────


class TestReviewDialogueSpeakerValidation:
    """Review 노드의 Dialogue speaker 검증 테스트."""

    def test_b_missing_produces_error(self):
        """Dialogue에서 B가 없으면 errors에 포함되어야 한다."""
        scenes = [_make_scene("A"), _make_scene("A"), _make_scene("Narrator")]
        result = _validate_scenes(scenes, duration=10, language="korean", structure="dialogue")
        assert not result["passed"]
        assert any("speaker 'B'" in e for e in result["errors"])

    def test_a_missing_produces_error(self):
        """Dialogue에서 A가 없으면 errors에 포함되어야 한다."""
        scenes = [_make_scene("B"), _make_scene("B"), _make_scene("Narrator")]
        result = _validate_scenes(scenes, duration=10, language="korean", structure="dialogue")
        assert not result["passed"]
        assert any("speaker 'A'" in e for e in result["errors"])

    def test_both_speakers_passes(self):
        """A와 B 모두 있으면 speaker 관련 에러가 없어야 한다."""
        scenes = [
            _make_scene("A"),
            _make_scene("B"),
            _make_scene("Narrator"),
            _make_scene("A"),
            _make_scene("B"),
        ]
        result = _validate_scenes(scenes, duration=10, language="korean", structure="dialogue")
        speaker_errors = [e for e in result["errors"] if "speaker" in e and "Dialogue" in e]
        assert len(speaker_errors) == 0

    def test_narrated_dialogue_also_validates(self):
        """Narrated Dialogue 구조에서도 동일 검증."""
        scenes = [_make_scene("A"), _make_scene("A")]
        result = _validate_scenes(scenes, duration=10, language="korean", structure="narrated_dialogue")
        assert not result["passed"]
        assert any("speaker 'B'" in e for e in result["errors"])

    def test_monologue_ignores_b_absence(self):
        """Monologue에서는 B 부재를 검증하지 않아야 한다."""
        scenes = [_make_scene("A"), _make_scene("A")]
        result = _validate_scenes(scenes, duration=10, language="korean", structure="monologue")
        dialogue_errors = [e for e in result["errors"] if "Dialogue" in e]
        assert len(dialogue_errors) == 0


# ── TestReviseDialogueMissingSpeaker ─────────────────────────────


class TestReviseDialogueMissingSpeaker:
    """Revise 노드의 Dialogue speaker 교대 배정 수정 테스트."""

    def test_regex_matches_error_message(self):
        """정규식이 Review 에러 메시지를 올바르게 매칭하는지 확인."""
        msg = "Dialogue 구조에서 speaker 'B'가 등장하지 않음 — 반드시 A와 B 모두 포함해야 함"
        assert _DIALOGUE_MISSING_SPEAKER_RE.search(msg)

    def test_alternating_assignment(self):
        """non-Narrator 씬이 교대 배정 (A, B, A, B...) 되어야 한다."""
        scenes = [
            _make_scene("A"),
            _make_scene("A"),
            _make_scene("Narrator"),
            _make_scene("A"),
            _make_scene("A"),
        ]
        errors = ["Dialogue 구조에서 speaker 'B'가 등장하지 않음 — 반드시 A와 B 모두 포함해야 함"]
        resolved = _try_rule_fix(scenes, errors)
        assert resolved

        non_narrator = [s for s in scenes if s["speaker"] != "Narrator"]
        speakers = [s["speaker"] for s in non_narrator]
        assert speakers == ["A", "B", "A", "B"]

    def test_narrator_preserved(self):
        """Narrator 씬은 교대 배정에서 변경되지 않아야 한다."""
        scenes = [
            _make_scene("A"),
            _make_scene("Narrator"),
            _make_scene("A"),
            _make_scene("A"),
        ]
        errors = ["Dialogue 구조에서 speaker 'B'가 등장하지 않음 — 반드시 A와 B 모두 포함해야 함"]
        _try_rule_fix(scenes, errors)
        assert scenes[1]["speaker"] == "Narrator"

    def test_no_non_narrator_unresolved(self):
        """non-Narrator 씬이 없으면 unresolved (False 반환)."""
        scenes = [_make_scene("Narrator"), _make_scene("Narrator")]
        errors = ["Dialogue 구조에서 speaker 'B'가 등장하지 않음 — 반드시 A와 B 모두 포함해야 함"]
        resolved = _try_rule_fix(scenes, errors)
        assert not resolved


# ── TestEnsureDialogueSpeakers ───────────────────────────────────


class TestEnsureDialogueSpeakers:
    """Quick 모드 ensure_dialogue_speakers 테스트."""

    def test_both_present_noop(self):
        """A와 B 모두 있으면 변경하지 않아야 한다."""
        scenes = [_make_scene("A"), _make_scene("B"), _make_scene("A")]
        original_speakers = [s["speaker"] for s in scenes]
        ensure_dialogue_speakers(scenes)
        assert [s["speaker"] for s in scenes] == original_speakers

    def test_b_missing_auto_fix(self):
        """B가 없으면 교대 배정으로 자동 수정되어야 한다."""
        scenes = [
            _make_scene("A"),
            _make_scene("A"),
            _make_scene("A"),
            _make_scene("A"),
        ]
        ensure_dialogue_speakers(scenes)
        speakers = [s["speaker"] for s in scenes]
        assert "B" in speakers
        assert speakers == ["A", "B", "A", "B"]

    def test_narrator_preserved(self):
        """Narrator 씬은 보존되어야 한다."""
        scenes = [
            _make_scene("A"),
            _make_scene("Narrator"),
            _make_scene("A"),
            _make_scene("A"),
        ]
        ensure_dialogue_speakers(scenes)
        assert scenes[1]["speaker"] == "Narrator"
        non_narrator = [s for s in scenes if s["speaker"] != "Narrator"]
        assert "B" in {s["speaker"] for s in non_narrator}

    def test_all_narrator_no_change(self):
        """모든 씬이 Narrator면 변경 불가."""
        scenes = [_make_scene("Narrator"), _make_scene("Narrator")]
        ensure_dialogue_speakers(scenes)
        assert all(s["speaker"] == "Narrator" for s in scenes)

    def test_imbalanced_auto_rebalance(self):
        """A=10, B=1 → 비율 불균형 시 교대 재배정."""
        scenes = [_make_scene("A")] * 10 + [_make_scene("B")]
        # 원본은 deepcopy 아니므로 새 dict 생성
        scenes = [_make_scene(s["speaker"]) for s in scenes]
        ensure_dialogue_speakers(scenes)
        non_narrator = [s for s in scenes if s["speaker"] in ("A", "B")]
        a_count = sum(1 for s in non_narrator if s["speaker"] == "A")
        b_count = sum(1 for s in non_narrator if s["speaker"] == "B")
        assert a_count >= 2
        assert b_count >= 2

    def test_balanced_noop(self):
        """A=5, B=5 → 변경 없음."""
        scenes = []
        for i in range(10):
            scenes.append(_make_scene("A" if i % 2 == 0 else "B"))
        original = [s["speaker"] for s in scenes]
        ensure_dialogue_speakers(scenes)
        assert [s["speaker"] for s in scenes] == original

    def test_borderline_20pct_noop(self):
        """A=4, B=1 → 20% = 통과 (변경 없음)."""
        scenes = [_make_scene("A")] * 4 + [_make_scene("B")]
        scenes = [_make_scene(s["speaker"]) for s in scenes]
        original = [s["speaker"] for s in scenes]
        ensure_dialogue_speakers(scenes)
        assert [s["speaker"] for s in scenes] == original


# ── TestReviewSpeakerBalance ─────────────────────────────────────


class TestReviewSpeakerBalance:
    """Review 노드의 speaker 비율 검증 + Narrator 존재 검증 테스트."""

    def test_imbalanced_a11_b1_produces_error(self):
        """A=11, B=1 → error (B가 8%로 20% 미만)."""
        scenes = [_make_scene("A")] * 11 + [_make_scene("B")]
        scenes = [_make_scene(s["speaker"]) for s in scenes]
        result = _validate_scenes(scenes, duration=30, language="korean", structure="dialogue")
        assert not result["passed"]
        assert any("speaker 비율 불균형" in e for e in result["errors"])

    def test_balanced_a5_b5_passes(self):
        """A=5, B=5 → no speaker balance error."""
        scenes = []
        for i in range(10):
            scenes.append(_make_scene("A" if i % 2 == 0 else "B"))
        result = _validate_scenes(scenes, duration=30, language="korean", structure="dialogue")
        balance_errors = [e for e in result["errors"] if "비율 불균형" in e]
        assert len(balance_errors) == 0

    def test_borderline_a4_b1_passes(self):
        """A=4, B=1 (20%) → pass."""
        scenes = [_make_scene("A")] * 4 + [_make_scene("B")]
        scenes = [_make_scene(s["speaker"]) for s in scenes]
        result = _validate_scenes(scenes, duration=15, language="korean", structure="dialogue")
        balance_errors = [e for e in result["errors"] if "비율 불균형" in e]
        assert len(balance_errors) == 0

    def test_narrated_dialogue_no_narrator_error(self):
        """Narrated Dialogue에서 Narrator=0 → error."""
        scenes = []
        for i in range(8):
            scenes.append(_make_scene("A" if i % 2 == 0 else "B"))
        result = _validate_scenes(scenes, duration=20, language="korean", structure="narrated_dialogue")
        assert any("Narrator 씬 없음" in e for e in result["errors"])

    def test_narrated_dialogue_with_narrator_no_warning(self):
        """Narrated Dialogue에서 Narrator 있음 → no warning."""
        scenes = [_make_scene("A"), _make_scene("B"), _make_scene("Narrator"), _make_scene("A"), _make_scene("B")]
        result = _validate_scenes(scenes, duration=15, language="korean", structure="narrated_dialogue")
        narrator_warnings = [w for w in result["warnings"] if "Narrator 씬 없음" in w]
        assert len(narrator_warnings) == 0


# ── TestReviseSpeakerImbalance ───────────────────────────────────


class TestReviseSpeakerImbalance:
    """Revise 노드의 speaker 비율 불균형 처리 테스트."""

    def test_imbalance_regex_matches(self):
        """새 regex가 비율 불균형 에러 메시지를 매칭."""
        from services.agent.nodes.revise import _SPEAKER_IMBALANCE_RE

        msg = "Dialogue 구조에서 speaker 비율 불균형 — B가 8%로 최소 20% 미만 (A=11, B=1, 총 12씬)"
        assert _SPEAKER_IMBALANCE_RE.search(msg)

    def test_imbalance_not_rule_fixed(self):
        """비율 불균형 에러는 _try_rule_fix()로 해결 불가 → False."""
        scenes = [_make_scene("A")] * 11 + [_make_scene("B")]
        scenes = [_make_scene(s["speaker"]) for s in scenes]
        errors = ["Dialogue 구조에서 speaker 비율 불균형 — B가 8%로 최소 20% 미만 (A=11, B=1, 총 12씬)"]
        resolved = _try_rule_fix(scenes, errors)
        assert not resolved

    def test_imbalance_with_other_fixable_errors(self):
        """비율 불균형 + 다른 수정 가능 에러 → False (비율 불균형이 unresolved)."""
        scenes = [_make_scene("A", duration=0)] * 11 + [_make_scene("B")]
        scenes = [_make_scene(s["speaker"], duration=s["duration"]) for s in scenes]
        errors = [
            "씬 1: duration이 0 이하 (0)",
            "Dialogue 구조에서 speaker 비율 불균형 — B가 8%로 최소 20% 미만 (A=11, B=1, 총 12씬)",
        ]
        resolved = _try_rule_fix(scenes, errors)
        assert not resolved
