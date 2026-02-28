import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import Character

def main():
    db = SessionLocal()
    try:
        print("\n--- Character Prompts & Quality Analysis ---")
        chars = db.query(Character).all()
        for c in chars:
            lora_count = len(c.loras) if c.loras else 0
            base_prompt = c.custom_base_prompt or ""
            ref_prompt = c.reference_base_prompt or ""
            ip_adapter = c.ip_adapter_model or "None"
            
            # Basic heuristics for quality
            has_trigger_words = lora_count > 0 and len(base_prompt) > 20
            has_reference_prompt = len(ref_prompt) > 20
            
            status = "🟢 GOOD" if (has_trigger_words and has_reference_prompt) else "🟡 NEEDS UPDATE"
            if len(base_prompt) < 10 and lora_count == 0:
                status = "🔴 POOR / INCOMPLETE"
            
            print(f"[{c.id}] {c.name} ({c.gender}) - {status}")
            print(f"  LoRAs:     {lora_count}")
            print(f"  Base Prom: {base_prompt[:80]}...")
            print(f"  Ref Prom:  {ref_prompt[:80]}...")
            print(f"  IP Adapter: {ip_adapter} (Weight: {c.ip_adapter_weight})")
            print("-" * 60)
    finally:
        db.close()

if __name__ == "__main__":
    main()
