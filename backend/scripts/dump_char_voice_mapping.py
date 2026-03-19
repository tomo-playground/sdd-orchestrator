import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import Character, VoicePreset


def main():
    db = SessionLocal()
    try:
        print("\n--- Character to TTS Voice Mapping Analysis ---\n")
        chars = db.query(Character).all()
        for c in chars:
            print(f"[{c.id}] Character: {c.name} ({c.gender})")
            print(f"   Visual Persona: {c.description[:100]}...")
            print(f"   Visual Prompt:  {c.custom_base_prompt[:100]}...")

            if c.voice_preset_id:
                vp = db.query(VoicePreset).filter(VoicePreset.id == c.voice_preset_id).first()
                if vp:
                    print(f"   >> Assigned Voice: [ID:{vp.id}] {vp.name}")
                    print(f"   >> Voice Desc:     {vp.description}")
                    print(
                        f"   >> Voice Design:   {vp.voice_design_prompt[:120]}..."
                        if vp.voice_design_prompt
                        else "   >> Voice Design:   None"
                    )
                else:
                    print(f"   >> Assigned Voice: ID {c.voice_preset_id} (NOT FOUND)")
            else:
                print("   >> Assigned Voice: None")

            print("-" * 80)
    finally:
        db.close()


if __name__ == "__main__":
    main()
