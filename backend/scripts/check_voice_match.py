import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import Character, VoicePreset

def main():
    db = SessionLocal()
    try:
        print("\n--- Audio Presets Check ---")
        chars = db.query(Character).all()
        voices = db.query(VoicePreset).all()
        
        voice_dict = {v.id: v for v in voices}
        
        for char in chars:
            voice = voice_dict.get(char.voice_preset_id)
            if voice:
                v_name = voice.name
                v_desc = voice.description or "No description"
            else:
                v_name = "None"
                v_desc = "None"
                
            print(f"[{char.name} ({char.gender})] -> Voice: {v_name}")
            print(f"   Char Desc: {char.description}")
            print(f"   Voice Desc: {v_desc}\n")
            
        print("--- Unused Voices ---")
        used_voice_ids = {c.voice_preset_id for c in chars if c.voice_preset_id}
        for v in voices:
            if v.id not in used_voice_ids:
                print(f"Voice: {v.name} (Desc: {v.description})")

    finally:
        db.close()

if __name__ == "__main__":
    main()
