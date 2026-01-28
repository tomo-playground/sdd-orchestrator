from database import SessionLocal
from models.tag import Tag
from sqlalchemy import text

def normalize_db_tags():
    db = SessionLocal()
    try:
        # 1. Update standard tags
        tags = db.query(Tag).filter(Tag.name.like('% %')).all()
        print(f"Found {len(tags)} tags with spaces.")
        
        updated_count = 0
        for tag in tags:
            new_name = tag.name.replace(" ", "_").lower()
            # Check for collision
            existing = db.query(Tag).filter(Tag.name == new_name).first()
            if existing:
                print(f"  ⚠️ Collision: '{tag.name}' -> '{new_name}' (deleting duplicate)")
                db.delete(tag)
            else:
                tag.name = new_name
            updated_count += 1
            
        db.commit()
        print(f"✅ Normalized {updated_count} tags in DB.")
        
        # 2. Cleanup Character prompts (as they might have been created with spaces)
        from models.character import Character
        chars = db.query(Character).all()
        for char in chars:
            if char.custom_base_prompt:
                char.custom_base_prompt = char.custom_base_prompt.replace(" ", "_")
            if char.reference_base_prompt:
                # Complicated because of weights, but replace spaces inside commas
                parts = [p.strip().replace(" ", "_") for p in char.reference_base_prompt.split(",")]
                char.reference_base_prompt = ", ".join(parts)
            # Add others if needed
        db.commit()
        print(f"✅ Normalized character prompts in DB.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error during normalization: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    normalize_db_tags()
