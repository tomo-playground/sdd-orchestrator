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
from models.tag import Tag
from services.controlnet import detect_pose_from_prompt


def final_audit():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # 1. Fetch all prompts
    prompts = [r[0] for r in db.query(Scene.image_prompt).all() if r[0]]
    prompts += [r[0] for r in db.query(ActivityLog.prompt).all() if r[0]]

    all_tags = []
    for p in prompts:
        tags = p.split(",")
        for t in tags:
            clean = re.sub(r'[\(\)\[\]]', '', t).split(":")[0].strip().lower()
            if clean:
                all_tags.append(clean)

    tag_counts = Counter(all_tags)

    print("\n[Audit: Pose Coverage Check]")
    print(f"{'Tag':35} | {'Count':6} | {'Status'}")
    print("-" * 60)

    missing_targets = []
    for tag, count in tag_counts.most_common(100):
        is_supported = detect_pose_from_prompt([tag]) is not None
        # Heuristic for action/pose tags
        if any(kw in tag for kw in ["standing", "sitting", "lying", "kneeling", "crouching", "running", "walking", "jumping", "pose", "action", "looking", "facing", "view"]):
            status = "✅ Supported" if is_supported else "❌ MISSING"
            print(f"{tag:35} | {count:6} | {status}")
            if not is_supported and count >= 1:
                missing_targets.append((tag, count))

    # 2. Check Tag Category anomalies
    print("\n[Audit: Category Checks]")
    scene_tags_posing = db.query(Tag.name).filter(
        Tag.category == "scene",
        Tag.name.ilike("%standing%") | Tag.name.ilike("%sitting%") | Tag.name.ilike("%pose%")
    ).all()
    print(f"Tags in 'scene' that look like 'pose': {len(scene_tags_posing)}")
    for t in scene_tags_posing[:10]:
        print(f" - {t[0]}")

    db.close()

if __name__ == "__main__":
    final_audit()
