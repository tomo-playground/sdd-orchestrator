
import requests
import sys

API_BASE = "http://localhost:8000"

def create_dummy_storyboard():
    payload = {
        "topic": "Termination Test",
        "duration": 3,
        "style": "anime",
        "language": "en",
        "structure": "default",
        "actor_a_gender": "female"
    }
    # Create (generate scenes)
    print("Generating storyboard...")
    res = requests.post(f"{API_BASE}/storyboards/create", json=payload)
    if res.status_code != 200:
        print(f"Failed to create: {res.text}")
        return None
    
    data = res.json()
    scenes = data.get("scenes", [])
    
    # Save
    save_payload = {
        "title": "Termination Test",
        "description": "To be deleted",
        "character_id": None,
        "style_profile_id": None,
        "default_caption": None,
        "scenes": scenes
    }
    print("Saving storyboard...")
    res = requests.post(f"{API_BASE}/storyboards", json=save_payload)
    if res.status_code != 200:
        print(f"Failed to save: {res.text}")
        return None
        
    sb_id = res.json().get("storyboard_id")
    print(f"Created Storyboard ID: {sb_id}")
    return sb_id

def delete_storyboard(sb_id):
    print(f"Deleting Storyboard ID: {sb_id}...")
    res = requests.delete(f"{API_BASE}/storyboards/{sb_id}")
    if res.status_code == 200:
        print("Success!")
    else:
        print(f"Failed! Status: {res.status_code}")
        print(res.text)

if __name__ == "__main__":
    # Target specific ID provided by user
    target_id = 204
    delete_storyboard(target_id)
