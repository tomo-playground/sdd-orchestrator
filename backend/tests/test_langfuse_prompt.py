"""LangFuse Prompt Management 단위 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from services.agent.langfuse_prompt import (
    A_GRADE_TEMPLATES,
    LANGFUSE_MANAGED_TEMPLATES,
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

    def test_create_storyboard_variant(self):
        assert _to_langfuse_name("create_storyboard_dialogue.j2") == "create-storyboard-dialogue"

    def test_underscore_to_hyphen(self):
        assert _to_langfuse_name("creative/sound_designer.j2") == "sound-designer"

    def test_storyboard_root(self):
        assert _to_langfuse_name("create_storyboard.j2") == "create-storyboard"

    def test_validate_image_tags(self):
        assert _to_langfuse_name("validate_image_tags.j2") == "validate-image-tags"


class TestManagedTemplates:
    """LangFuse 관리 템플릿 목록 검증."""

    def test_count(self):
        assert len(LANGFUSE_MANAGED_TEMPLATES) == 28  # A등급 14 + B등급 9 + include제거 5

    def test_backward_compat_alias(self):
        assert A_GRADE_TEMPLATES is LANGFUSE_MANAGED_TEMPLATES

    def test_all_are_j2(self):
        for t in LANGFUSE_MANAGED_TEMPLATES:
            assert t.endswith(".j2"), f"{t}는 .j2로 끝나야 합니다"

    def test_no_includes_in_managed(self):
        """관리 대상 템플릿에는 {% include %} 사용 금지."""
        from pathlib import Path

        templates_dir = Path(__file__).resolve().parent.parent / "templates"
        for t in LANGFUSE_MANAGED_TEMPLATES:
            content = (templates_dir / t).read_text(encoding="utf-8")
            assert "{% include" not in content, f"관리 대상 {t}에 include 발견 — 제외 필요"

    def test_b_grade_templates_included(self):
        """B등급 9개 + include 제거 5개 포함 확인."""
        expected = {
            "creative/director.j2",
            "creative/scriptwriter.j2",
            "creative/director_plan.j2",
            "creative/writer_planning.j2",
            "creative/tts_designer.j2",
            "creative/director_checkpoint.j2",
            "creative/explain.j2",
            "creative/director_evaluate.j2",
            "creative/review_unified.j2",
            "creative/cinematographer.j2",
            "create_storyboard.j2",
            "create_storyboard_confession.j2",
            "create_storyboard_dialogue.j2",
            "create_storyboard_narrated.j2",
        }
        assert expected.issubset(LANGFUSE_MANAGED_TEMPLATES)


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

    def test_unmanaged_template_skips_langfuse(self):
        """LANGFUSE_MANAGED_TEMPLATES 외 템플릿은 LangFuse fetch를 시도하지 않음."""
        mock_client = MagicMock()

        with patch("services.agent.observability.get_langfuse_client", return_value=mock_client):
            # review_evaluate.j2는 managed → LangFuse 시도
            get_prompt_template("review_evaluate.j2")
            assert mock_client.get_prompt.called

            mock_client.reset_mock()

            # create_storyboard.j2는 managed → LangFuse 시도
            get_prompt_template("create_storyboard.j2")
            assert mock_client.get_prompt.called

    def test_b_grade_managed_uses_langfuse(self):
        """B등급(include 없음)도 LangFuse에서 fetch."""
        mock_prompt = MagicMock()
        mock_prompt.prompt = [
            {"role": "system", "content": "You are the Production Director."},
            {"role": "user", "content": "Results: {{ results | tojson }}"},
        ]
        mock_prompt.version = 1

        mock_client = MagicMock()
        mock_client.get_prompt.return_value = mock_prompt

        with patch("services.agent.observability.get_langfuse_client", return_value=mock_client):
            bundle = get_prompt_template("creative/director.j2")
            assert bundle.system_instruction == "You are the Production Director."
            assert bundle.langfuse_prompt is mock_prompt
            rendered = bundle.template.render(results={"test": True})
            assert '"test": true' in rendered

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


class TestPromptPartials:
    """prompt_partials 렌더 테스트."""

    def test_static_partials_not_empty(self):
        from services.agent.prompt_partials import EMOTION_CONSISTENCY_RULES, IMAGE_PROMPT_KO_RULES

        assert len(IMAGE_PROMPT_KO_RULES) > 100
        assert len(EMOTION_CONSISTENCY_RULES) > 100

    def test_render_selected_concept_none(self):
        from services.agent.prompt_partials import render_selected_concept

        assert render_selected_concept(None) == ""

    def test_render_selected_concept_with_data(self):
        from services.agent.prompt_partials import render_selected_concept

        result = render_selected_concept({"title": "Test", "concept": "Story", "strengths": ["a"]})
        assert "SELECTED CONCEPT" in result
        assert "Title: Test" in result
        assert "Strengths: a" in result

    def test_render_character_profile_none(self):
        from services.agent.prompt_partials import render_character_profile

        assert render_character_profile(None) == ""

    def test_render_character_profile_with_speaker(self):
        from services.agent.prompt_partials import render_character_profile

        ctx = {"name": "Harin", "gender": "female", "description": "Cheerful", "costume_tags": ["uniform"]}
        result = render_character_profile(ctx, "A")
        assert "SPEAKER A" in result
        assert "Harin" in result
        assert "uniform" in result

    def test_render_allowed_tags_empty(self):
        from services.agent.prompt_partials import render_allowed_tags

        assert render_allowed_tags({}) == ""

    def test_render_allowed_tags_with_data(self):
        from services.agent.prompt_partials import render_allowed_tags

        result = render_allowed_tags({"camera": ["close-up", "cowboy_shot"], "mood": ["peaceful"]})
        assert "close-up" in result
        assert "peaceful" in result
