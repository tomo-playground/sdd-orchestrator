"""Remove LoRA tags from TagAlias entries."""
import re
from database import SessionLocal
from models.tag_alias import TagAlias

def cleanup_lora_aliases():
    db = SessionLocal()
    try:
        aliases = db.query(TagAlias).all()
        deleted_count = 0
        updated_count = 0
        
        for alias in aliases:
            if not alias.target_tag or '<lora:' not in alias.target_tag:
                continue
                
            # Remove LoRA tags
            lora_pattern = r',?\s*<lora:[^>]+>'
            new_target = re.sub(lora_pattern, '', alias.target_tag).strip().strip(',').strip()
            
            source_norm = alias.source_tag.strip().lower()
            target_norm = new_target.strip().lower()
            
            # Delete if redundant (target is empty or same as source)
            if not target_norm or target_norm == source_norm:
                print(f'DELETE: {alias.source_tag} -> {alias.target_tag}')
                db.delete(alias)
                deleted_count += 1
            else:
                print(f'UPDATE: {alias.source_tag}: {alias.target_tag} -> {new_target}')
                alias.target_tag = new_target
                updated_count += 1
        
        db.commit()
        print(f'\n✅ Cleanup complete: DELETED {deleted_count}, UPDATED {updated_count}')
        return {"deleted": deleted_count, "updated": updated_count}
    except Exception as e:
        print(f'❌ Error: {e}')
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == '__main__':
    cleanup_lora_aliases()
