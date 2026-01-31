import base64
import json
import os
import sys
import urllib.request

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal

API_URL = "http://localhost:8000/scene/generate"

from models.character import Character
from services.prompt.v3_composition import V3PromptBuilder


def generate_with_v3_builder():
    session = SessionLocal()
    try:
        builder = V3PromptBuilder(session)

        # 1. Test Generic Composition
        input_tags = [
            "masterpiece", "best_quality",
            "1girl", "solo",
            "blue_eyes", "long_hair",
            "school_uniform",
            "sitting", "looking_at_viewer",
            "classroom", "sunset"
        ]

        print("📝 Testing Generic V3 Composition...")
        generic_prompt = builder.compose(input_tags)
        print(f"🚀 Generic Prompt: \n{generic_prompt}\n")

        # 2. Test Character-based Composition (if any character exists)
        char = session.query(Character).first()
        if char:
            print(f"👤 Testing Composition for Character: {char.name}")
            char_prompt = builder.compose_for_character(char.id, ["sitting", "classroom", "sunset"])
            print(f"🚀 Character Prompt: \n{char_prompt}\n")

            # Use this for image generation
            final_prompt = char_prompt
        else:
            final_prompt = generic_prompt

        # 3. Generate Image
        payload = {
            "prompt": final_prompt,
            "negative_prompt": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry",
            "width": 512,
            "height": 768,
            "steps": 25,
            "cfg_scale": 7.5,
            "seed": -1
        }

        # ... (rest of the generation logic remains similar)
        print("\n🎨 Sending to SD Engine...")
        data_json = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            API_URL,
            data=data_json,
            headers={'Content-Type': 'application/json'}
        )

        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read())

        image_b64 = data.get("image") or (data.get("images")[0] if "images" in data else None)

        if image_b64:
            if "," in image_b64:
                image_b64 = image_b64.split(",")[1]
            output_file = "v3_db_verification.png"
            with open(output_file, "wb") as f:
                f.write(base64.b64decode(image_b64))
            print(f"✅ Image Generated: {output_file}")
        else:
            print("❌ No image data returned.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    generate_with_v3_builder()
