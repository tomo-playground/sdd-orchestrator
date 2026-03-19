import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load env variables
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "../.env")))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found in environment.")
    sys.exit(1)


def audit_characters_vs_files():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, name, preview_image_url, ip_adapter_weight, ip_adapter_model FROM characters")
        )

        characters = list(result)
        print(f"--- Database Characters ({len(characters)}) ---")
        char_names = set()
        for char in characters:
            char_names.add(char.name)
            print(f"Name: {char.name}")
            print(f"  ID: {char.id}")
            print(f"  Preview URL: {char.preview_image_url}")
            print(f"  IP Adapter: weight={char.ip_adapter_weight}, model={char.ip_adapter_model}")
            print("-" * 20)

        print("\n--- Orphaned Reference Files ---")
        ref_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "references")
        if os.path.exists(ref_dir):
            files = [f for f in os.listdir(ref_dir) if f.endswith(".png")]
            for f in files:
                stem = os.path.splitext(f)[0]
                if stem not in char_names:
                    print(f"Orphaned File: {f}")
        else:
            print(f"Reference directory not found: {ref_dir}")


if __name__ == "__main__":
    audit_characters_vs_files()
