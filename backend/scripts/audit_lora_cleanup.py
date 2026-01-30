
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.lora import LoRA
from models.character import Character
from sqlalchemy import or_

def check_loras():
    db = SessionLocal()
    try:
        lora_names = [
            "mha_midoriya-10", 
            "flat_color", 
            "Gentle_Cubism_Light", 
            "harukaze-doremi-casual", 
            "blindbox_v1_mix"
        ]
        
        print(f"Checking {len(lora_names)} LoRAs...")
        
        for name in lora_names:
            lora = db.query(LoRA).filter(or_(LoRA.name == name, LoRA.name.ilike(f"%{name}%"))).first()
            if lora:
                print(f"✅ Found LoRA: {lora.name}")
                print(f"   - Type: {lora.lora_type}")
                print(f"   - Triggers: {lora.trigger_words}")
            else:
                print(f"❌ LoRA NOT found: {name}")

        print("\nChecking Characters...")
        char_names = ["Midoriya", "Doremi", "Blindbox"]
        for name in char_names:
            char = db.query(Character).filter(Character.name.ilike(f"%{name}%")).first()
            if char:
                print(f"✅ Found Character: {char.name}")
                print(f"   - LoRAs: {char.loras}")
            else:
                print(f"❌ Character NOT found: {name}")
                
    finally:
        db.close()

if __name__ == "__main__":
    check_loras()
