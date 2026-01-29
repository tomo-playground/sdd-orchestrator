
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.character import Character
from services.controlnet import generate_reference_for_character

async def regenerate_references():
    db = SessionLocal()
    try:
        # Target characters
        target_names = ["Blindbox", "Chibi Chan", "Doremi", "Flat Color Girl"]
        characters = db.query(Character).filter(Character.name.in_(target_names)).all()
        
        if not characters:
            print("No matching characters found!")
            return
        
        print(f"Found {len(characters)} characters to regenerate.")
        
        for character in characters:
            try:
                print(f"Generating IP-Adapter reference for {character.name}...")
                # This will save to assets/references/{character_name}.png
                filename = await generate_reference_for_character(db, character)
                print(f"  ✅ Success! Saved as {filename}")
            except Exception as e:
                print(f"  ❌ Failed for {character.name}: {e}")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(regenerate_references())
