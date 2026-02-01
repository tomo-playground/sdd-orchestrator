
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_prompt_compose_repro():
    """
    Reproduce the 500 error in /prompt/compose
    """
    payload = {
        "mode": "standard",
        "tokens": ["1girl", "smile", "sitting", "indoors"],
        "character_id": 1,
        "loras": []
    }
    
    print("\n[Test] Sending request to /prompt/compose...")
    response = client.post("/prompt/compose", json=payload)
    
    if response.status_code != 200:
        print(f"\n[Test] Error Response ({response.status_code}):")
        print(response.text)
        
    assert response.status_code == 200
    data = response.json()
    assert "prompt" in data
    assert "effective_mode" in data
    print("\n[Test] Success:", data)
