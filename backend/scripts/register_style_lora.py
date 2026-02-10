import argparse

from database import SessionLocal
from models.lora import LoRA
from models.tag_alias import TagAlias


def register_style_lora(tag_name: str, lora_name_query: str, weight: float = 0.8):
    """Register a style tag to automatically trigger a LoRA via TagAlias."""
    db = SessionLocal()
    try:
        # 1. Find LoRA
        lora = db.query(LoRA).filter(LoRA.name.ilike(f"%{lora_name_query}%")).first()
        if not lora:
            print(f"❌ LoRA matching '{lora_name_query}' not found.")
            return

        print(f"✅ Found LoRA: {lora.name}")

        # 2. Construct Target Tag
        # e.g., "chibi, <lora:blindbox_v1_mix:0.8>"
        # If trigger words exist, we could add them, but sometimes they are weird (BTM).
        # Let's keep it simple: Tag + LoRA
        target_tag = f"{tag_name}, <lora:{lora.name}:{weight}>"

        # 3. Create or Update Alias
        existing = db.query(TagAlias).filter(TagAlias.source_tag == tag_name).first()
        if existing:
            print(f"🔄 Updating existing alias for '{tag_name}':")
            print(f"   Old: {existing.target_tag}")
            print(f"   New: {target_tag}")
            existing.target_tag = target_tag
            existing.reason = "Auto-inject Style LoRA"
        else:
            print(f"✨ Creating new alias for '{tag_name}' -> '{target_tag}'")
            alias = TagAlias(
                source_tag=tag_name,
                target_tag=target_tag,
                reason="Auto-inject Style LoRA",
                is_active=True
            )
            db.add(alias)

        db.commit()
        print("Done! Restart backend to apply changes.")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Map a style tag to a LoRA")
    parser.add_argument("tag", help=" The prompt tag (e.g. 'chibi')")
    parser.add_argument("lora", help="Part of the LoRA name (e.g. 'blindbox')")
    parser.add_argument("--weight", type=float, default=0.8, help="LoRA weight")

    args = parser.parse_args()
    register_style_lora(args.tag, args.lora, args.weight)
