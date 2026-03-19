import os
import sys

# Add backend directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.tag import Tag


def delete_tag(name):
    session = SessionLocal()
    try:
        tag = session.query(Tag).filter(Tag.name == name).first()
        if tag:
            session.delete(tag)
            session.commit()
            print(f"✅ Deleted '{name}' from DB.")
        else:
            print(f"⚠️ '{name}' not found in DB.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    delete_tag("anime")
