import os
import re
import sys
from collections import Counter

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add current directory to path
sys.path.append(os.getcwd())

from config import DATABASE_URL
from models.activity_log import ActivityLog
from models.scene import Scene
from services.controlnet import detect_pose_from_prompt


def deep_analyze_poses():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # 1. Fetch all prompts
    prompts = [r[0] for r in db.query(Scene.image_prompt).all() if r[0]]
    prompts += [r[0] for r in db.query(ActivityLog.prompt).all() if r[0]]

    # 2. Extract tags and clean them
    all_tags = []
    for p in prompts:
        # Split by comma
        tags = p.split(",")
        for t in tags:
            # Clean weights like (tag:1.2)
            clean = re.sub(r'\(+', '', t)
            clean = re.sub(r'\)+', '', clean)
            clean = clean.split(":")[0].strip().lower()
            if clean:
                all_tags.append(clean)

    tag_counts = Counter(all_tags)

    # 3. Filter for action/body related keywords
    body_keywords = [
        "pose", "standing", "sitting", "lying", "laying", "kneeling", "crouching",
        "leaning", "running", "walking", "jumping", "dancing", "sleeping",
        "arm", "hand", "leg", "foot", "looking", "facing", "view",
        "pointing", "reaching", "holding", "shouting", "crying", "laughing",
        "from behind", "profile", "side view", "portrait"
    ]

    print("\n[Deep Data Analysis: Most Frequent Action/Pose Tags]")
    print(f"{'Tag':35} | {'Count':6} | {'Status'}")
    print("-" * 60)

    candidates = []
    for tag, count in tag_counts.most_common(1000):
        if any(kw in tag for kw in body_keywords):
            is_supported = detect_pose_from_prompt(tag) is not None
            candidates.append((tag, count, is_supported))

    # Show top 40 candidates
    for tag, count, supported in candidates[:40]:
        status = "✅ Supported" if supported else "❌ MISSING (Target!)"
        print(f"{tag:35} | {count:6} | {status}")

    db.close()

if __name__ == "__main__":
    deep_analyze_poses()
