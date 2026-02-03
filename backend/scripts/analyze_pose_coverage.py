import os
import sys
from collections import Counter

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add current directory to path
sys.path.append(os.getcwd())

from config import DATABASE_URL
from models.activity_log import ActivityLog
from models.associations import CharacterTag
from models.scene import Scene
from models.tag import Tag
from services.controlnet import detect_pose_from_prompt


def analyze_pose_coverage():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # 1. Get all tags from Character links
    char_tags = []
    tags = db.query(Tag).join(CharacterTag).all()
    char_tags.extend([t.name.lower() for t in tags])

    # 2. Get all tags from Scenes
    scene_tags = []
    scenes = db.query(Scene).all()
    for s in scenes:
        if s.image_prompt:
            scene_tags.extend([t.strip().lower() for t in s.image_prompt.split(",")])

    # 3. Get all tags from ActivityLogs
    log_tags = []
    logs = db.query(ActivityLog).all()
    for log_entry in logs:
        if log_entry.tags_used:
            log_tags.extend([t.lower() for t in log_entry.tags_used])
        if log_entry.prompt:
            log_tags.extend([t.strip().lower() for t in log_entry.prompt.split(",")])

    all_found_tags = Counter(char_tags + scene_tags + log_tags)

    # 4. Known pose keywords from controlnet.py
    pose_keywords = [
        "standing", "sitting", "lying", "kneeling", "bending",
        "pointing", "reaching", "holding", "carrying", "looking",
        "dancing", "fighting", "sleeping", "reading", "typing",
        "eating", "drinking", "shouting", "crying", "laughing",
        "hug", "kiss", "handshake", "kick", "punch",
        "crawling", "squatting", "stretching", "yoga", "swimming",
        "leaning", "looking back", "profile", "from behind",
        "laying", "squat", "bent over", "on knees"
    ]

    print("\n[DB Pose Tag Analysis]")
    print(f"Total Unique Tags Found: {len(all_found_tags)}")

    print("\n--- Common Potential Pose Tags Found in DB ---")
    potential_poses = []
    for tag, count in all_found_tags.most_common(500):
        # Heuristic to find pose-like tags
        if any(pk in tag for pk in pose_keywords) or "pose" in tag:
            is_supported = detect_pose_from_prompt([tag]) is not None
            potential_poses.append((tag, count, is_supported))

    for tag, count, supported in sorted(potential_poses, key=lambda x: x[1], reverse=True)[:50]:
        status = "✅ Supported" if supported else "❌ MISSING"
        print(f"{tag:35} | Count: {count:4} | {status}")

    db.close()

if __name__ == "__main__":
    analyze_pose_coverage()
