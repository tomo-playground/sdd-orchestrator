"""LangFuse Prompt Management 단위 테스트.

LangFuse 네이티브 compile() 전환 완료 후:
- _to_langfuse_name: 프롬프트→LangFuse 이름 매핑 검증
- LANGFUSE_MANAGED_TEMPLATES: 관리 대상 목록 검증
- compile_prompt: LangFuse compile() 경로 검증
- prompt_partials: Python 기반 파셜 렌더 검증
"""

from __future__ import annotations

from services.agent.langfuse_prompt import (
    A_GRADE_TEMPLATES,
    LANGFUSE_MANAGED_TEMPLATES,
    _to_langfuse_name,
)


class TestToLangfuseName:
    """프롬프트 이름 → LangFuse 이름 변환 테스트 (폴더 기반 매핑)."""

    def test_creative_prefix_mapped(self):
        assert _to_langfuse_name("creative/analyze_topic") == "tool/analyze-topic"

    def test_root_template_mapped(self):
        assert _to_langfuse_name("review_evaluate") == "pipeline/review/evaluate"

    def test_create_storyboard_variant_mapped(self):
        assert _to_langfuse_name("create_storyboard_dialogue") == "storyboard/dialogue"

    def test_underscore_to_hyphen_mapped(self):
        assert _to_langfuse_name("creative/sound_designer") == "pipeline/sound-designer"

    def test_storyboard_root_mapped(self):
        assert _to_langfuse_name("create_storyboard") == "storyboard/default"

    def test_validate_image_tags_mapped(self):
        assert _to_langfuse_name("validate_image_tags") == "tool/validate-image-tags"

    def test_unmapped_fallback(self):
        """매핑되지 않은 프롬프트는 기존 로직으로 변환."""
        assert _to_langfuse_name("creative/new_feature") == "new-feature"
        assert _to_langfuse_name("some_template") == "some-template"


class TestManagedTemplates:
    """LangFuse 관리 프롬프트 목록 검증."""

    def test_count(self):
        assert len(LANGFUSE_MANAGED_TEMPLATES) == 32

    def test_backward_compat_alias(self):
        assert A_GRADE_TEMPLATES is LANGFUSE_MANAGED_TEMPLATES

    def test_no_j2_extension(self):
        for t in LANGFUSE_MANAGED_TEMPLATES:
            assert not t.endswith(".j2"), f"{t}에 .j2 확장자가 남아 있습니다"

    def test_b_grade_templates_included(self):
        """B등급 9개 + 파셜전환 5개 포함 확인."""
        expected = {
            "creative/director",
            "creative/scriptwriter",
            "creative/director_plan",
            "creative/writer_planning",
            "creative/tts_designer",
            "creative/director_checkpoint",
            "creative/explain",
            "creative/director_evaluate",
            "creative/review_unified",
            "creative/cinematographer",
            "create_storyboard",
            "create_storyboard_confession",
            "create_storyboard_dialogue",
            "create_storyboard_narrated",
        }
        assert expected.issubset(LANGFUSE_MANAGED_TEMPLATES)


class TestCompilePrompt:
    """compile_prompt() 동작 테스트 (LangFuse 네이티브 경로)."""

    def test_langfuse_compile_success(self):
        """LangFuse compile()로 system/user 분리 성공."""
        from unittest.mock import MagicMock, patch

        from services.agent.langfuse_prompt import compile_prompt

        mock_prompt = MagicMock()
        mock_prompt.compile.return_value = [
            {"role": "system", "content": "You are an evaluator."},
            {"role": "user", "content": "Analyze: test_topic"},
        ]

        mock_client = MagicMock()
        mock_client.get_prompt.return_value = mock_prompt

        with patch("services.agent.observability.get_langfuse_client", return_value=mock_client):
            result = compile_prompt("creative/analyze_topic", topic="test_topic")
            assert result.system == "You are an evaluator."
            assert "test_topic" in result.user
            assert result.langfuse_prompt is mock_prompt

    def test_langfuse_disabled_fallback(self):
        """LangFuse 비활성 시 빈 프롬프트 반환."""
        from unittest.mock import patch

        from services.agent.langfuse_prompt import compile_prompt

        with patch("services.agent.observability.get_langfuse_client", return_value=None):
            result = compile_prompt("validate_image_tags", tags_block="- smile")
            assert result.system == ""
            assert result.langfuse_prompt is None

    def test_langfuse_fetch_failure_fallback(self):
        """LangFuse fetch 실패 시 빈 프롬프트 반환."""
        from unittest.mock import MagicMock, patch

        from services.agent.langfuse_prompt import compile_prompt

        mock_client = MagicMock()
        mock_client.get_prompt.side_effect = Exception("LangFuse unavailable")

        with patch("services.agent.observability.get_langfuse_client", return_value=mock_client):
            result = compile_prompt("review_evaluate")
            assert result.system == ""
            assert result.langfuse_prompt is None


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
