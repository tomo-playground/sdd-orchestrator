"""
Tests for SceneCandidate schema and media_asset_id based candidates format.

Covers:
1. SceneCandidate Pydantic schema validation
2. serialize_scene includes candidate URLs from asset_url_map
3. Save/retrieve scenes with media_asset_id based candidates
"""

import pytest
from conftest import create_test_storyboard
from fastapi.testclient import TestClient

from models.media_asset import MediaAsset
from models.scene import Scene
from schemas import SceneCandidate, StoryboardScene
from services.storyboard import serialize_scene


class TestSceneCandidateSchema:
    """Test SceneCandidate Pydantic model validation."""

    def test_scene_candidate_with_all_fields(self):
        """SceneCandidate should accept media_asset_id, match_rate, and image_url."""
        candidate = SceneCandidate(
            media_asset_id=123,
            match_rate=0.95,
            image_url="http://example.com/img.png",
        )
        assert candidate.media_asset_id == 123
        assert candidate.match_rate == 0.95
        assert candidate.image_url == "http://example.com/img.png"

    def test_scene_candidate_minimal(self):
        """SceneCandidate should work with only media_asset_id."""
        candidate = SceneCandidate(media_asset_id=456)
        assert candidate.media_asset_id == 456
        assert candidate.match_rate is None
        assert candidate.image_url is None

    def test_scene_candidate_requires_media_asset_id(self):
        """SceneCandidate should reject missing media_asset_id."""
        with pytest.raises(ValueError):
            SceneCandidate(match_rate=0.9)

    def test_storyboard_scene_with_candidates(self):
        """StoryboardScene should accept list of SceneCandidate."""
        scene = StoryboardScene(
            scene_id=1,
            script="Test scene",
            candidates=[
                SceneCandidate(media_asset_id=1, match_rate=0.95),
                SceneCandidate(media_asset_id=2, match_rate=0.88),
            ],
        )
        assert len(scene.candidates) == 2
        assert scene.candidates[0].media_asset_id == 1
        assert scene.candidates[1].match_rate == 0.88


class TestSerializeSceneWithCandidates:
    """Test serialize_scene enriches candidates with URLs."""

    def test_serialize_scene_without_candidates(self, db_session):
        """serialize_scene should handle scene without candidates."""
        from models.storyboard import Storyboard

        sb = Storyboard(title="Test", group_id=1)
        db_session.add(sb)
        db_session.flush()

        scene = Scene(
            storyboard_id=sb.id,
            order=0,
            script="Test",
            candidates=None,
        )
        db_session.add(scene)
        db_session.flush()

        result = serialize_scene(scene)
        assert result["candidates"] is None

    def test_serialize_scene_enriches_candidates_with_urls(self, db_session):
        """serialize_scene should add image_url from asset_url_map."""
        from models.storyboard import Storyboard

        sb = Storyboard(title="Test", group_id=1)
        db_session.add(sb)
        db_session.flush()

        # Create scene with candidate data (media_asset_id based)
        scene = Scene(
            storyboard_id=sb.id,
            order=0,
            script="Test",
            candidates=[
                {"media_asset_id": 100, "match_rate": 0.95},
                {"media_asset_id": 101, "match_rate": 0.88},
            ],
        )
        db_session.add(scene)
        db_session.flush()

        # Provide asset_url_map
        asset_url_map = {
            100: "http://storage.example.com/img100.png",
            101: "http://storage.example.com/img101.png",
        }

        result = serialize_scene(scene, asset_url_map)

        assert len(result["candidates"]) == 2
        assert result["candidates"][0]["media_asset_id"] == 100
        assert result["candidates"][0]["image_url"] == "http://storage.example.com/img100.png"
        assert result["candidates"][0]["match_rate"] == 0.95

        assert result["candidates"][1]["media_asset_id"] == 101
        assert result["candidates"][1]["image_url"] == "http://storage.example.com/img101.png"

    def test_serialize_scene_handles_missing_asset_in_map(self, db_session):
        """serialize_scene should not fail if asset_id not in map."""
        from models.storyboard import Storyboard

        sb = Storyboard(title="Test", group_id=1)
        db_session.add(sb)
        db_session.flush()

        scene = Scene(
            storyboard_id=sb.id,
            order=0,
            script="Test",
            candidates=[
                {"media_asset_id": 100, "match_rate": 0.95},
                {"media_asset_id": 999, "match_rate": 0.88},  # Not in map
            ],
        )
        db_session.add(scene)
        db_session.flush()

        asset_url_map = {100: "http://storage.example.com/img100.png"}

        result = serialize_scene(scene, asset_url_map)

        # First candidate should have URL
        assert result["candidates"][0]["image_url"] == "http://storage.example.com/img100.png"
        # Second candidate should NOT have image_url key added
        assert "image_url" not in result["candidates"][1] or result["candidates"][1].get("image_url") is None


