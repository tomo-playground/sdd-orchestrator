import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import VoicePreset

def main():
    db = SessionLocal()
    try:
        print("\n--- Audio Presets Database Dump ---")
        voices = db.query(VoicePreset).all()
        for v in voices:
            print(f"ID: {v.id}")
            print(f"Name: {v.name}")
            print(f"Desc: {v.description}")
            print(f"Voice Design: {v.voice_design_prompt}")
            print(f"Seed: {v.voice_seed}")
            print("-" * 30)

    finally:
        db.close()

if __name__ == "__main__":
    main()
