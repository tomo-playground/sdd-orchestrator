import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import or_
from database import SessionLocal
from models.tag_alias import TagAlias
from models.character import Character
from models.lora import LoRA
from models.sd_model import StyleProfile

def migrate_and_cleanup():
    db = SessionLocal()
    try:
        aliases = db.query(TagAlias).all()
        updated_count = 0
        deleted_count = 0
        migrated_chars = 0
        
        print("🔍 Scanning TagAliases for LoRA definitions...")
        
        lora_pattern = re.compile(r'<lora:([^:>]+)(?::[^:>]+)?(?::([0-9.]+))?>')

        for alias in aliases:
            if not alias.target_tag or '<lora:' not in alias.target_tag:
                continue

            # Extract LoRA info
            matches = lora_pattern.findall(alias.target_tag)
            if not matches:
                continue

            print(f"\nProcessing alias: '{alias.source_tag}' -> '{alias.target_tag}'")
            
            # Check if source_tag matches a Character
            char = db.query(Character).filter(
                or_(Character.name.ilike(alias.source_tag), Character.name.ilike(alias.source_tag.replace('_', ' ')))
            ).first()

            if char:
                print(f"  ✨ Found matching character: {char.name}")
                current_loras = char.loras or []
                modified_char = False
                
                for lora_name, weight_str in matches:
                    weight = float(weight_str) if weight_str else 0.8
                    
                    # Find LoRA in DB
                    lora_obj = db.query(LoRA).filter(LoRA.name == lora_name).first()
                    # Try fuzzy search if not found
                    if not lora_obj:
                         lora_obj = db.query(LoRA).filter(LoRA.name.ilike(f"%{lora_name}%")).first()
                    
                    if lora_obj:
                        # Check duplication
                        exists = any(l.get('lora_id') == lora_obj.id for l in current_loras)
                        if not exists:
                            print(f"    -> Migrating LoRA '{lora_obj.name}' (w={weight}) to character")
                            current_loras.append({
                                "lora_id": lora_obj.id,
                                "name": lora_obj.name,
                                "weight": weight,
                                "trigger_words": lora_obj.trigger_words or [],
                                "lora_type": lora_obj.lora_type or "style"
                            })
                            modified_char = True
                        else:
                            print(f"    -> Character already has LoRA '{lora_obj.name}'")
                    else:
                        print(f"    ⚠️  LoRA '{lora_name}' not found in DB. Skipping migration.")

                if modified_char:
                    char.loras = current_loras
                    migrated_chars += 1
            else:
                print(f"  ℹ️  No character matched. LoRA info will be removed from alias but not migrated.")

            # Remove LoRA string from target_tag
            new_target = lora_pattern.sub('', alias.target_tag)
            # Clean up commas and spaces
            new_target = re.sub(r',\s*,', ',', new_target)
            new_target = new_target.strip().strip(',').strip()
            
            source_norm = alias.source_tag.strip().lower()
            target_norm = new_target.strip().lower()

            # Decide action
            if not target_norm or target_norm == source_norm:
                print(f"  🗑️  Result is empty or redundant. Deleting alias.")
                db.delete(alias)
                deleted_count += 1
            else:
                print(f"  ✏️  Updating alias target to: '{new_target}'")
                alias.target_tag = new_target
                updated_count += 1

        db.commit()
        print(f"\n✅ Migration & Cleanup Complete!")
        print(f"   - Updated Aliases: {updated_count}")
        print(f"   - Deleted Aliases: {deleted_count}")
        print(f"   - Migrated Characters: {migrated_chars}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_and_cleanup()
