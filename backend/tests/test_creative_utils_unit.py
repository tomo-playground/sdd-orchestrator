"""creative_utils 순수 함수 단위 테스트."""

from __future__ import annotations

import pytest

from services.creative_utils import (
    _fix_json_escapes,
    _strip_preamble,
    parse_json_response,
    resolve_characters_from_context,
)

# ── _strip_preamble ──────────────────────────────────────


class TestStripPreamble:
    def test_strips_text_before_brace(self):
        assert _strip_preamble('some preamble {"key": "value"}') == '{"key": "value"}'

    def test_returns_none_when_no_brace(self):
        assert _strip_preamble("no json here") is None

    def test_preserves_pure_json(self):
        assert _strip_preamble('{"k": 1}') == '{"k": 1}'


# ── _fix_json_escapes ─────────────────────────────────────


class TestFixJsonEscapes:
    def test_valid_escapes_preserved(self):
        assert _fix_json_escapes(r"\"hello\"") == r"\"hello\""

    def test_invalid_backslash_doubled(self):
        result = _fix_json_escapes("\\q")
        assert result == "\\\\q"

    def test_valid_unicode_preserved(self):
        assert _fix_json_escapes("\\u0041") == "\\u0041"

    def test_invalid_unicode_escaped(self):
        # \uZZZZ is not valid hex
        result = _fix_json_escapes("\\uZZZZ")
        assert result == "\\\\uZZZZ"

    def test_trailing_backslash(self):
        result = _fix_json_escapes("test\\")
        assert result == "test\\\\"

    def test_empty_string(self):
        assert _fix_json_escapes("") == ""

    def test_newline_tab_preserved(self):
        assert _fix_json_escapes("\\n\\t") == "\\n\\t"


# ── parse_json_response ───────────────────────────────────


class TestParseJsonResponse:
    def test_plain_json(self):
        assert parse_json_response('{"key": "val"}') == {"key": "val"}

    def test_markdown_fenced(self):
        raw = '```json\n{"key": "val"}\n```'
        assert parse_json_response(raw) == {"key": "val"}

    def test_preamble_stripped(self):
        raw = '알겠습니다. {"key": "val"}'
        assert parse_json_response(raw) == {"key": "val"}

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="Empty"):
            parse_json_response("")

    def test_invalid_json_raises(self):
        with pytest.raises(Exception):
            parse_json_response("not json at all")

    def test_json_with_invalid_escapes_fixed(self):
        raw = '{"path": "C:\\new\\folder"}'
        result = parse_json_response(raw)
        assert "path" in result


# ── resolve_characters_from_context ───────────────────────


class TestResolveCharactersFromContext:
    def test_with_characters_key(self):
        ctx = {"characters": {"speaker_1": {"id": 1, "name": "하루", "tags": []}}}
        result = resolve_characters_from_context(ctx)
        assert result == {"speaker_1": {"id": 1, "name": "하루", "tags": []}}

    def test_legacy_character_name(self):
        ctx = {"character_name": "미도리", "character_id": 3}
        result = resolve_characters_from_context(ctx)
        assert "speaker_1" in result
        assert result["speaker_1"]["name"] == "미도리"
        assert result["speaker_1"]["id"] == 3

    def test_empty_context(self):
        assert resolve_characters_from_context({}) == {}

    def test_characters_key_takes_priority(self):
        ctx = {
            "characters": {"speaker_1": {"id": 1, "name": "하루", "tags": []}},
            "character_name": "미도리",
        }
        result = resolve_characters_from_context(ctx)
        assert result["speaker_1"]["name"] == "하루"
