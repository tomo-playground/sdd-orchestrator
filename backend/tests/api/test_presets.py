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


def test_presets_contain_emotion_presets(client: TestClient):
    """SP-074: /presets 응답에 emotion_presets 필드가 포함된다."""
    response = client.get("/api/v1/presets")
    data = response.json()
    assert "emotion_presets" in data
    assert isinstance(data["emotion_presets"], list)
    assert len(data["emotion_presets"]) > 0
    ep = data["emotion_presets"][0]
    assert "id" in ep
    assert "label" in ep
    assert "emotion" in ep


def test_presets_contain_bgm_mood_presets(client: TestClient):
    """SP-074: /presets 응답에 bgm_mood_presets 필드가 포함된다."""
    response = client.get("/api/v1/presets")
    data = response.json()
    assert "bgm_mood_presets" in data
    assert isinstance(data["bgm_mood_presets"], list)
    assert len(data["bgm_mood_presets"]) > 0
    bp = data["bgm_mood_presets"][0]
    assert "id" in bp
    assert "label" in bp
    assert "mood" in bp
    assert "prompt" in bp


def test_presets_contain_ip_adapter_models(client: TestClient):
    """SP-074: /presets 응답에 ip_adapter_models 필드가 포함된다."""
    from config import IP_ADAPTER_MODEL_OPTIONS

    response = client.get("/api/v1/presets")
    data = response.json()
    assert "ip_adapter_models" in data
    assert isinstance(data["ip_adapter_models"], list)
    assert len(data["ip_adapter_models"]) > 0
    assert data["ip_adapter_models"] == IP_ADAPTER_MODEL_OPTIONS


def test_presets_contain_overlay_styles(client: TestClient):
    """SP-074: /presets 응답에 overlay_styles 필드가 포함된다."""
    response = client.get("/api/v1/presets")
    data = response.json()
    assert "overlay_styles" in data
    assert isinstance(data["overlay_styles"], list)
    assert len(data["overlay_styles"]) > 0
    os_item = data["overlay_styles"][0]
    assert "id" in os_item
    assert "label" in os_item


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
