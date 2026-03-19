import os
import sys

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from backend.database import SessionLocal
from backend.models.sd_model import SDModel


def main():
    db = SessionLocal()
    try:
        # Find active models
        active_models = db.query(SDModel).filter(SDModel.is_active).all()

        if not active_models:
            print("No active models found in database.")
            # Fallback: check all models
            all_models = db.query(SDModel).all()
            if all_models:
                print(f"Found {len(all_models)} inactive models:")
                for m in all_models:
                    print(f"- {m.name} (Base: {m.base_model})")
            else:
                print("No models found in database at all.")
            return

        print(f"Found {len(active_models)} active model(s):")
        for m in active_models:
            print(f"- Name: {m.name}")
            print(f"  Base Model: {m.base_model}")
            print(f"  Civitai ID: {m.civitai_id}")
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
