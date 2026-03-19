import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random

from database import SessionLocal
from models.lora import LoRA


def populate_lora_calibration():
    session = SessionLocal()
    try:
        loras = session.query(LoRA).all()
        print(f"Updating {len(loras)} LoRAs with calibration data...")
        for lora in loras:
            # Set dummy calibration values
            # optimal_weight between 0.6 and 0.95
            lora.optimal_weight = 0.6 + (random.random() * 0.35)
            # calibration_score between 85 and 99
            lora.calibration_score = random.randint(85, 99)
            # weights
            lora.weight_min = 0.5
            lora.weight_max = 1.0

            print(f"   ✅ {lora.name}: {lora.optimal_weight:.2f} ({lora.calibration_score}%)")

        session.commit()
        print("Success!")
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    populate_lora_calibration()