class TestCandidatesWithMediaAssetIntegration:
    """Integration tests for candidates with MediaAsset."""

    def test_save_and_retrieve_scene_with_media_asset_candidates(self, client: TestClient, db_session):
        """Candidates with media_asset_id should be saved and URLs resolved on retrieval."""
        # 1. Create MediaAssets first
        asset1 = MediaAsset(
            file_type="candidate",
            storage_key="candidates/test_img1.png",
            file_name="test_img1.png",
            mime_type="image/png",
        )
        asset2 = MediaAsset(
            file_type="candidate",
            storage_key="candidates/test_img2.png",
            file_name="test_img2.png",
            mime_type="image/png",
        )
        db_session.add_all([asset1, asset2])
        db_session.flush()

        # 2. Create storyboard with candidates referencing asset IDs
        candidates_data = [
            {"media_asset_id": asset1.id, "match_rate": 0.95},
            {"media_asset_id": asset2.id, "match_rate": 0.88},
        ]

        scenes = [
            {
                "scene_id": 0,
                "script": "Test scene with asset candidates",
                "speaker": "narrator",
                "duration": 5.0,
                "image_prompt": "A test prompt",
                "candidates": candidates_data,
            }
        ]

        data = create_test_storyboard(client, title="Media Asset Candidates Test", scenes=scenes)
        storyboard_id = data["storyboard_id"]

        # 3. Retrieve storyboard
        get_response = client.get(f"/api/v1/storyboards/{storyboard_id}")
        assert get_response.status_code == 200
        get_data = get_response.json()

        # 4. Verify candidates have URLs populated
        retrieved_candidates = get_data["scenes"][0]["candidates"]
        assert len(retrieved_candidates) == 2

        # Check that image_url is populated (not None)
        assert retrieved_candidates[0]["media_asset_id"] == asset1.id
        assert retrieved_candidates[0]["match_rate"] == 0.95
        assert retrieved_candidates[0]["image_url"] is not None
        assert "candidates/test_img1.png" in retrieved_candidates[0]["image_url"]

        assert retrieved_candidates[1]["media_asset_id"] == asset2.id
        assert retrieved_candidates[1]["image_url"] is not None

    def test_candidates_empty_list_persistence(self, client: TestClient):
        """Empty candidates list should be persisted correctly."""
        scenes = [
            {
                "scene_id": 0,
                "script": "Scene without candidates",
                "speaker": "narrator",
                "duration": 5.0,
                "image_prompt": "A test prompt",
                "candidates": [],
            }
        ]

        data = create_test_storyboard(client, title="Empty Candidates Test", scenes=scenes)
        storyboard_id = data["storyboard_id"]

        get_response = client.get(f"/api/v1/storyboards/{storyboard_id}")
        assert get_response.status_code == 200
        get_data = get_response.json()

        # Empty candidates should be preserved (or None)
        retrieved_candidates = get_data["scenes"][0]["candidates"]
        assert retrieved_candidates is None or len(retrieved_candidates) == 0
