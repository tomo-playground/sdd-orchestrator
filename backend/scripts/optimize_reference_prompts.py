"""Update characters with new optimized reference prompts and relative preview URLs."""

import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from config import DEFAULT_REFERENCE_BASE_PROMPT, DEFAULT_REFERENCE_NEGATIVE_PROMPT
from database import SessionLocal
from models.character import Character


def main():
    db = SessionLocal()
    try:
        characters = db.query(Character).all()
        print(f"Updating {len(characters)} characters...")

        for char in characters:
            # Only update if it's still using old defaults or is empty
            # We check for common old keywords
            old_positive_keywords = ["anime portrait", "clean background", "head and shoulders"]
            old_negative_keywords = ["from side", "from behind", "profile"]

            is_old_pos = any(k in (char.reference_base_prompt or "") for k in old_positive_keywords)
            is_old_neg = any(k in (char.reference_negative_prompt or "") for k in old_negative_keywords)

            if is_old_pos or not char.reference_base_prompt:
                print(f"  Character {char.name}: Updating Positive Reference Prompt")
                char.reference_base_prompt = DEFAULT_REFERENCE_BASE_PROMPT

            if is_old_neg or not char.reference_negative_prompt:
                print(f"  Character {char.name}: Updating Negative Reference Prompt")
                char.reference_negative_prompt = DEFAULT_REFERENCE_NEGATIVE_PROMPT

            # Fix preview_image_url to be relative if it contains localhost
            if char.preview_image_url and "localhost:8000" in char.preview_image_url:
                print(f"  Character {char.name}: Making preview URL relative")
                char.preview_image_url = char.preview_image_url.split("localhost:8000")[-1]

        db.commit()
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
