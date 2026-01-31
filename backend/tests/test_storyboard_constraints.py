
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_storyboard_long_title_no_error():
    """
    Test that a storyboard title longer than 200 characters does NOT raise 500 error.
    Success (200 OK) implies truncation worked and DB insert succeeded.
    """
    long_title = "A" * 250
    payload = {
        "title": long_title,
        "description": "Test description",
        "default_character_id": None,
        "default_style_profile_id": None,
        "scenes": []
    }
    
    response = client.post("/storyboards", json=payload)
    if response.status_code != 200:
        print(f"Error Response: {response.text}")
        
    assert response.status_code == 200
    data = response.json()
    assert "storyboard_id" in data


def test_create_storyboard_update_long_title_no_error():
    """
    Test that updating text with long title returns 200 OK (no DB error).
    """
    # 1. Create
    payload = {
        "title": "Initial Title",
        "description": "Initial Desc",
        "scenes": []
    }
    create_res = client.post("/storyboards", json=payload)
    assert create_res.status_code == 200
    sb_id = create_res.json()["storyboard_id"]
    
    # 2. Update
    long_title = "B" * 300
    update_payload = {
        "title": long_title,
        "description": "Updated Desc",
        "default_character_id": None,
        "default_style_profile_id": None,
        "scenes": []
    }
    
    update_res = client.put(f"/storyboards/{sb_id}", json=update_payload)
    assert update_res.status_code == 200


def test_scene_boolean_type_casting_no_error():
    """
    Test that passing boolean for integer fields returns 200 OK.
    This implies the type mismatch error is resolved by casting.
    """
    payload = {
        "title": "Boolean Test Storyboard",
        "description": "Testing boolean casting",
        "scenes": [
            {
                "scene_id": 1,
                "script": "Scene 1",
                "use_reference_only": True,  # Passing Boolean
                "reference_only_weight": 0.8
            },
            {
                "scene_id": 2,
                "script": "Scene 2",
                "use_reference_only": False, # Passing Boolean
                "reference_only_weight": 0.2
            }
        ]
    }
    
    response = client.post("/storyboards", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "storyboard_id" in data
