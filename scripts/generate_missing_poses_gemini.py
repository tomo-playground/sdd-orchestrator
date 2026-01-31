import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from services.gemini_imagen import generate_pose_image_via_gemini
from config import logger

def main():
    missing_poses = {
        "pointing forward": "pointing_forward.png",
        "covering face": "covering_face.png"
    }
    
    output_dir = Path("backend/assets/poses")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for pose_desc, filename in missing_poses.items():
        print(f"Generating pose: {pose_desc} using imagen-4.0-generate-001...")
        # Direct generation call
        from google.genai import types
        from config import gemini_client
        
        try:
            response = gemini_client.models.generate_images(
                model="imagen-4.0-generate-001",
                prompt=(
                    f"Full body sketch of a person doing a {pose_desc}, "
                    "minimalist line art, white background, high contrast, "
                    "clean lines, no shading, stick figure style, "
                    "anatomically correct, wide shot, full body visible"
                ),
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="3:4"
                )
            )
            if response.generated_images:
                image_bytes = response.generated_images[0].image.image_bytes
                output_path = output_dir / filename
                with open(output_path, "wb") as f:
                    f.write(image_bytes)
                print(f"✅ Successfully generated and saved to {output_path}")
            else:
                print(f"❌ No images returned for {pose_desc}")
        except Exception as e:
            print(f"❌ Failed to generate {pose_desc}: {e}")

if __name__ == "__main__":
    main()
