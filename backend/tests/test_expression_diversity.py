"""Expression 단조로움 보정 테스트."""

from __future__ import annotations

from services.agent.nodes._context_tag_utils import (
    _infer_emotion_from_script,
    diversify_expressions,
)


class TestInferEmotionFromScript:
    """스크립트 키워드 → emotion 추론."""

    def test_anxious_keywords(self):
        assert _infer_emotion_from_script("요즘 공부가 좀 어려워서요...") == "anxious"

    def test_sad_keywords(self):
        assert _infer_emotion_from_script("너무 슬퍼요") == "sad"

    def test_happy_keywords(self):
        assert _infer_emotion_from_script("정말 감사합니다!") == "happy"

    def test_calm_keywords(self):
        assert _infer_emotion_from_script("말씀드리니 좀 낫네요") == "calm"

    def test_determined_keywords(self):
        assert _infer_emotion_from_script("우리 같이 해보자!") == "determined"

    def test_no_match_returns_none(self):
        assert _infer_emotion_from_script("안녕하세요") is None

    def test_empty_script(self):
        assert _infer_emotion_from_script("") is None


class TestDiversifyExpressions:
    """Expression 단조로움 감지 및 보정."""

    def test_all_smile_gets_diversified(self):
        """6씬 모두 smile → 스크립트 기반으로 일부 교체."""
        scenes = [
            {"speaker": "A", "script": "편하게 얘기해 봐.", "context_tags": {"expression": "smile"}},
            {"speaker": "B", "script": "요즘 공부가 좀 어려워서요...", "context_tags": {"expression": "smile"}},
            {"speaker": "A", "script": "혼자 힘들어하지 마.", "context_tags": {"expression": "smile"}},
            {"speaker": "B", "script": "말씀드리니 좀 낫네요.", "context_tags": {"expression": "smile"}},
            {"speaker": "A", "script": "같이 해보자!", "context_tags": {"expression": "smile"}},
            {"speaker": "B", "script": "감사합니다!", "context_tags": {"expression": "smile"}},
        ]
        diversify_expressions(scenes)
        expressions = [s["context_tags"]["expression"] for s in scenes]
        # 더 이상 모두 smile이 아님
        assert len(set(expressions)) > 1
        # Scene 1: "어려워" → anxious → nervous
        assert scenes[1]["context_tags"]["expression"] == "nervous"
        # Scene 3: "낫" → calm → expressionless
        assert scenes[3]["context_tags"]["expression"] == "expressionless"

    def test_already_diverse_no_change(self):
        """이미 다양한 expression → 변경 없음."""
        scenes = [
            {"speaker": "A", "script": "test", "context_tags": {"expression": "smile"}},
            {"speaker": "B", "script": "test", "context_tags": {"expression": "sad"}},
            {"speaker": "A", "script": "test", "context_tags": {"expression": "surprised"}},
            {"speaker": "B", "script": "test", "context_tags": {"expression": "nervous"}},
        ]
        original = [s["context_tags"]["expression"] for s in scenes]
        diversify_expressions(scenes)
        result = [s["context_tags"]["expression"] for s in scenes]
        assert result == original

    def test_narrator_scenes_excluded(self):
        """Narrator 씬은 다양성 계산에서 제외."""
        scenes = [
            {"speaker": "A", "script": "test", "context_tags": {"expression": "smile"}},
            {"speaker": "Narrator", "script": "bg", "context_tags": {"expression": "smile"}},
            {"speaker": "B", "script": "test", "context_tags": {"expression": "sad"}},
        ]
        diversify_expressions(scenes)
        # Narrator expression 변경 없음
        assert scenes[1]["context_tags"]["expression"] == "smile"

    def test_scenes_with_emotion_preserved(self):
        """emotion이 이미 있는 씬은 건너뜀."""
        scenes = [
            {"speaker": "A", "script": "어려워", "context_tags": {"expression": "smile", "emotion": "happy"}},
            {"speaker": "B", "script": "어려워", "context_tags": {"expression": "smile"}},
            {"speaker": "A", "script": "힘들어", "context_tags": {"expression": "smile"}},
            {"speaker": "B", "script": "걱정돼", "context_tags": {"expression": "smile"}},
        ]
        diversify_expressions(scenes)
        # emotion이 있는 Scene 0은 변경 없음
        assert scenes[0]["context_tags"]["expression"] == "smile"
        assert scenes[0]["context_tags"]["emotion"] == "happy"

    def test_fewer_than_3_scenes_skipped(self):
        """캐릭터 씬 3개 미만이면 건너뜀."""
        scenes = [
            {"speaker": "A", "script": "test", "context_tags": {"expression": "smile"}},
            {"speaker": "B", "script": "test", "context_tags": {"expression": "smile"}},
        ]
        diversify_expressions(scenes)
        assert scenes[0]["context_tags"]["expression"] == "smile"
        assert scenes[1]["context_tags"]["expression"] == "smile"
