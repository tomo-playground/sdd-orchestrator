
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.character import Character
from services.controlnet import generate_reference_for_character

async def sync_chibi_chan():
    db = SessionLocal()
    try:
        character = db.query(Character).filter(Character.name == "Chibi Chan").first()
        if not character:
            print("Chibi Chan not found!")
            return
        
        print(f"Generating IP-Adapter reference for {character.name}...")
        # This will save to assets/references/Chibi_Chan.png
        filename = await generate_reference_for_character(db, character)
        print(f"Success! Saved as {filename}")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(sync_chibi_chan())
