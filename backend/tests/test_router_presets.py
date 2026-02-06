"""Tests for presets router endpoints."""

from fastapi.testclient import TestClient


class TestPresetsRouter:
    """Test preset listing and detail endpoints."""

    def test_list_presets(self, client: TestClient, db_session):
        """GET /presets returns all available presets."""
        response = client.get("/presets")
        assert response.status_code == 200
        data = response.json()

        assert "presets" in data
        presets = data["presets"]
        assert isinstance(presets, list)
        assert len(presets) > 0

        # Check structure of first preset
        first = presets[0]
        assert "id" in first
        assert "name" in first
        assert "name_ko" in first
        assert "description" in first
        assert "structure" in first
        assert "sample_topics" in first
        assert "default_duration" in first
        assert "default_style" in first
        assert "default_language" in first

    def test_list_presets_contains_known_ids(self, client: TestClient, db_session):
        """Preset list includes known preset IDs."""
        response = client.get("/presets")
        data = response.json()
        ids = [p["id"] for p in data["presets"]]

        assert "monologue" in ids
        assert "dialogue" in ids
        assert "narrated_dialogue" in ids
        assert len(ids) == 3  # Monologue + Dialogue + Narrated Dialogue

    def test_get_preset_detail_monologue(self, client: TestClient, db_session):
        """GET /presets/monologue returns monologue preset details."""
        response = client.get("/presets/monologue")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "monologue"
        assert data["name"] == "Monologue"
        assert data["name_ko"] == "독백"
        assert data["structure"] == "Monologue"
        assert "template" in data
        assert "sample_topics" in data
        assert isinstance(data["sample_topics"], list)
        assert len(data["sample_topics"]) > 0
        assert data["default_duration"] == 30

    def test_get_preset_detail_dialogue(self, client: TestClient, db_session):
        """GET /presets/dialogue returns dialogue preset."""
        response = client.get("/presets/dialogue")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "dialogue"
        assert data["name"] == "Dialogue"
        assert data["structure"] == "Dialogue"
        assert data["default_duration"] == 30

    def test_get_preset_not_found(self, client: TestClient, db_session):
        """GET /presets/{invalid_id} returns 404."""
        response = client.get("/presets/nonexistent_preset")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_preset_topics_monologue(self, client: TestClient, db_session):
        """GET /presets/monologue/topics returns sample topics."""
        response = client.get("/presets/monologue/topics")
        assert response.status_code == 200
        data = response.json()

        assert "topics" in data
        topics = data["topics"]
        assert isinstance(topics, list)
        assert len(topics) == 5

    def test_get_preset_topics_not_found(self, client: TestClient, db_session):
        """GET /presets/{invalid}/topics returns 404."""
        response = client.get("/presets/nonexistent_preset/topics")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_all_presets_have_sample_topics(self, client: TestClient, db_session):
        """Every preset has at least one sample topic."""
        response = client.get("/presets")
        presets = response.json()["presets"]

        for preset in presets:
            assert len(preset["sample_topics"]) > 0, (
                f"Preset '{preset['id']}' has no sample topics"
            )

    def test_preset_detail_has_extra_fields(self, client: TestClient, db_session):
        """Preset detail includes extra_fields key."""
        response = client.get("/presets/monologue")
        data = response.json()

        assert "extra_fields" in data

    def test_all_presets_have_default_style(self, client: TestClient, db_session):
        """Every preset has a default_style set."""
        response = client.get("/presets")
        presets = response.json()["presets"]

        for preset in presets:
            assert preset["default_style"], (
                f"Preset '{preset['id']}' missing default_style"
            )
