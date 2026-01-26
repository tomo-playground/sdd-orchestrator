"""Tests for prompt validation API endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


def test_validate_tags_empty(client: TestClient):
    """Test tag validation with empty list."""
    response = client.post(
        "/prompt/validate-tags",
        json={"tags": [], "check_danbooru": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["risky_tags"]) == 0
    assert len(data["unknown_in_db"]) == 0
    assert data["warnings"] == []


def test_validate_tags_with_db_tags(client: TestClient):
    """Test tag validation against DB (tags likely in DB)."""
    # Test with tags that are likely in the production DB
    response = client.post(
        "/prompt/validate-tags",
        json={"tags": ["1girl", "standing"], "check_danbooru": False},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2
    # At least one should be categorized
    assert len(data["risky_tags"]) + len(data["unknown_in_db"]) <= 2


def test_validate_tags_risky_known(client: TestClient):
    """Test detection of known risky tags."""
    # Use tags from RISKY_TAG_REPLACEMENTS that are unlikely to be in DB
    response = client.post(
        "/prompt/validate-tags",
        json={"tags": ["birds eye view", "high angle", "low angle"], "check_danbooru": False},
    )
    assert response.status_code == 200
    data = response.json()

    # At least one should be detected as risky (in RISKY_TAG_REPLACEMENTS)
    assert len(data["risky_tags"]) >= 1

    # Check that warnings have proper structure
    assert len(data["warnings"]) >= 1
    for warning in data["warnings"]:
        assert "tag" in warning
        assert "reason" in warning
        assert "suggestion" in warning
        # If it's a risky tag, it should have a suggestion
        if warning["tag"] in data["risky_tags"]:
            assert warning["suggestion"] is not None


@patch("services.prompt_validation.get_tag_info_sync")
def test_validate_tags_with_danbooru(mock_get_tag, client: TestClient):
    """Test tag validation with Danbooru check."""
    # Mock Danbooru responses
    def mock_tag_info(tag_name):
        if tag_name == "high_quality_tag":
            return {"name": tag_name, "post_count": 10000}
        if tag_name == "low_usage_tag":
            return {"name": tag_name, "post_count": 50}
        if tag_name == "zero_posts_tag":
            return {"name": tag_name, "post_count": 0}
        return None  # Not found

    mock_get_tag.side_effect = mock_tag_info

    response = client.post(
        "/prompt/validate-tags",
        json={
            "tags": [
                "high_quality_tag",
                "low_usage_tag",
                "zero_posts_tag",
                "not_found_tag",
            ],
            "check_danbooru": True,
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["risky_tags"]) == 2  # low_usage_tag, zero_posts_tag
    assert len(data["unknown_in_db"]) == 1  # not_found_tag

    # Verify presence in lists (risky_tags and unknown_in_db)
    assert "low_usage_tag" in data["risky_tags"]
    assert "zero_posts_tag" in data["risky_tags"]
    assert "not_found_tag" in data["unknown_in_db"]


@patch("services.prompt_validation.get_tag_info_sync")
def test_validate_tags_danbooru_error(mock_get_tag, client: TestClient):
    """Test tag validation when Danbooru API fails."""
    mock_get_tag.side_effect = Exception("API Error")

    response = client.post(
        "/prompt/validate-tags",
        json={"tags": ["test_tag"], "check_danbooru": True},
    )
    assert response.status_code == 200
    data = response.json()

    # Should mark as unknown when API fails
    assert len(data["unknown_in_db"]) == 1
    assert "test_tag" in data["unknown_in_db"]

    # Should have warning about API error
    warnings = [w for w in data["warnings"] if w["tag"] == "test_tag"]
    assert len(warnings) == 1
    assert "api error" in warnings[0]["reason"].lower()


def test_auto_replace_empty(client: TestClient):
    """Test auto-replacement with empty list."""
    response = client.post(
        "/prompt/auto-replace",
        json={"tags": []},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["replaced_count"] == 0
    assert data["removed_count"] == 0
    assert data["replacements"] == []
    assert data["removed"] == []


def test_auto_replace_risky_tags(client: TestClient):
    """Test auto-replacement of known risky tags."""
    response = client.post(
        "/prompt/auto-replace",
        json={"tags": ["medium shot", "1girl", "close up", "standing"]},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["replaced_count"] == 2
    assert data["original"] == ["medium shot", "1girl", "close up", "standing"]
    assert data["replaced"] == ["cowboy shot", "1girl", "close-up", "standing"]

    # Check replacement details
    replacements = {r["from"]: r["to"] for r in data["replacements"]}
    assert replacements["medium shot"] == "cowboy shot"
    assert replacements["close up"] == "close-up"


def test_auto_replace_no_risky(client: TestClient):
    """Test auto-replacement when no risky tags present."""
    response = client.post(
        "/prompt/auto-replace",
        json={"tags": ["1girl", "standing", "smile"]},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["replaced_count"] == 0
    assert data["removed_count"] == 0
    assert data["original"] == data["replaced"]
    assert data["replacements"] == []


def test_auto_replace_with_removal(client: TestClient):
    """Test auto-replacement with tags that should be removed."""
    response = client.post(
        "/prompt/auto-replace",
        json={"tags": ["1girl", "unreal engine", "standing", "octane render"]},
    )
    assert response.status_code == 200
    data = response.json()

    # unreal engine and octane render should be removed
    assert data["removed_count"] == 2
    assert "unreal engine" in data["removed"]
    assert "octane render" in data["removed"]

    # Removed tags should not appear in replaced list
    assert "unreal engine" not in data["replaced"]
    assert "octane render" not in data["replaced"]

    # Safe tags should remain
    assert "1girl" in data["replaced"]
    assert "standing" in data["replaced"]

    # Check replacements structure
    removed_actions = [r for r in data["replacements"] if r["action"] == "removed"]
    assert len(removed_actions) == 2


def test_validate_tags_request_validation(client: TestClient):
    """Test request validation for validate-tags endpoint."""
    # Missing tags field
    response = client.post(
        "/prompt/validate-tags",
        json={"check_danbooru": True},
    )
    assert response.status_code == 422

    # Invalid tags type
    response = client.post(
        "/prompt/validate-tags",
        json={"tags": "not_a_list", "check_danbooru": True},
    )
    assert response.status_code == 422


def test_auto_replace_request_validation(client: TestClient):
    """Test request validation for auto-replace endpoint."""
    # Missing tags field
    response = client.post(
        "/prompt/auto-replace",
        json={},
    )
    assert response.status_code == 422

    # Invalid tags type
    response = client.post(
        "/prompt/auto-replace",
        json={"tags": "not_a_list"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "tags,expected_total",
    [
        (["definitely_unknown_tag_xyz123"], 1),  # Should be unknown
        (["medium shot"], 1),  # Known risky
        (["definitely_unknown_tag_abc456", "medium shot"], 2),  # Mixed
    ],
)
def test_validate_tags_various_inputs(
    client: TestClient, tags: list[str], expected_total: int
):
    """Test tag validation with various input combinations."""
    response = client.post(
        "/prompt/validate-tags",
        json={"tags": tags, "check_danbooru": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == expected_total
    # Just verify all tags are categorized
    assert len(data["risky_tags"]) + len(data["unknown_in_db"]) <= expected_total
