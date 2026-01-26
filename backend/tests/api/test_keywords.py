from fastapi.testclient import TestClient


def test_get_keyword_priority(client: TestClient):
    """Test getting keyword priorities."""
    response = client.get("/keywords/priority")
    assert response.status_code == 200
    data = response.json()
    assert "priority" in data
    assert "patterns" in data
    assert data["priority"]["quality"] == 1
    assert "1girl" in data["patterns"]["subject"]

def test_get_keyword_categories(client: TestClient):
    """Test getting keyword categories."""
    response = client.get("/keywords/categories")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    # Note: Depending on DB state, this might be empty or populated.
    # We just check the structure for now.
    assert isinstance(data["categories"], dict)

def test_get_keyword_suggestions(client: TestClient):
    """Test getting keyword suggestions."""
    response = client.get("/keywords/suggestions?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)
