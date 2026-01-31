import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add current directory to path
sys.path.append(os.getcwd())

from config import DATABASE_URL
from models.tag import Tag

def reclassify_tags():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Define rules: keyword -> target category
    rules = {
        "pose": ["standing", "sitting", "leaning", "lying", "kneeling", "squatting", "crouching", "pose", "t-pose", "from behind", "profile", "side view"],
        "action": ["running", "walking", "jumping", "dancing", "fighting", "waving", "pointing", "holding", "carrying", "reaching", "shouting", "laughing"],
        "expression": ["smile", "grin", "angry", "sad", "crying", "blush", "surprised", "expression"],
        "camera": ["close-up", "full body", "cowboy shot", "view", "angle", "from above", "from below"]
    }

    print("[Tag Reclassification Start]")
    total_updated = 0
    
    for category, keywords in rules.items():
        for kw in keywords:
            # Case-insensitive match
            tags = db.query(Tag).filter(Tag.name.ilike(f"%{kw}%")).all()
            for tag in tags:
                if tag.category != category:
                    tag.category = category
                    total_updated += 1
    
    db.commit()
    print(f"[Finished] Total tags reclassified: {total_updated}")

    # Re-check distribution using raw SQL for simplicity
    print("\n[New Category Distribution]")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT category, COUNT(*) FROM tags GROUP BY category"))
        for row in result:
            print(f"Category: {str(row[0]):20} | Count: {row[1]}")

    db.close()

if __name__ == "__main__":
    reclassify_tags()
