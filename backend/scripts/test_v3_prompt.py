import base64
import json
import urllib.error
import urllib.request

API_URL = "http://localhost:8000/scene/generate"

# The V3-assembled prompt (Layer 0 -> 11)
# Character: Hana (Blue eyes, long hair, mole, white dress)
# Scene: Cafe, Rain, Sad, Drinking Coffee
PROMPT = (
    "masterpiece, best_quality, "  # L0
    "1girl, solo, "  # L1
    "long_hair, blue_eyes, mole_under_eye, "  # L2 (Identity)
    "slim_body, "  # L3
    "white_dress, puffy_sleeves, "  # L4 (Clothing)
    "red_ribbon, "  # L6 (Acc)
    "sad, melancholic_expression, "  # L7 (Exp)
    "sitting, drinking_coffee, looking_out_window, "  # L8 (Action)
    "upper_body, side_view, "  # L9 (Camera)
    "cafe, window, "  # L10 (Env)
    "rainy_day, rain_on_glass, gloomy_lighting, cinematic"  # L11 (Atm)
)

NEGATIVE_PROMPT = "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry"

payload = {
    "prompt": PROMPT,
    "negative_prompt": NEGATIVE_PROMPT,
    "width": 512,
    "height": 768,
    "steps": 20,
    "cfg_scale": 7.0,
    "sampler_name": "DPM++ 2M Karras",
    "seed": -1,
}

print(f"🚀 Sending V3 Prompt to Backend...\nPrompt: {PROMPT}\n")

try:
    data_json = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data_json, headers={"Content-Type": "application/json"})

    with urllib.request.urlopen(req, timeout=60) as response:
        response_body = response.read()
        data = json.loads(response_body)

    # Check response structure
    print("✅ Response received!")

    image_b64 = None
    if "image_b64" in data:
        image_b64 = data["image_b64"]
    elif "image" in data:  # Backend seems to use 'image' key
        image_b64 = data["image"]
    elif "images" in data and len(data["images"]) > 0:
        # Some SD backends return list of images
        image_b64 = data["images"][0]

    if image_b64:
        # Save image
        if "," in image_b64:
            image_b64 = image_b64.split(",")[1]

        with open("v3_test_result.png", "wb") as f:
            f.write(base64.b64decode(image_b64))
        print("🎉 Image saved to: v3_test_result.png")
    else:
        print("⚠️ No image data found in response:", data.keys())

except Exception as e:
    print(f"❌ Error: {e}")
