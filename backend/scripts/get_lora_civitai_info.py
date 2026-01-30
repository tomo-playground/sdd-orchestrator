import os
import sys

# Adjust path if run from backend dir
if os.getcwd().endswith('backend'):
    sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))
elif os.path.exists('backend'):
     sys.path.append(os.getcwd())

from backend.config import DATABASE_URL
from backend.models.lora import LoRA
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def get_civitai_info():
    # Use direct session creation to avoid potential import side-effects with model bases
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        target_loras = [
            'chibi-laugh',
            'eureka_v9',
            'flat_color',
            'Gentle_Cubism_Light',
            'blindbox_v1_mix',
            'harukaze-doremi-casual',
            'mha_midoriya-10'
        ]

        # We might need to use the model class if mapped, or reflection if we want to be safe
        # But let's try just importing LoRA and see if we can avoid the error by not importing all models via __init__ or similar
        # Actually the error comes from importing backend.models.lora presumably if it was already imported elsewhere or Base metadata conflict

        loras = db.query(LoRA).filter(LoRA.name.in_(target_loras)).all()

        print("--- LoRA Civitai Info ---")
        for lora in loras:
            print(f"LoRA: {lora.name}")
            print(f"  ID: {lora.civitai_id}")
            print(f"  URL: {lora.civitai_url}")
            print(f"  Triggers: {lora.trigger_words}")
            print("-" * 20)

    finally:
        db.close()

if __name__ == "__main__":
    get_civitai_info()
