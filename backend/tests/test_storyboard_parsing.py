"""Tests for Gemini response parsing utilities in storyboard service.

Covers:
- Markdown code block stripping (P0 fix)
- scene_tags -> context_tags field name normalization
- Duration-based scene count calculation and trimming
"""

import json

from services.storyboard import (
    normalize_scene_tags_key,
    strip_markdown_codeblock,
)

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


# ---------------------------------------------------------------------------
# calculate_max_scenes
# ---------------------------------------------------------------------------


class TestCalculateMaxScenes:
    """Tests for duration-based max scene count calculation."""

    def test_10s_max_5_scenes(self):
        """10 seconds → max 5 scenes (ceil(10/2))."""
        from services.storyboard import calculate_max_scenes

        assert calculate_max_scenes(10) == 5

    def test_30s_max_15_scenes(self):
        """30 seconds → max 15 scenes."""
        from services.storyboard import calculate_max_scenes

        assert calculate_max_scenes(30) == 15

    def test_45s_max_23_scenes(self):
        """45 seconds → max 23 scenes (ceil(45/2) = 23)."""
        from services.storyboard import calculate_max_scenes

        assert calculate_max_scenes(45) == 23

    def test_60s_max_30_scenes(self):
        """60 seconds → max 30 scenes."""
        from services.storyboard import calculate_max_scenes

        assert calculate_max_scenes(60) == 30

    def test_minimum_1_scene(self):
        """Very short duration still returns at least 1."""
        from services.storyboard import calculate_max_scenes

        assert calculate_max_scenes(1) == 1

    def test_odd_duration(self):
        """Odd duration rounds up: 15s → ceil(15/2) = 8."""
        from services.storyboard import calculate_max_scenes

        assert calculate_max_scenes(15) == 8


# ---------------------------------------------------------------------------
# trim_scenes_to_duration
# ---------------------------------------------------------------------------


class TestTrimScenesToDuration:
    """Tests for trimming excess Gemini scenes based on duration."""

    def _make_scenes(self, count: int) -> list[dict]:
        return [{"scene_id": i + 1, "script": f"Scene {i + 1}"} for i in range(count)]

    def test_no_trim_when_within_limit(self):
        """5 scenes for 10s (max=5) → no trim."""
        from services.storyboard import trim_scenes_to_duration

        scenes = self._make_scenes(5)
        result = trim_scenes_to_duration(scenes, 10)
        assert len(result) == 5

    def test_trim_9_scenes_to_5_for_10s(self):
        """9 scenes for 10s (max=5) → trimmed to 5."""
        from services.storyboard import trim_scenes_to_duration

        scenes = self._make_scenes(9)
        result = trim_scenes_to_duration(scenes, 10)
        assert len(result) == 5
        assert result[-1]["scene_id"] == 5

    def test_trim_20_scenes_to_15_for_30s(self):
        """20 scenes for 30s (max=15) → trimmed to 15."""
        from services.storyboard import trim_scenes_to_duration

        scenes = self._make_scenes(20)
        result = trim_scenes_to_duration(scenes, 30)
        assert len(result) == 15

    def test_no_trim_when_fewer_than_max(self):
        """3 scenes for 30s (max=15) → no trim."""
        from services.storyboard import trim_scenes_to_duration

        scenes = self._make_scenes(3)
        result = trim_scenes_to_duration(scenes, 30)
        assert len(result) == 3

    def test_empty_scenes_returns_empty(self):
        """0 scenes → empty list."""
        from services.storyboard import trim_scenes_to_duration

        result = trim_scenes_to_duration([], 10)
        assert result == []

    def test_preserves_first_scenes_on_trim(self):
        """Trimming keeps the first N scenes (preserves story beginning)."""
        from services.storyboard import trim_scenes_to_duration

        scenes = self._make_scenes(10)
        result = trim_scenes_to_duration(scenes, 10)
        assert [s["scene_id"] for s in result] == [1, 2, 3, 4, 5]
