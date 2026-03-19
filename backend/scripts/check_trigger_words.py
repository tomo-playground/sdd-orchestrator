import os
import sys

# We assume this script is run with PYTHONPATH=backend
# So we can import directly from models and database

try:
    from database import SessionLocal
    from models.lora import LoRA
except ImportError:
    # If run from root without PYTHONPATH=backend, try setting it up
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from backend.database import SessionLocal
    from backend.models.lora import LoRA


def check_trigger_words():
    db = SessionLocal()
    try:
        loras = db.query(LoRA).all()
        print("--- Trigger Words Report ---")
        param_issues = []
        for lora in loras:
            if not lora.trigger_words:
                continue

            issues = []
            for tag in lora.trigger_words:
                if " " in tag:
                    issues.append(f"Space found in '{tag}' (should be '{tag.replace(' ', '_')}')")
                if tag != tag.lower() and not tag.startswith("by "):
                    issues.append(f"Uppercase found in '{tag}' (should be '{tag.lower()}')")

            if issues:
                param_issues.append((lora.name, issues))
                print(f"LoRA: {lora.name}")
                for issue in issues:
                    print(f"  - {issue}")

        if not param_issues:
            print("All trigger words seem to follow basic Danbooru standards (snake_case, lowercase).")

    finally:
        db.close()


if __name__ == "__main__":
    check_trigger_words()
