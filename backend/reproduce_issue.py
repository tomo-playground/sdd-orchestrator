
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reproduce")

API_URL = "http://localhost:8000/prompt/compose"

payload = {
  "tokens": [
    "best_quality",
    "masterpiece",
    "1girl",
    "pink_hair",
    "looking_at_viewer",
    "upper_body",
    "kitchen",
    "day",
    "bright",
    "anime_style",
    "casual_outfit",
    "blush",
    "standing",
    "cooking",
    "solo",
    "open_mouth"
  ],
  "mode": "auto",
  "loras": [
    {
      "name": "harukaze-doremi-casual",
      "weight": 0.61,
      "trigger_words": ["by Harukaze Unipo"],
      "lora_type": "style"
    }
  ],
  "use_break": True
}

try:
    logger.info("Sending request to %s...", API_URL)
    response = requests.post(API_URL, json=payload)
    response.raise_for_status()
    
    data = response.json()
    print("--- Response ---")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    prompt = data.get("prompt", "")
    weights = data.get("lora_weights")
    
    if "<lora:harukaze-doremi-casual:0.61>" in prompt:
         print("\n✅ SUCCESS: LoRA tag found in composed prompt.")
    else:
         print("\n❌ FAILURE: LoRA tag MISSING in composed prompt.")

    meta = data.get("meta")
    if meta and meta.get("token_count") > 0:
        print(f"\n✅ SUCCESS: Meta data found. Token Count: {meta['token_count']}, Has Break: {meta['has_break']}")
    else:
        print(f"\n❌ FAILURE: Meta data MISSING or incorrect. Got: {meta}")

    if weights and weights.get("harukaze-doremi-casual") == 0.61:
         print("\n✅ SUCCESS: LoRA weights metadata found.")
    else:
         print(f"\n❌ FAILURE: LoRA weights metadata MISSING or incorrect. Got: {weights}")
         
except Exception as e:
    logger.error("Request failed: %s", e)
    if hasattr(e, 'response') and e.response:
        print("Response Text:", e.response.text)
