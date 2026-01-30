
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Tag, TagRule


def migrate_rules():
    db = SessionLocal()
    try:
        print("Starting tag rule migration...")

        # List of conflicting pairs to migrate
        conflicts = [
            # Expression conflicts
            ('crying', 'laughing'), ('crying', 'happy'), ('crying', 'smile'),
            ('sad', 'happy'), ('sad', 'smile'), ('sad', 'laughing'),
            ('angry', 'happy'), ('angry', 'smile'),
            # Gaze conflicts
            ('looking_down', 'looking_up'), ('looking_away', 'looking_at_viewer'),
            ('closed_eyes', 'looking_at_viewer'),
            # Pose conflicts
            ('sitting', 'standing'), ('lying', 'standing'), ('lying', 'sitting'),
        ]

        count = 0
        skipped = 0

        for s_name, t_name in conflicts:
            # Find tags
            s_tag = db.query(Tag).filter(Tag.name == s_name).first()
            t_tag = db.query(Tag).filter(Tag.name == t_name).first()

            if not s_tag or not t_tag:
                print(f"⚠️  Skipping pair ({s_name}, {t_name}): One or both tags not found in DB.")
                continue

            # Check if rule already exists (bidirectional check not strictly needed if we consistently add, but good for safety)
            exists = db.query(TagRule).filter(
                TagRule.source_tag_id == s_tag.id,
                TagRule.target_tag_id == t_tag.id,
                TagRule.rule_type == 'conflict'
            ).first()

            if not exists:
                # Also check reverse direction just in case
                reverse_exists = db.query(TagRule).filter(
                    TagRule.source_tag_id == t_tag.id,
                    TagRule.target_tag_id == s_tag.id,
                    TagRule.rule_type == 'conflict'
                ).first()

                if not reverse_exists:
                    rule = TagRule(
                        source_tag_id=s_tag.id,
                        target_tag_id=t_tag.id,
                        rule_type='conflict',
                        message='Conflicting tags',
                        active=True
                    )
                    db.add(rule)
                    count += 1
                    print(f"✅ Added conflict rule: {s_name} <-> {t_name}")
                else:
                    skipped += 1
            else:
                skipped += 1

        db.commit()
        print("\nMigration complete!")
        print(f"- Added: {count}")
        print(f"- Skipped (already exists): {skipped}")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_rules()
