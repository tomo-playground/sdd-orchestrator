import os
import sys
from collections import Counter

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add current directory to path
sys.path.append(os.getcwd())

from config import DATABASE_URL
from models.activity_log import ActivityLog
from models.tag import Tag
from services.controlnet import detect_pose_from_prompt


def analyze_db_assets():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # 1. Analyze Tag Categories
    print("\n[Tag Category Distribution]")
    tags = db.query(Tag.category).all()
    cat_counts = Counter([t[0] for t in tags])
    for cat, count in cat_counts.most_common():
        print(f"Category: {str(cat):20} | Count: {count}")

    # 2. Extract potential pose tags
    print("\n[Sampling Pose Tags from DB]")
    # Get tags classified as 'pose' or 'action' or 'motion'
    pose_related_tags = db.query(Tag.name).filter(Tag.category.in_(['pose', 'action', 'motion', 'character_action'])).all()
    print(f"Total tags in pose segments: {len(pose_related_tags)}")

    # Check top tags in prompts
    log_prompts = db.query(ActivityLog.prompt).limit(500).all()
    all_tokens = []
    for p in log_prompts:
        if p[0]:
            all_tokens.extend([t.strip().lower() for t in p[0].split(",")])

    token_counts = Counter(all_tokens)

    pose_keywords = ["standing", "sitting", "leaning", "lying", "kneeling", "arms", "hands", "looking", "facing", "pose", "action", "walking", "running"]

    print(f"\n{'Tag (Top Prompts)':30} | {'Count':6} | {'Status'}")
    print("-" * 50)
    for tag, count in token_counts.most_common(200):
        if any(k in tag for k in pose_keywords):
            is_supported = detect_pose_from_prompt([tag]) is not None
            status = "✅ Supported" if is_supported else "❌ MISSING"
            print(f"{tag:30} | {count:6} | {status}")

    db.close()

if __name__ == "__main__":
    analyze_db_assets()
