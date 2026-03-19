from database import SessionLocal
from models.tag_alias import TagAlias


def register_eureka_rule():
    db = SessionLocal()
    try:
        # User defined trigger words
        trigger_words = "eureka, 1girl, choker, short aqua hair, hairclip, purple eyes, white-blue dress, long sleeves, white-blue boots"

        # Target: Triggers + LoRA syntax
        # Using weight 0.8 as standard
        target_tag = f"{trigger_words}, <lora:eureka_v9:0.8>"

        # Source tag: "eureka" (simple keyword to trigger everything)
        source_tag = "eureka"

        existing = db.query(TagAlias).filter(TagAlias.source_tag == source_tag).first()
        if existing:
            print(f"Updating existing alias for '{source_tag}'")
            existing.target_tag = target_tag
            existing.reason = "User manual trigger definition"
        else:
            print(f"Creating new alias for '{source_tag}'")
            db.add(
                TagAlias(
                    source_tag=source_tag,
                    target_tag=target_tag,
                    reason="User manual trigger definition",
                    is_active=True,
                )
            )

        db.commit()
        print("✅ Eureka rule registered successfully!")
        print(f"   Input: '{source_tag}'")
        print(f"   Result: '{target_tag}'")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    register_eureka_rule()
