import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import LoRA


def main():
    db = SessionLocal()
    try:
        print("\n--- Available LoRAs ---")
        loras = db.query(LoRA).all()
        for l in loras:
            print(f"ID:{l.id} | Name:{l.name} | Type:{l.lora_type}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
