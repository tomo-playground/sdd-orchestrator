
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.tag import Tag, TagRule


def check_existing_rule():
    db = SessionLocal()
    try:
        rules = db.query(TagRule).filter(TagRule.rule_type == "conflict").all()
        print(f"Checking {len(rules)} existing conflict rules...")

        found = False
        for rule in rules:
            t1 = db.query(Tag).get(rule.source_tag_id)
            t2 = db.query(Tag).get(rule.target_tag_id)
            if t1 and t2:
                pair = {t1.name, t2.name}
                if pair == {"sitting", "standing"}:
                    print(f"✅ Found existing rule: {t1.name} <-> {t2.name}")
                    found = True
                    break

        if not found:
            print("❌ No existing rule for sitting <-> standing")

    finally:
        db.close()

if __name__ == "__main__":
    check_existing_rule()
