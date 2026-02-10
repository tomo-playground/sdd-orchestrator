from database import SessionLocal
from models.tag_alias import TagAlias


def add_chibi_alias():
    db = SessionLocal()
    try:
        # Check existing
        existing = db.query(TagAlias).filter(TagAlias.source_tag == "chibi").first()
        if existing:
            print(f"Update existing alias for 'chibi' (was {existing.target_tag})")
            existing.target_tag = "chibi, <lora:blindbox_v1_mix:0.8>"
            existing.reason = "Auto-inject LoRA"
        else:
            print("Creating new alias for 'chibi'")
            alias = TagAlias(
                source_tag="chibi",
                target_tag="chibi, <lora:blindbox_v1_mix:0.8>",
                reason="Auto-inject LoRA",
                is_active=True
            )
            db.add(alias)

        db.commit()
        print("✅ Successfully added/updated alias for 'chibi'")
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_chibi_alias()
