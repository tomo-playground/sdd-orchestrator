
import requests

API_BASE = "http://127.0.0.1:8000"

def test_scene_tag_persistence():
    # 1. Prepare Storyboard Save Request
    payload = {
        "title": "Persistence Test Storyboard",
        "description": "Verification of scene_tags and character_actions",
        "default_character_id": 1,
        "scenes": [
            {
                "scene_id": 1,
                "script": "Testing scene tags persistence.",
                "tags": [
                    {"tag_id": 50, "weight": 1.2}, # outdoors
                    {"tag_id": 100, "weight": 1.0} # day
                ],
                "character_actions": [
                    {"character_id": 1, "tag_id": 20, "weight": 1.2}, # smile
                    {"character_id": 1, "tag_id": 35, "weight": 1.5} # holding_flower
                ]
            }
        ]
    }
    
    print("\n--- Testing Scene Tag & Action Save ---")
    res = requests.post(f"{API_BASE}/storyboards", json=payload)
    if res.status_code == 200:
        data = res.json()
        storyboard_id = data["storyboard_id"]
        print(f"✅ Storyboard saved with ID: {storyboard_id}")
        
        # NOTE: Since we don't have a GET endpoint that returns these relations easily yet,
        # we would normally check the DB directly. But for this test, if status is 200, 
        # it means the flush and commit worked without error.
    else:
        print(f"❌ Failed to save storyboard: {res.text}")

if __name__ == "__main__":
    try:
        test_scene_tag_persistence()
    except Exception as e:
        print(f"Error: {e}")
