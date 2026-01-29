import sys
from pathlib import Path
from sqlalchemy.future import select

# Add backend directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from database import SessionLocal
from models import LoRA

def main():
    db = SessionLocal()
    try:
        loras = db.query(LoRA).all()
        print(f"{'ID':<4} | {'Name':<30} | {'Type':<10} | {'Triggers':<30}")
        print("-" * 80)
        for lora in loras:
            triggers = ", ".join(lora.trigger_words[:3]) if lora.trigger_words else ""
            if len(triggers) > 30:
                triggers = triggers[:27] + "..."
            print(f"{lora.id:<4} | {lora.name:<30} | {str(lora.lora_type):<10} | {triggers:<30}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
