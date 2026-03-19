from sqlalchemy.orm.attributes import flag_modified

from database import SessionLocal
from models.character import Character
from models.lora import LoRA


def fix_data():
    db = SessionLocal()
    try:
        # 1. Fix LoRA Info
        print("🔧 Checking LoRA info for all characters...")
        characters = db.query(Character).all()
        for char in characters:
            if char.loras:
                modified = False
                new_loras = []
                for l_item in char.loras:
                    # Check if name is missing or None
                    if not l_item.get("name"):
                        lid = l_item.get("lora_id")
                        if lid:
                            lora = db.query(LoRA).filter(LoRA.id == lid).first()
                            if lora:
                                l_item["name"] = lora.name
                                l_item["trigger_words"] = lora.trigger_words
                                l_item["lora_type"] = lora.lora_type
                                print(f"  -> Enriched LoRA for {char.name}: {lora.name}")
                                modified = True
                    new_loras.append(l_item)

                if modified:
                    char.loras = new_loras
                    flag_modified(char, "loras")  # Force update for JSON/JSONB

        # 2. Update Chibi Chan Prompts
        print("🔧 Updating Chibi Chan prompts...")
        chibi = db.query(Character).filter(Character.name == "Chibi Chan").first()
        if chibi:
            chibi.reference_base_prompt = "masterpiece, best_quality, chibi, super_deformed, small_body, big_head, cute_anime_style, 1girl, solo, simple_background, white_background, full_body, standing, looking_at_viewer, smile, vibrant_colors"
            chibi.reference_negative_prompt = "lowres, bad_anatomy, bad_hands, text, error, missing_fingers, extra_digit, fewer_digits, cropped, worst_quality, low_quality, normal_quality, jpeg_artifacts, signature, watermark, username, blurry, easynegative, realistic, photorealistic"
            print("  -> Updated Chibi Chan prompts.")
        else:
            print("  -> Chibi Chan not found.")

        db.commit()
        print("✅ All updates completed successfully.")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    fix_data()
