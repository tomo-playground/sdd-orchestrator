"""Tests for _sanitize_candidates_for_db helper."""

from schemas import SceneCandidate
from services.storyboard import _sanitize_candidates_for_db


def test_sanitize_strips_image_url_from_pydantic():
    """SceneCandidate.model_dump should exclude image_url."""
    candidates = [
        SceneCandidate(media_asset_id=1, match_rate=0.85, image_url="http://example.com/img.png"),
        SceneCandidate(media_asset_id=2, match_rate=0.70),
    ]
    result = _sanitize_candidates_for_db(candidates)

    assert len(result) == 2
    assert "image_url" not in result[0]
    assert result[0]["media_asset_id"] == 1
    assert result[0]["match_rate"] == 0.85
    assert "image_url" not in result[1]
    assert result[1]["media_asset_id"] == 2


def test_sanitize_strips_image_url_from_dicts():
    """Plain dicts with image_url should have it removed."""
    candidates = [
        {"media_asset_id": 10, "match_rate": 0.9, "image_url": "http://localhost/a.png"},
        {"media_asset_id": 20, "match_rate": 0.5},
    ]
    result = _sanitize_candidates_for_db(candidates)

    assert len(result) == 2
    assert "image_url" not in result[0]
    assert result[0]["media_asset_id"] == 10
    assert "image_url" not in result[1]


def test_sanitize_empty_candidates():
    """Empty list should return empty list."""
    result = _sanitize_candidates_for_db([])
    assert result == []
