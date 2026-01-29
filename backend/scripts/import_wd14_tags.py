import csv
import sys
import os

# Add backend directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.dialects.postgresql import insert
from database import SessionLocal
from models.tag import Tag
import re

CSV_PATH = "models/wd14/selected_tags.csv"

# Layer Definitions
LAYER_QUALITY = 0
LAYER_SUBJECT = 1
LAYER_IDENTITY = 2
LAYER_BODY = 3
LAYER_MAIN_CLOTH = 4
LAYER_DETAIL_CLOTH = 5
LAYER_ACCESSORY = 6
LAYER_EXPRESSION = 7
LAYER_ACTION = 8
LAYER_CAMERA = 9
LAYER_ENVIRONMENT = 10
LAYER_ATMOSPHERE = 11

# Scope Definitions
SCOPE_PERMANENT = "PERMANENT"
SCOPE_TRANSIENT = "TRANSIENT"
SCOPE_ANY = "ANY"

def determine_layer_and_scope(name, wd14_category):
    """
    Heuristic to assign Layer and Scope based on tag name and WD14 category.
    WD14 Category 4 = Character Name -> Layer 2
    """
    if wd14_category == 4:
        return LAYER_IDENTITY, SCOPE_PERMANENT

    # Normalize name
    name = name.lower().strip()

    # Rule 1: Explicit Matches (High Priority)
    if name in ["masterpiece", "best_quality", "highres", "absurdres"]:
        return LAYER_QUALITY, SCOPE_ANY
    if name in ["1girl", "1boy", "solo", "multiple_girls", "2girls"]:
        return LAYER_SUBJECT, SCOPE_ANY
    
    # Priority Rule: Style/Atmosphere (Before falling through)
    if name in ["anime", "photorealistic", "realistic", "illustration", "3d", "comic", "sketch"]:
        return LAYER_ATMOSPHERE, SCOPE_TRANSIENT

    # Rule 2: Suffix Matching (Identity/Body)
    if name.endswith("_eyes") or name.endswith("_hair") or name.endswith("_skin") or name.endswith("_ears"):
        return LAYER_IDENTITY, SCOPE_PERMANENT
    if name.endswith("_breasts") or name.endswith("_hips") or name in ["tall", "short", "muscular", "curvy", "slim_body"]:
        return LAYER_BODY, SCOPE_PERMANENT

    # Rule 3: Clothing
    if name.endswith("_uniform") or name.endswith("_dress") or name.endswith("_outfit") or name.endswith("_costume") or name in ["suit", "bikini", "armor"]:
        return LAYER_MAIN_CLOTH, SCOPE_ANY
    if name.endswith("_skirt") or name.endswith("_shirt") or name.endswith("_pants") or name.endswith("_jacket") or name.endswith("_shorts"):
        if name in ["t-shirt", "white_shirt"]: # Common main/detail ambiguity
             return LAYER_DETAIL_CLOTH, SCOPE_ANY
        return LAYER_DETAIL_CLOTH, SCOPE_ANY
    if name.endswith("_footwear") or name.endswith("_shoes") or name.endswith("_boots") or name.endswith("_socks") or name.endswith("_pantyhose"):
        return LAYER_DETAIL_CLOTH, SCOPE_ANY

    # Rule 4: Accessories
    if name.endswith("_gloves") or name.endswith("_ribbon") or name.endswith("_glasses") or name.endswith("_hat") or name.endswith("_cap"):
        return LAYER_ACCESSORY, SCOPE_ANY
    if name in ["jewelry", "necklace", "earrings", "bracelet", "ring", "choker"]:
        return LAYER_ACCESSORY, SCOPE_ANY

    # Rule 5: Expression
    if name in ["smile", "blush", "angry", "sad", "crying", "surprised", "open_mouth", "closed_eyes", "scared", "expressionless"]:
        return LAYER_EXPRESSION, SCOPE_TRANSIENT
    if name.endswith("_expression"):
        return LAYER_EXPRESSION, SCOPE_TRANSIENT

    # Rule 6: Action/Pose
    if name.endswith("ing") and name not in ["clothing", "wearing", "lighting", "shading"]:
        # e.g., sitting, standing, running, eating
        return LAYER_ACTION, SCOPE_TRANSIENT
    if name in ["looking_at_viewer", "looking_back", "from_behind"]:
        return LAYER_ACTION, SCOPE_TRANSIENT

    # Rule 7: Camera
    if name in ["close-up", "portrait", "upper_body", "full_body", "cowboy_shot", "dutch_angle", "from_above", "from_below"]:
        return LAYER_CAMERA, SCOPE_TRANSIENT

    # Rule 8: Environment
    if name.endswith("_background") or name in ["indoors", "outdoors", "simple_background"]:
        return LAYER_ENVIRONMENT, SCOPE_TRANSIENT
    if name in ["sky", "cloud", "sun", "moon", "night", "day", "sunset", "sunrise", "rain", "snow"]:
        return LAYER_ATMOSPHERE, SCOPE_TRANSIENT
    if name in ["bedroom", "classroom", "street", "beach", "forest", "room", "kitchen", "bathroom"]:
        return LAYER_ENVIRONMENT, SCOPE_TRANSIENT

    # Rule 9: Default Fallbacks
    # Identify objects vs abstract concepts? Hard with just regex.
    # Default to Accessory (Layer 6) / ANY if it seems like an object?
    # Or default to 0 and let user classify?
    # Let's verify WD14 Category 0 (General) -> Default Layer 6 (Acc) is safer than Environment.
    return LAYER_ACCESSORY, SCOPE_ANY


