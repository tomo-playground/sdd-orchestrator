"""Fix incorrect LoRA trigger words in the database."""

from database import SessionLocal
from models import LoRA


def main():
    db = SessionLocal()
    try:
        # LoRA ID 4: eureka_v9 -> should be Eureka
        lora_eureka = db.query(LoRA).filter(LoRA.id == 4).first()
        if lora_eureka:
            print(f"Fixing {lora_eureka.name}")
            lora_eureka.trigger_words = ["eureka (eureka seven)"]

        # LoRA ID 9: mha_midoriya-10 -> should be Midoriya
        lora_mha = db.query(LoRA).filter(LoRA.id == 9).first()
        if lora_mha:
            print(f"Fixing {lora_mha.name}")
            lora_mha.trigger_words = ["midoriya izuku"]

        # ID 5: flat_color -> should be empty or general
        lora_flat = db.query(LoRA).filter(LoRA.id == 5).first()
        if lora_flat:
            print(f"Fixing {lora_flat.name}")
            lora_flat.trigger_words = ["flat color"]

        # ID 6: Gentle_Cubism_Light -> should be general
        lora_cubism = db.query(LoRA).filter(LoRA.id == 6).first()
        if lora_cubism:
            print(f"Fixing {lora_cubism.name}")
            lora_cubism.trigger_words = ["cubism style"]

        db.commit()
        print("LoRA triggers fixed!")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
