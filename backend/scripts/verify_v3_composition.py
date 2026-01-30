import os
import sys

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from services.prompt.v3_composition import V3PromptBuilder


def verify_v3_logic():
    db = SessionLocal()
    try:
        print("🧪 Testing V3 12-Layer Prompt Composition...")

        # 1. Setup Sample Tags if they don't exist (though they should from import)
        # masterpiece (L0), 1girl (L1), blue_eyes (L2), school_uniform (L4), smile (L7), classroom (L10)

        tags = ["masterpiece", "1girl", "blue_eyes", "school_uniform", "smile", "classroom"]

        # 2. Setup Sample LoRAs
        char_lora = {"name": "hana_model", "weight": 0.8, "trigger_words": ["hana_def"]}
        style_lora = {"name": "anime_style", "weight": 0.5, "trigger_words": ["manga_style"]}

        builder = V3PromptBuilder(db)

        # 3. Build Prompt
        prompt = builder.compose(
            tags=tags,
            character_loras=[char_lora],
            style_loras=[style_lora]
        )

        print(f"\n🚀 GENERATED PROMPT:\n{prompt}")

        # 4. Expectations
        # masterpiece (L0) -> 1girl (L1) -> (hana_def, LoRA:hana) (L2) -> blue_eyes (L2) -> school_uniform (L4) -> (smile:1.1) (L7) -> classroom (L10) -> manga_style (L11) -> LoRA:style (L11)

        tokens = [t.strip() for t in prompt.split(",")]

        print("\n🔍 Verification Board:")
        print(f"- masterpiece at start: {'✅' if tokens[0] == 'masterpiece' else '❌'}")
        print(f"- LoRA:hana exists: {'✅' if '<lora:hana_model:0.8>' in tokens else '❌'}")
        print(f"- BREAK inserted: {'✅' if 'BREAK' in tokens else '❌'}")
        print(f"- smile emphasized: {'✅' if '(smile:1.1)' in tokens else '❌'}")
        print(f"- Style LoRA at end: {'✅' if tokens[-1] == '<lora:anime_style:0.5>' else '❌'}")

    finally:
        db.close()

if __name__ == "__main__":
    verify_v3_logic()
