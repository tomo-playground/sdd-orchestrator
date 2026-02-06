from conftest import create_test_storyboard
from fastapi.testclient import TestClient

from models.media_asset import MediaAsset


def test_candidates_persistence(client: TestClient, db_session):
    """
    Regression test for verifying that image candidates are correctly persisted and retrieved.
    Steps:
    1. Create MediaAssets for candidates.
    2. Create a storyboard with a scene containing 'candidates' data (media_asset_id based).
    3. Save the storyboard via API.
    4. Retrieve the storyboard via API.
    5. Assert that 'candidates' field in the response contains the correct data with URLs.
    """

    # 1. Create MediaAssets first
    assets = []
    for i in range(3):
        asset = MediaAsset(
            file_type="candidate",
            storage_key=f"candidates/test_candidate_{i}.png",
            file_name=f"test_candidate_{i}.png",
            mime_type="image/png",
        )
        db_session.add(asset)
        assets.append(asset)
    db_session.flush()

    # 2. Prepare candidate data with media_asset_id
    candidates_data = [
        {"media_asset_id": assets[0].id, "match_rate": 0.95},
        {"media_asset_id": assets[1].id, "match_rate": 0.88},
        {"media_asset_id": assets[2].id, "match_rate": 0.82},
    ]

    scenes = [
        {
            "scene_id": 0,
            "script": "A test scene",
            "speaker": "Narrator",
            "duration": 5.0,
            "image_prompt": "A beautiful landscape",
            "candidates": candidates_data,
        }
    ]

    # 3. Create Storyboard
    data = create_test_storyboard(client, title="Candidates Test", scenes=scenes)
    storyboard_id = data["storyboard_id"]
    assert storyboard_id is not None

    # 4. Retrieve Storyboard
    get_response = client.get(f"/storyboards/{storyboard_id}")
    assert get_response.status_code == 200
    get_data = get_response.json()

    # 5. Verify Candidates Persistence
    scenes = get_data["scenes"]
    assert len(scenes) == 1
    retrieved_candidates = scenes[0]["candidates"]

    assert retrieved_candidates is not None, "candidates field should not be None"
    assert len(retrieved_candidates) == 3

    # Check that media_asset_id and match_rate are preserved
    for i, rc in enumerate(retrieved_candidates):
        assert rc["media_asset_id"] == assets[i].id
        assert rc["match_rate"] == candidates_data[i]["match_rate"]
        # image_url should be populated by serialize_scene
        assert rc["image_url"] is not None
        assert f"test_candidate_{i}.png" in rc["image_url"]