def import_tags():
    session = SessionLocal()
    try:
        if not os.path.exists(CSV_PATH):
            print(f"❌ CSV not found: {CSV_PATH}")
            return

        print(f"🚀 Importing WD14 tags from {CSV_PATH}...")
        
        # Determine "Legacy Category" default
        
        tags_to_insert = []
        
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # CSV usage: tag_id,name,category,count
                name = row["name"]
                wd14_cat = int(row["category"])
                count = int(row["count"])
                
                layer, scope = determine_layer_and_scope(name, wd14_cat)

                tags_to_insert.append({
                    "name": name,
                    "wd14_category": wd14_cat,
                    "wd14_count": count,
                    "default_layer": layer,
                    "usage_scope": scope,
                })
        
        # Inject Custom/Critical Tags that might be missing from WD14
        custom_tags = [
            ("masterpiece", LAYER_QUALITY, SCOPE_ANY),
            ("best_quality", LAYER_QUALITY, SCOPE_ANY),
            ("highres", LAYER_QUALITY, SCOPE_ANY),
            ("absurdres", LAYER_QUALITY, SCOPE_ANY),
            ("extremely_detailed", LAYER_QUALITY, SCOPE_ANY),
            ("anime", LAYER_ATMOSPHERE, SCOPE_TRANSIENT),
            ("photorealistic", LAYER_ATMOSPHERE, SCOPE_TRANSIENT),
            ("realistic", LAYER_ATMOSPHERE, SCOPE_TRANSIENT),
            ("3d", LAYER_ATMOSPHERE, SCOPE_TRANSIENT),
            ("illustration", LAYER_ATMOSPHERE, SCOPE_TRANSIENT),
        ]
        
        print(f"➕ Injecting {len(custom_tags)} custom tags...")
        for name, layer, scope in custom_tags:
            tags_to_insert.append({
                "name": name,
                "wd14_category": 0,
                "wd14_count": 0,
                "default_layer": layer,
                "usage_scope": scope,
            })
        
        print(f"📦 Prepared {len(tags_to_insert)} tags. Executing bulk upsert...")
        
        # Batch insert
        batch_size = 1000
        for i in range(0, len(tags_to_insert), batch_size):
            batch = tags_to_insert[i:i+batch_size]
            stmt = insert(Tag).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=['name'],
                set_={
                    "wd14_category": stmt.excluded.wd14_category,
                    "wd14_count": stmt.excluded.wd14_count,
                    "default_layer": stmt.excluded.default_layer,
                    "usage_scope": stmt.excluded.usage_scope,
                }
            )
            session.execute(stmt)
            session.commit()
            print(f"   Processed {i + len(batch)} / {len(tags_to_insert)}")
            
        print("✅ Import Completed!")

    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    import_tags()
