
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from main import app  # Assuming main.py exports 'app'

def test_candidates_persistence(client: TestClient, db_session: Session):
    """
    Regression test for verifying that image candidates are correctly persisted and retrieved.
    Steps:
    1. Create a storyboard with a scene containing 'candidates' data.
    2. Save the storyboard via API.
    3. Retrieve the storyboard via API.
    4. Assert that 'candidates' field in the response matches the input.
    """
    
    # 1. Prepare Mock Data
    candidates_data = [
        {"image_url": "http://example.com/img1.png", "match_rate": 0.95},
        {"image_url": "http://example.com/img2.png", "match_rate": 0.88},
        {"image_url": "http://example.com/img3.png", "match_rate": 0.82},
    ]

    storyboard_payload = {
        "title": "Candidates Test Storyboard",
        "description": "Testing persistence of candidates field",
        "scenes": [
            {
                "scene_id": 0,
                "script": "A test scene",
                "speaker": "Narrator",
                "duration": 5.0,
                "image_prompt": "A beautiful landscape",
                "candidates": candidates_data
            }
        ]
    }

    # 2. Create Storyboard
    response = client.post("/storyboards", json=storyboard_payload)
    assert response.status_code == 200, f"Failed to create storyboard: {response.text}"
    data = response.json()
    storyboard_id = data["storyboard_id"]
    assert storyboard_id is not None

    # 3. Retrieve Storyboard
    get_response = client.get(f"/storyboards/{storyboard_id}")
    assert get_response.status_code == 200
    get_data = get_response.json()

    # 4. Verify Candidates Persistence
    scenes = get_data["scenes"]
    assert len(scenes) == 1
    retrieved_candidates = scenes[0]["candidates"]
    
    assert retrieved_candidates is not None, "candidates field should not be None"
    assert len(retrieved_candidates) == 3
    
    # Check content matches (ignoring order if needed, but list usually preserves order)
    # The JSONB field might return data slightly differently if not careful, but exact match expectation is fine here.
    assert retrieved_candidates == candidates_data
