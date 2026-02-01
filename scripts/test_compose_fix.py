
import requests

API_BASE = "http://localhost:8000"

def test_prompt_compose():
    payload = {
        "mode": "lora",
        "tokens": ["1girl", "smile", "outdoors"],
        "loras": [
            {
                "id": 1,
                "name": "test_lora",
                "weight": 0.8,
                "trigger_words": ["trigger"],
                "lora_type": "standard",
                "optimal_weight": 0.8
            }
        ],
        "use_break": True
    }
    print("Sending prompt compose request...")
    res = requests.post(f"{API_BASE}/prompt/compose", json=payload)
    if res.status_code == 200:
        print("Success!")
        print(res.json())
    else:
        print(f"Failed! Status: {res.status_code}")
        print(res.text)

if __name__ == "__main__":
    test_prompt_compose()
