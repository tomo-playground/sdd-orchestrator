from fastapi.testclient import TestClient


def test_list_presets(client: TestClient):
    """Test listing presets."""
    response = client.get("/api/v1/presets")
    assert response.status_code == 200
    data = response.json()
    assert "presets" in data
    assert isinstance(data["presets"], list)
    assert len(data["presets"]) > 0
    # Check for expected fields in the first preset
    preset = data["presets"][0]
    assert "id" in preset
    assert "name" in preset
    assert "structure" in preset

def test_get_preset_detail(client: TestClient):
    """Test getting a specific preset detail."""
    # First get list to find a valid ID
    response = client.get("/api/v1/presets")
    presets = response.json()["presets"]
    if not presets:
        return

    preset_id = presets[0]["id"]
    response = client.get(f"/api/v1/presets/{preset_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == preset_id
    assert "template" in data

def test_get_preset_topics(client: TestClient):
    """Test getting sample topics for a preset."""
    # First get list to find a valid ID
    response = client.get("/api/v1/presets")
    presets = response.json()["presets"]
    if not presets:
        return

    preset_id = presets[0]["id"]
    response = client.get(f"/api/v1/presets/{preset_id}/topics")
    assert response.status_code == 200
    data = response.json()
    assert "topics" in data
    assert isinstance(data["topics"], list)
