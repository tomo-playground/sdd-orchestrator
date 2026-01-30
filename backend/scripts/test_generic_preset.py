import base64
import sys
from pathlib import Path

import requests

# Add backend directory to sys.path
backend_dir = Path("/Users/tomo-mini/Workspace/shorts-producer/backend")
sys.path.insert(0, str(backend_dir))

from database import SessionLocal
from models import Character, Tag


def main():
    db = SessionLocal()
    try:
        print("🔍 Fetching character and settings...")
        char = db.query(Character).filter(Character.name == "Generic Anime Girl").first()
        if not char:
            print("❌ Generic Anime Girl not found!")
            return

        # Get tag names
        [t.name for t in db.query(Tag).filter(Tag.id.in_(char.identity_tags or [])).all()]
        [t.name for t in db.query(Tag).filter(Tag.id.in_(char.clothing_tags or [])).all()]

        # Test Scene
        scene_prompt = "1girl, smiling, holding a coffee cup, sitting in a cozy cafe, soft sunlight, highly detailed"

        # Call the actual compose API to see how it sorts
        # Since we're in a script, we'll mimic the logic or call the local API if running
        api_base = "http://localhost:8000"
        payload = {
            "character_id": char.id,
            "scene_prompt": scene_prompt,
            "use_ip_adapter": True,
            "ip_adapter_reference": char.name,
            "ip_adapter_weight": 0.7,
            "width": 512,
            "height": 512
        }

        print(f"🚀 Requesting generation for scene: '{scene_prompt}'")
        try:
            # We use the internal logic directly if the API is not up,
            # but let's try the API first as it's cleaner.
            resp = requests.post(f"{api_base}/scene/generate", json=payload, timeout=300)
            resp.raise_for_status()
            result = resp.json()

            output_path = "outputs/test_verification_generic.png"
            image_b64 = result['image']

            # Save the result
            with open(backend_dir / output_path, "wb") as f:
                f.write(base64.b64decode(image_b64))

            print(f"✅ Success! Image saved to backend/{output_path}")
            print(f"📝 Final Prompt Used: {result.get('full_prompt')[:100]}...")

        except Exception as e:
            print(f"❌ API Request failed: {e}")
            print("Trying to run internal logic instead...")
            # Fallback to direct logic if API is down
            from logic import generate_scene_image
            from schemas import SceneGenerateRequest

            req = SceneGenerateRequest(**payload)
            res = generate_scene_image(req)

            output_path = "outputs/test_verification_generic_fallback.png"
            with open(backend_dir / output_path, "wb") as f:
                f.write(base64.b64decode(res.image))
            print(f"✅ Success (Fallback)! Image saved to backend/{output_path}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
