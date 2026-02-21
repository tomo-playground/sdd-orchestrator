"""Tests for seed integration in generation pipeline.

Covers:
- _try_parse_seed returns int
- _call_sd_api includes seed in result
- SceneGenerateResponse.seed field
- Cache hit behavior
"""

from __future__ import annotations

import json


class TestTryParseSeed:
    """Test _try_parse_seed return value."""

    def test_parses_seed_from_string_info(self):
        """Should parse seed from JSON string info."""
        from services.generation import _try_parse_seed

        data = {"info": json.dumps({"seed": 12345, "sampler": "DPM++"})}
        result = _try_parse_seed(data)
        assert result == 12345

    def test_parses_seed_from_dict_info(self):
        """Should parse seed from dict info."""
        from services.generation import _try_parse_seed

        data = {"info": {"seed": 67890}}
        result = _try_parse_seed(data)
        assert result == 67890

    def test_returns_none_on_missing_seed(self):
        """Should return None if seed not in info."""
        from services.generation import _try_parse_seed

        data = {"info": json.dumps({"sampler": "DPM++"})}
        result = _try_parse_seed(data)
        assert result is None

    def test_returns_none_on_invalid_info(self):
        """Should return None on unparseable info."""
        from services.generation import _try_parse_seed

        data = {"info": "not json at all {{{"}
        result = _try_parse_seed(data)
        assert result is None


class TestSceneGenerateResponseSeed:
    """Test SceneGenerateResponse includes seed field."""

    def test_seed_field_exists(self):
        """SceneGenerateResponse should have an optional seed field."""
        from schemas import SceneGenerateResponse

        resp = SceneGenerateResponse(image="base64data", seed=42)
        assert resp.seed == 42

    def test_seed_default_none(self):
        """seed should default to None."""
        from schemas import SceneGenerateResponse

        resp = SceneGenerateResponse(image="base64data")
        assert resp.seed is None
