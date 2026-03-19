import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import Character


def main():
    db = SessionLocal()
    try:
        print("\n--- MediaAsset Storage Keys ---")
        chars = db.query(Character).all()
        for c in chars:
            if c.preview_image_asset:
                print(
                    f"ID:{c.id} | Name:{c.name} | StorageKey:{c.preview_image_asset.storage_key} | URL:{c.preview_image_url}"
                )
            else:
                print(f"ID:{c.id} | Name:{c.name} | NO PREVIEW ASSET")
    finally:
        db.close()


if __name__ == "__main__":
    main()
