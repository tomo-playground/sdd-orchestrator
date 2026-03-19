import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import VoicePreset


def main():
    db = SessionLocal()
    try:
        print("\n--- Voices ---")
        for v in db.query(VoicePreset).all():
            print(f"ID:{v.id} | Name:{v.name} | Language:{v.language} | Engine:{v.tts_engine}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
