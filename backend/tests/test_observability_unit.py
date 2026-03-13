"""observability 모듈 순수 함수 단위 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock

from services.agent.observability import (
    LLMCallResult,
    _current_root_span,
    _safe_extract_text,
    _to_hex32,
    end_root_span,
)


class TestToHex32:
    def test_uuid_to_hex(self):
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        assert _to_hex32(uuid_str) == "550e8400e29b41d4a716446655440000"

    def test_already_hex(self):
        hex_str = "550e8400e29b41d4a716446655440000"
        assert _to_hex32(hex_str) == hex_str

    def test_empty_string(self):
        assert _to_hex32("") == ""


class TestSafeExtractText:
    def test_normal_response(self):
        part = MagicMock()
        part.text = "Hello world"
        content = MagicMock()
        content.parts = [part]
        candidate = MagicMock()
        candidate.content = content
        response = MagicMock()
        response.candidates = [candidate]

        assert _safe_extract_text(response) == "Hello world"

    def test_multiple_parts(self):
        part1 = MagicMock()
        part1.text = "Hello "
        part2 = MagicMock()
        part2.text = "world"
        content = MagicMock()
        content.parts = [part1, part2]
        candidate = MagicMock()
        candidate.content = content
        response = MagicMock()
        response.candidates = [candidate]

        assert _safe_extract_text(response) == "Hello world"

    def test_no_candidates(self):
        response = MagicMock()
        response.candidates = []
        assert _safe_extract_text(response) == ""

    def test_none_candidates(self):
        response = MagicMock()
        response.candidates = None
        assert _safe_extract_text(response) == ""

    def test_no_parts(self):
        candidate = MagicMock()
        candidate.content = MagicMock()
        candidate.content.parts = None
        response = MagicMock()
        response.candidates = [candidate]
        assert _safe_extract_text(response) == ""

    def test_part_without_text_attr(self):
        part = MagicMock(spec=[])  # no text attribute
        content = MagicMock()
        content.parts = [part]
        candidate = MagicMock()
        candidate.content = content
        response = MagicMock()
        response.candidates = [candidate]
        assert _safe_extract_text(response) == ""

    def test_exception_fallback(self):
        response = MagicMock()
        response.candidates = None
        response.text = "fallback text"
        # Force candidates check to work (returns None), so fallback to response.text
        assert _safe_extract_text(response) == ""


class TestLLMCallResult:
    def test_record_extracts_text(self):
        result = LLMCallResult()
        part = MagicMock()
        part.text = "response text"
        content = MagicMock()
        content.parts = [part]
        candidate = MagicMock()
        candidate.content = content
        response = MagicMock()
        response.candidates = [candidate]
        response.usage_metadata = None

        result.record(response)
        assert result.output == "response text"
        assert result.usage is None

    def test_record_extracts_usage(self):
        result = LLMCallResult()
        part = MagicMock()
        part.text = "text"
        content = MagicMock()
        content.parts = [part]
        candidate = MagicMock()
        candidate.content = content
        response = MagicMock()
        response.candidates = [candidate]
        meta = MagicMock()
        meta.prompt_token_count = 100
        meta.candidates_token_count = 50
        meta.total_token_count = 150
        response.usage_metadata = meta

        result.record(response)
        assert result.usage == {"input": 100, "output": 50, "total": 150}

    def test_default_values(self):
        result = LLMCallResult()
        assert result.generation is None
        assert result.output == ""
        assert result.usage is None


class TestEndRootSpan:
    def test_ends_and_clears_span(self):
        mock_span = MagicMock()
        _current_root_span.set(mock_span)

        end_root_span()

        mock_span.end.assert_called_once()
        assert _current_root_span.get() is None

    def test_noop_when_no_span(self):
        _current_root_span.set(None)
        end_root_span()  # 예외 없이 통과

    def test_idempotent(self):
        mock_span = MagicMock()
        _current_root_span.set(mock_span)

        end_root_span()
        end_root_span()  # 두 번째 호출도 안전

        mock_span.end.assert_called_once()

    def test_swallows_exception(self):
        mock_span = MagicMock()
        mock_span.end.side_effect = RuntimeError("connection lost")
        _current_root_span.set(mock_span)

        end_root_span()  # 예외 삼키고 정상 종료
        assert _current_root_span.get() is None
