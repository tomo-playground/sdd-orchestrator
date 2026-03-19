"""Test applying conflict rules via API."""

import json

import requests

API_BASE = "http://localhost:8000"

# Apply selected rules
rules_to_apply = {"rules": [{"tag1": "indoors", "tag2": "outdoors"}, {"tag1": "day", "tag2": "night"}]}

print("Applying conflict rules...")
print(json.dumps(rules_to_apply, indent=2))
print()

response = requests.post(f"{API_BASE}/generation-logs/apply-conflict-rules", json=rules_to_apply)

if response.status_code == 200:
    result = response.json()
    print("✅ Success!")
    print(json.dumps(result, indent=2))
else:
    print(f"❌ Error {response.status_code}")
    print(response.text)
