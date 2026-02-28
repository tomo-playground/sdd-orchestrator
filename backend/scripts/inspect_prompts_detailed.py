import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import Character

def main():
    db = SessionLocal()
    try:
        print("\n--- Detailed Prompt Inspection ---")
        for char_id in [17, 18]:
            c = db.query(Character).filter(Character.id == char_id).first()
            if c:
                print(f"[{c.id}] {c.name}")
                print(f"  Base:\n{c.custom_base_prompt}\n")
                print(f"  Ref Base:\n{c.reference_base_prompt}\n")
                print("-" * 60)
    finally:
        db.close()

if __name__ == "__main__":
    main()
