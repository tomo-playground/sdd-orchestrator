
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.tag_alias import TagAlias


def inspect_aliases():
    db = SessionLocal()
    try:
        count = db.query(TagAlias).count()
        print(f"Total Tag Aliases: {count}")

        print("\n--- First 20 Aliases ---")
        aliases = db.query(TagAlias).limit(20).all()
        for alias in aliases:
            print(f"ID: {alias.id} | {alias.source_tag} -> {alias.target_tag}")

    finally:
        db.close()

if __name__ == "__main__":
    inspect_aliases()
