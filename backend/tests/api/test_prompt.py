import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from models import TagAlias
from services.keywords.db_cache import TagAliasCache, TagRuleCache


@pytest.fixture(autouse=True)
def seed_prompt_rules():
    """Seed risky tag replacements and rules for tests."""
    db = SessionLocal()
    try:
        # Seed Aliases (Risky Tag Replacements)
        replacements = [
            ("medium shot", "cowboy_shot"),
            ("close up", "close-up"),
            ("birds eye view", "from above"),
            ("unreal engine", None),  # removed
            ("octane render", None),  # removed
        ]
        for source, target in replacements:
            existing = db.query(TagAlias).filter(TagAlias.source_tag == source).first()
            if not existing:
                db.add(TagAlias(source_tag=source, target_tag=target, is_active=True))

        db.commit()

        # Refresh Caches
        TagAliasCache.refresh(db)
        TagRuleCache.refresh(db)
    finally:
        db.close()
    yield


def test_validate_tags_empty(client: TestClient):
    """Test tag validation with empty list."""
    response = client.post(
        "/api/admin/prompt/validate-tags",
        json={"tags": [], "check_danbooru": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_tags"] == 0
    assert len(data["risky"]) == 0
    assert len(data["unknown"]) == 0
    assert data["warnings"] == []


def test_validate_tags_with_db_tags(client: TestClient):
    """Test tag validation against DB (tags likely in DB)."""
    # Test with tags that are likely in the production DB
    response = client.post(
        "/api/admin/prompt/validate-tags",
        json={"tags": ["1girl", "standing"], "check_danbooru": False},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total_tags"] == 2
    # At least one should be categorized
    assert len(data["risky"]) + len(data["unknown"]) <= 2


def test_validate_tags_risky_known(client: TestClient):
    """Test detection of known risky tags."""
    # Use tags from RISKY_TAG_REPLACEMENTS that are unlikely to be in DB
    response = client.post(
        "/api/admin/prompt/validate-tags",
        json={"tags": ["birds eye view", "high angle", "low angle"], "check_danbooru": False},
    )
    assert response.status_code == 200
    data = response.json()

    # At least one should be detected as risky (in RISKY_TAG_REPLACEMENTS)
    assert len(data["risky"]) >= 1

    # Check that warnings have proper structure
    assert len(data["warnings"]) >= 1
    for warning in data["warnings"]:
        assert "tag" in warning
        assert "reason" in warning
        assert "suggestion" in warning
        # If it's a risky tag, it should have a suggestion
        if warning["tag"] in data["risky"]:
            assert warning["suggestion"] is not None


@pytest.mark.skip(reason="Danbooru validation not ported to V3 (prompt_validation module removed)")
def test_validate_tags_with_danbooru(client: TestClient):
    """Test tag validation with Danbooru check."""


@pytest.mark.skip(reason="Danbooru validation not ported to V3 (prompt_validation module removed)")
def test_validate_tags_danbooru_error(client: TestClient):
    """Test tag validation when Danbooru API fails."""


def test_auto_replace_empty(client: TestClient):
    """Test auto-replacement with empty list."""
    response = client.post(
        "/api/admin/prompt/auto-replace",
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
        "/api/admin/prompt/auto-replace",
        json={"tags": ["medium shot", "1girl", "close up", "standing"]},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["replaced_count"] == 2
    assert data["original"] == ["medium shot", "1girl", "close up", "standing"]
    assert data["replaced"] == ["cowboy_shot", "1girl", "close-up", "standing"]

    # Check replacement details
    replacements = {r["from"]: r["to"] for r in data["replacements"]}
    assert replacements["medium shot"] == "cowboy_shot"
    assert replacements["close up"] == "close-up"


def test_auto_replace_no_risky(client: TestClient):
    """Test auto-replacement when no risky tags present."""
    response = client.post(
        "/api/admin/prompt/auto-replace",
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
        "/api/admin/prompt/auto-replace",
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
        "/api/admin/prompt/validate-tags",
        json={"check_danbooru": True},
    )
    assert response.status_code == 422

    # Invalid tags type
    response = client.post(
        "/api/admin/prompt/validate-tags",
        json={"tags": "not_a_list", "check_danbooru": True},
    )
    assert response.status_code == 422


def test_auto_replace_request_validation(client: TestClient):
    """Test request validation for auto-replace endpoint."""
    # Missing tags field
    response = client.post(
        "/api/admin/prompt/auto-replace",
        json={},
    )
    assert response.status_code == 422

    # Invalid tags type
    response = client.post(
        "/api/admin/prompt/auto-replace",
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
def test_validate_tags_various_inputs(client: TestClient, tags: list[str], expected_total: int):
    """Test tag validation with various input combinations."""
    response = client.post(
        "/api/admin/prompt/validate-tags",
        json={"tags": tags, "check_danbooru": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_tags"] == expected_total
    # Just verify all tags are categorized
    assert len(data["risky"]) + len(data["unknown"]) <= expected_total
