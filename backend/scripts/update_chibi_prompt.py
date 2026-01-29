
from database import SessionLocal
from models.character import Character

def update_chibi_prompt():
    db = SessionLocal()
    try:
        # Find Chibi Chan (assuming name is "Chibi Chan")
        chibi = db.query(Character).filter(Character.name == "Chibi Chan").first()
        if not chibi:
            print("❌ Character 'Chibi Chan' not found!")
            return

        print(f"Update Chibi Chan (ID: {chibi.id})...")
        
        # Update prompts
        chibi.reference_base_prompt = "masterpiece, best_quality, chibi, super_deformed, small_body, big_head, cute_anime_style, 1girl, solo, simple_background, white_background, full_body, standing, looking_at_viewer, smile, vibrant_colors"
        chibi.reference_negative_prompt = "lowres, bad_anatomy, bad_hands, text, error, missing_fingers, extra_digit, fewer_digits, cropped, worst_quality, low_quality, normal_quality, jpeg_artifacts, signature, watermark, username, blurry, easynegative, realistic, photorealistic"
        
        db.commit()
        print("✅ Successfully updated reference prompts for Chibi Chan.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_chibi_prompt()
