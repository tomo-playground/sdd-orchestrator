"""LangFuse Prompt Management 단위 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from services.agent.langfuse_prompt import (
    A_GRADE_TEMPLATES,
    PromptBundle,
    _to_langfuse_name,
    get_prompt_template,
)


class TestToLangfuseName:
    """템플릿 경로 → LangFuse 이름 변환 테스트."""

    def test_creative_prefix_removed(self):
        assert _to_langfuse_name("creative/analyze_topic.j2") == "analyze-topic"

    def test_root_template(self):
        assert _to_langfuse_name("review_evaluate.j2") == "review-evaluate"

    def test_partial_prefix(self):
        assert _to_langfuse_name("_partials/character_profile.j2") == "partial-character-profile"

    def test_underscore_to_hyphen(self):
        assert _to_langfuse_name("creative/sound_designer.j2") == "sound-designer"

    def test_storyboard_root(self):
        assert _to_langfuse_name("create_storyboard.j2") == "create-storyboard"

    def test_validate_image_tags(self):
        assert _to_langfuse_name("validate_image_tags.j2") == "validate-image-tags"


class TestAGradeTemplates:
    """A등급 템플릿 목록 검증."""

    def test_count(self):
        assert len(A_GRADE_TEMPLATES) == 14

    def test_all_are_j2(self):
        for t in A_GRADE_TEMPLATES:
            assert t.endswith(".j2"), f"{t}는 .j2로 끝나야 합니다"

    def test_no_includes_in_a_grade(self):
        """A등급 템플릿에는 {% include %} 사용 금지."""
        from pathlib import Path

        templates_dir = Path(__file__).resolve().parent.parent / "templates"
        for t in A_GRADE_TEMPLATES:
            content = (templates_dir / t).read_text(encoding="utf-8")
            assert "{% include" not in content, f"A등급 {t}에 include 발견 — B등급으로 재분류 필요"


class TestPromptBundle:
    """PromptBundle 구조 테스트."""

    def test_default_values(self):
        from jinja2 import Template

        tmpl = Template("hello")
        bundle = PromptBundle(template=tmpl)
        assert bundle.system_instruction is None
        assert bundle.langfuse_prompt is None

    def test_with_system_instruction(self):
        from jinja2 import Template

        tmpl = Template("hello")
        bundle = PromptBundle(template=tmpl, system_instruction="You are a helper.")
        assert bundle.system_instruction == "You are a helper."


class TestGetPromptTemplate:
    """get_prompt_template() 동작 테스트."""

    def test_b_grade_always_file_fallback(self):
        """B등급 템플릿은 항상 로컬 파일 사용."""
        bundle = get_prompt_template("creative/cinematographer.j2")
        assert isinstance(bundle, PromptBundle)
        assert bundle.langfuse_prompt is None
        assert bundle.system_instruction is None
        assert hasattr(bundle.template, "render")

    def test_a_grade_fallback_when_langfuse_disabled(self):
        """LangFuse 비활성 시 A등급도 로컬 파일 사용."""
        with patch("services.agent.observability.get_langfuse_client", return_value=None):
            bundle = get_prompt_template("creative/analyze_topic.j2")
            assert bundle.langfuse_prompt is None
            assert bundle.system_instruction is None

    def test_a_grade_text_prompt_compat(self):
        """text 타입 LangFuse 프롬프트 (하위 호환)."""
        mock_prompt = MagicMock()
        mock_prompt.prompt = "Hello {{ topic }}"
        mock_prompt.version = 1

        mock_client = MagicMock()
        mock_client.get_prompt.return_value = mock_prompt

        with patch("services.agent.observability.get_langfuse_client", return_value=mock_client):
            bundle = get_prompt_template("creative/analyze_topic.j2")
            assert bundle.langfuse_prompt is mock_prompt
            assert bundle.system_instruction is None  # text 타입은 system 없음
            rendered = bundle.template.render(topic="테스트")
            assert rendered == "Hello 테스트"

    def test_a_grade_chat_prompt_with_system(self):
        """chat 타입 LangFuse 프롬프트 — system + user 분리."""
        mock_prompt = MagicMock()
        mock_prompt.prompt = [
            {"role": "system", "content": "You are a Location Planner."},
            {"role": "user", "content": "Plan for {{ topic }}"},
        ]
        mock_prompt.version = 2

        mock_client = MagicMock()
        mock_client.get_prompt.return_value = mock_prompt

        with patch("services.agent.observability.get_langfuse_client", return_value=mock_client):
            bundle = get_prompt_template("creative/location_planner.j2")
            assert bundle.system_instruction == "You are a Location Planner."
            assert bundle.langfuse_prompt is mock_prompt
            rendered = bundle.template.render(topic="카페")
            assert rendered == "Plan for 카페"

    def test_a_grade_chat_prompt_no_system(self):
        """chat 타입이지만 system 메시지 없는 경우."""
        mock_prompt = MagicMock()
        mock_prompt.prompt = [
            {"role": "user", "content": "Analyze {{ topic }}"},
        ]
        mock_prompt.version = 1

        mock_client = MagicMock()
        mock_client.get_prompt.return_value = mock_prompt

        with patch("services.agent.observability.get_langfuse_client", return_value=mock_client):
            bundle = get_prompt_template("creative/sound_designer.j2")
            assert bundle.system_instruction is None
            rendered = bundle.template.render(topic="BGM")
            assert rendered == "Analyze BGM"

    def test_a_grade_langfuse_fetch_failure_fallback(self):
        """LangFuse fetch 실패 시 로컬 파일 fallback."""
        mock_client = MagicMock()
        mock_client.get_prompt.side_effect = Exception("LangFuse unavailable")

        with patch("services.agent.observability.get_langfuse_client", return_value=mock_client):
            bundle = get_prompt_template("creative/analyze_topic.j2")
            assert bundle.langfuse_prompt is None
            assert bundle.system_instruction is None

    def test_langfuse_chat_with_jinja2_loop(self):
        """chat 타입에서 user 메시지의 Jinja2 루프 렌더링."""
        mock_prompt = MagicMock()
        mock_prompt.prompt = [
            {"role": "system", "content": "You are an evaluator."},
            {"role": "user", "content": "Tags:\n{% for tag in tags %}- {{ tag }}\n{% endfor %}"},
        ]
        mock_prompt.version = 1

        mock_client = MagicMock()
        mock_client.get_prompt.return_value = mock_prompt

        with patch("services.agent.observability.get_langfuse_client", return_value=mock_client):
            bundle = get_prompt_template("validate_image_tags.j2")
            assert bundle.system_instruction == "You are an evaluator."
            rendered = bundle.template.render(tags=["smile", "brown_hair"])
            assert "- smile" in rendered
            assert "- brown_hair" in rendered

    def test_langfuse_chat_with_tojson(self):
        """chat 타입에서 tojson 필터 렌더링."""
        mock_prompt = MagicMock()
        mock_prompt.prompt = [
            {"role": "system", "content": "Analyze."},
            {"role": "user", "content": "Data: {{ data | tojson }}"},
        ]
        mock_prompt.version = 1

        mock_client = MagicMock()
        mock_client.get_prompt.return_value = mock_prompt

        with patch("services.agent.observability.get_langfuse_client", return_value=mock_client):
            bundle = get_prompt_template("creative/sound_designer.j2")
            rendered = bundle.template.render(data={"key": "value"})
            assert '"key"' in rendered
