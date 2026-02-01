"""Generate missing pose images using Gemini Imagen.

Usage:
    python scripts/generate_missing_poses_gemini.py [--all] [--poses eating,cooking]
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from config import gemini_client, logger
from google.genai import types

# All pose definitions: description -> filename
ALL_POSES = {
    # Standing poses
    "standing neutral": "standing_neutral.png",
    "standing and waving": "standing_waving.png",
    "standing with arms up": "standing_arms_up.png",
    "standing with arms crossed": "standing_arms_crossed.png",
    "standing with hands on hips": "standing_hands_on_hips.png",
    "standing looking at the viewer": "looking_at_viewer_neutral.png",
    "standing seen from behind": "standing_from_behind.png",
    # Sitting poses
    "sitting on a chair": "sitting_neutral.png",
    "sitting with chin resting on hand": "sitting_chin_rest.png",
    "sitting and leaning forward": "sitting_leaning.png",
    # Action poses
    "walking forward": "walking.png",
    "running dynamically": "running.png",
    "jumping in mid-air": "jumping.png",
    "lying on the ground": "lying_neutral.png",
    "kneeling on the ground": "kneeling_neutral.png",
    "crouching low": "crouching_neutral.png",
    "pointing forward with one arm": "pointing_forward.png",
    "covering face with both hands": "covering_face.png",
    # New daily life / interaction poses
    "standing and holding an object in one hand": "holding_object.png",
    "eating with chopsticks, hand near mouth": "eating.png",
    "standing and cooking, both hands forward": "cooking.png",
    "standing and holding an umbrella with one arm raised": "holding_umbrella.png",
    "sitting at a desk and writing with one hand": "writing.png",
    "standing in profile view, seen from the side": "profile_standing.png",
    "standing and looking up at the sky": "standing_looking_up.png",
    "leaning against a wall with arms crossed": "leaning_wall.png",
    "sitting at a table and eating with chopsticks": "sitting_eating.png",
}

OUTPUT_DIR = Path("backend/assets/poses")


def generate_pose(pose_desc: str, filename: str) -> bool:
    """Generate a single pose image via Gemini Imagen."""
    output_path = OUTPUT_DIR / filename

    try:
        response = gemini_client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=(
                f"Full body sketch of a single person {pose_desc}, "
                "minimalist line art, white background, high contrast, "
                "clean lines, no shading, stick figure style, "
                "anatomically correct, wide shot, full body visible"
            ),
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="3:4",
            ),
        )
        if response.generated_images:
            image_bytes = response.generated_images[0].image.image_bytes
            output_path.write_bytes(image_bytes)
            print(f"  Saved: {output_path} ({len(image_bytes)} bytes)")
            return True
        else:
            print(f"  No images returned")
            return False
    except Exception as e:
        print(f"  Failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate pose images via Gemini Imagen")
    parser.add_argument("--all", action="store_true", help="Regenerate all 27 poses")
    parser.add_argument("--poses", type=str, default=None,
                        help="Comma-separated filenames (e.g. eating.png,cooking.png)")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not gemini_client:
        print("GEMINI_API_KEY not set. Exiting.")
        sys.exit(1)

    # Determine which poses to generate
    if args.poses:
        selected = set(args.poses.split(","))
        poses = {d: f for d, f in ALL_POSES.items() if f in selected}
    elif args.all:
        poses = ALL_POSES
    else:
        # Default: only missing files
        poses = {d: f for d, f in ALL_POSES.items() if not (OUTPUT_DIR / f).exists()}

    if not poses:
        print("All pose files already exist. Use --all to regenerate.")
        return

    print(f"Generating {len(poses)} pose(s) via Gemini Imagen...\n")

    success = 0
    fail = 0
    batch_count = 0
    RATE_LIMIT_BATCH = 9  # Imagen 4.0: 10 requests/min
    RATE_LIMIT_WAIT = 65  # seconds to wait between batches

    for desc, filename in poses.items():
        # Rate limit: pause every 9 requests
        if batch_count > 0 and batch_count % RATE_LIMIT_BATCH == 0:
            print(f"\n  Rate limit pause ({RATE_LIMIT_WAIT}s)...\n")
            time.sleep(RATE_LIMIT_WAIT)

        print(f"[{success + fail + 1}/{len(poses)}] {filename} ({desc})")
        if generate_pose(desc, filename):
            success += 1
        else:
            fail += 1
        batch_count += 1

    print(f"\nDone: {success} succeeded, {fail} failed")
    if fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
