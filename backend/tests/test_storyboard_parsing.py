"""Tests for Gemini response parsing utilities in storyboard service.

Covers:
- Markdown code block stripping (P0 fix)
- scene_tags -> context_tags field name normalization
"""

import json

import pytest

from services.storyboard import normalize_scene_tags_key, strip_markdown_codeblock


# ---------------------------------------------------------------------------
# strip_markdown_codeblock
# ---------------------------------------------------------------------------

class TestStripMarkdownCodeblock:
    """Tests for stripping markdown code block fences from Gemini responses."""

    def test_plain_json_no_codeblock(self):
        """Plain JSON without code block is returned as-is (stripped)."""
        raw = '  [{"scene_id": 1}]  '
        assert strip_markdown_codeblock(raw) == '[{"scene_id": 1}]'

    def test_json_codeblock_lowercase(self):
        """Standard ```json ... ``` is stripped correctly."""
        raw = '```json\n[{"scene_id": 1}]\n```'
        result = strip_markdown_codeblock(raw)
        assert json.loads(result) == [{"scene_id": 1}]

    def test_json_codeblock_uppercase(self):
        """```JSON ... ``` (uppercase) is stripped correctly."""
        raw = '```JSON\n[{"scene_id": 1}]\n```'
        result = strip_markdown_codeblock(raw)
        assert json.loads(result) == [{"scene_id": 1}]

    def test_generic_codeblock_no_lang(self):
        """``` ... ``` without language tag is stripped correctly."""
        raw = '```\n[{"scene_id": 1}]\n```'
        result = strip_markdown_codeblock(raw)
        assert json.loads(result) == [{"scene_id": 1}]

    def test_codeblock_with_surrounding_text(self):
        """Text before/after code block is ignored; only content inside is returned."""
        raw = 'Here is the storyboard:\n```json\n[{"scene_id": 1}]\n```\nEnd of response.'
        result = strip_markdown_codeblock(raw)
        assert json.loads(result) == [{"scene_id": 1}]

    def test_codeblock_with_leading_trailing_whitespace(self):
        """Whitespace around the code block is handled gracefully."""
        raw = '\n\n  ```json\n  [{"scene_id": 1}]  \n  ```\n\n'
        result = strip_markdown_codeblock(raw)
        assert json.loads(result) == [{"scene_id": 1}]

    def test_multiline_json_in_codeblock(self):
        """Multi-line JSON inside code block is preserved correctly."""
        raw = '```json\n[\n  {\n    "scene_id": 1,\n    "script": "hello"\n  }\n]\n```'
        result = strip_markdown_codeblock(raw)
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["script"] == "hello"

    def test_codeblock_with_extra_newlines(self):
        """Code block with extra blank lines inside is handled."""
        raw = '```json\n\n[{"scene_id": 1}]\n\n```'
        result = strip_markdown_codeblock(raw)
        assert json.loads(result) == [{"scene_id": 1}]


# ---------------------------------------------------------------------------
# normalize_scene_tags_key
# ---------------------------------------------------------------------------

class TestNormalizeSceneTagsKey:
    """Tests for scene_tags -> context_tags field name normalization."""

    def test_scene_tags_renamed_to_context_tags(self):
        """'scene_tags' key is renamed to 'context_tags'."""
        scenes = [
            {
                "scene_id": 1,
                "scene_tags": {"expression": ["smile"], "environment": ["classroom"]},
            }
        ]
        result = normalize_scene_tags_key(scenes)
        assert "context_tags" in result[0]
        assert "scene_tags" not in result[0]
        assert result[0]["context_tags"]["expression"] == ["smile"]

    def test_context_tags_already_present(self):
        """When 'context_tags' already exists, it is kept (no overwrite)."""
        scenes = [
            {
                "scene_id": 1,
                "context_tags": {"expression": ["smile"]},
            }
        ]
        result = normalize_scene_tags_key(scenes)
        assert result[0]["context_tags"]["expression"] == ["smile"]
        assert "scene_tags" not in result[0]

    def test_both_keys_present_context_tags_wins(self):
        """If both keys exist, 'context_tags' is preserved and 'scene_tags' is kept."""
        scenes = [
            {
                "scene_id": 1,
                "scene_tags": {"expression": ["angry"]},
                "context_tags": {"expression": ["smile"]},
            }
        ]
        result = normalize_scene_tags_key(scenes)
        # context_tags should not be overwritten
        assert result[0]["context_tags"]["expression"] == ["smile"]

    def test_neither_key_present(self):
        """When neither key exists, no key is added."""
        scenes = [{"scene_id": 1, "script": "hello"}]
        result = normalize_scene_tags_key(scenes)
        assert "context_tags" not in result[0]
        assert "scene_tags" not in result[0]

    def test_multiple_scenes_mixed(self):
        """Normalization works across multiple scenes with mixed field names."""
        scenes = [
            {"scene_id": 1, "scene_tags": {"mood": ["calm"]}},
            {"scene_id": 2, "context_tags": {"mood": ["tense"]}},
            {"scene_id": 3},
        ]
        result = normalize_scene_tags_key(scenes)
        assert result[0]["context_tags"]["mood"] == ["calm"]
        assert "scene_tags" not in result[0]
        assert result[1]["context_tags"]["mood"] == ["tense"]
        assert "context_tags" not in result[2]

    def test_empty_list(self):
        """Empty scenes list returns empty list."""
        assert normalize_scene_tags_key([]) == []
