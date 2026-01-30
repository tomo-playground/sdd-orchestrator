import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from database import SessionLocal
from models import LoRA


def main():
    db = SessionLocal()
    try:
        # Find chibi-laugh LoRA
        lora = db.query(LoRA).filter(LoRA.name == "chibi-laugh").first()

        if not lora:
            print("❌ chibi-laugh LoRA not found")
            return

        # Update metadata manually
        # Based on common chibi-laugh LoRAs, this is typically a style/pose LoRA
        lora.lora_type = "pose"
        lora.display_name = "Chibi Laugh"
        lora.trigger_words = ["chibi", "laughing", "open mouth", "happy"]

        db.commit()
        db.refresh(lora)

        print("✅ Updated chibi-laugh:")
        print(f"   Type: {lora.lora_type}")
        print(f"   Display Name: {lora.display_name}")
        print(f"   Triggers: {lora.trigger_words}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
