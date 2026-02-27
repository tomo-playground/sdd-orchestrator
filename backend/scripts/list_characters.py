import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import joinedload

from database import SessionLocal
from models import Character


def main():
    db = SessionLocal()
    try:
        characters = db.query(Character).options(joinedload(Character.tags)).all()

        print(f"\n{'ID':<4} | {'Name':<25} | {'Gender':<8} | {'LoRAs':<30}")
        print("-" * 78)

        for char in characters:
            loras_str = ""
            if char.loras:
                loras_str = f"{len(char.loras)} LoRA(s)"

            print(f"{char.id:<4} | {char.name:<25} | {str(char.gender):<8} | {loras_str:<30}")

        print(f"\nTotal: {len(characters)} characters")

    finally:
        db.close()


if __name__ == "__main__":
    main()
