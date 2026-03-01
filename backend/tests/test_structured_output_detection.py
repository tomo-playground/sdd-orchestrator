"""_is_likely_structured_output 판별 함수 단위 테스트."""

from __future__ import annotations

from services.agent.tools.base import _is_likely_structured_output


class TestIsLikelyStructuredOutput:
    def test_json_object(self):
        assert _is_likely_structured_output('{"key": "value"}') is True

    def test_json_array(self):
        assert _is_likely_structured_output("[1, 2, 3]") is True

    def test_markdown_fenced_json(self):
        assert _is_likely_structured_output("```json\n{}\n```") is True

    def test_json_embedded_in_text(self):
        assert _is_likely_structured_output("result: {scenes: []}") is True

    def test_plain_text(self):
        assert _is_likely_structured_output("This is plain text") is False

    def test_korean_text(self):
        assert _is_likely_structured_output("네, 알겠습니다. 작업을 완료했습니다.") is False

    def test_empty_string(self):
        assert _is_likely_structured_output("") is False

    def test_whitespace_only(self):
        assert _is_likely_structured_output("   \n\t  ") is False

    def test_braces_in_text(self):
        # Contains { and } so should be True
        assert _is_likely_structured_output("The function returns {result}") is True
