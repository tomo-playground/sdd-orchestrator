
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.character import Character
from models.lora import LoRA


def list_candidates():
    db = SessionLocal()
    try:
        print("--- Characters ---")
        chars = db.query(Character).all()
        for c in chars:
            print(f"[{c.id}] {c.name}")

        print("\n--- LoRAs ---")
        loras = db.query(LoRA).all()
        for lora in loras:
            print(f"[{lora.id}] {lora.name} (type: {lora.lora_type})")

    finally:
        db.close()

if __name__ == "__main__":
    list_candidates()
