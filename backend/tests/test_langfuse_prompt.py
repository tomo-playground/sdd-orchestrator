"""LangFuse Prompt Management 단위 테스트.

LangFuse 네이티브 compile() 전환 완료 후:
- _to_langfuse_name: 템플릿→LangFuse 이름 매핑 검증
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
    """템플릿 경로 → LangFuse 이름 변환 테스트 (폴더 기반 매핑)."""

    def test_creative_prefix_mapped(self):
        assert _to_langfuse_name("creative/analyze_topic.j2") == "tool/analyze-topic"

    def test_root_template_mapped(self):
        assert _to_langfuse_name("review_evaluate.j2") == "pipeline/review/evaluate"

    def test_create_storyboard_variant_mapped(self):
        assert _to_langfuse_name("create_storyboard_dialogue.j2") == "storyboard/dialogue"

    def test_underscore_to_hyphen_mapped(self):
        assert _to_langfuse_name("creative/sound_designer.j2") == "pipeline/sound-designer"

    def test_storyboard_root_mapped(self):
        assert _to_langfuse_name("create_storyboard.j2") == "storyboard/default"

    def test_validate_image_tags_mapped(self):
        assert _to_langfuse_name("validate_image_tags.j2") == "tool/validate-image-tags"

    def test_unmapped_fallback(self):
        """매핑되지 않은 템플릿은 기존 로직으로 변환."""
        assert _to_langfuse_name("creative/new_feature.j2") == "new-feature"
        assert _to_langfuse_name("some_template.j2") == "some-template"


class TestManagedTemplates:
    """LangFuse 관리 템플릿 목록 검증."""

    def test_count(self):
        assert len(LANGFUSE_MANAGED_TEMPLATES) == 28  # A등급 14 + B등급 9 + include제거 5

    def test_backward_compat_alias(self):
        assert A_GRADE_TEMPLATES is LANGFUSE_MANAGED_TEMPLATES

    def test_all_are_j2(self):
        for t in LANGFUSE_MANAGED_TEMPLATES:
            assert t.endswith(".j2"), f"{t}는 .j2로 끝나야 합니다"

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
            result = compile_prompt("creative/analyze_topic.j2", topic="test_topic")
            assert result.system == "You are an evaluator."
            assert "test_topic" in result.user
            assert result.langfuse_prompt is mock_prompt

    def test_langfuse_disabled_fallback(self):
        """LangFuse 비활성 시 로컬 .j2 파일 fallback."""
        from unittest.mock import patch

        from services.agent.langfuse_prompt import compile_prompt

        with patch("services.agent.observability.get_langfuse_client", return_value=None):
            result = compile_prompt("validate_image_tags.j2", tags_block="- smile")
            assert result.system == ""
            assert result.langfuse_prompt is None

    def test_langfuse_fetch_failure_fallback(self):
        """LangFuse fetch 실패 시 로컬 .j2 파일 fallback."""
        from unittest.mock import MagicMock, patch

        from services.agent.langfuse_prompt import compile_prompt

        mock_client = MagicMock()
        mock_client.get_prompt.side_effect = Exception("LangFuse unavailable")

        with patch("services.agent.observability.get_langfuse_client", return_value=mock_client):
            result = compile_prompt("review_evaluate.j2")
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
