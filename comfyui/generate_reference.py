"""캐릭터 레퍼런스 이미지 생성 — ComfyUI workflow runner 사용."""

from __future__ import annotations

import sys
import time
from pathlib import Path

# backend 모듈 접근
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from workflow_runner import run_workflow

from config import DEFAULT_REFERENCE_NEGATIVE_PROMPT
from database import SessionLocal
from models.character import Character
from services.prompt.composition import get_prompt_builder

OUTPUT_DIR = Path("/tmp/comfy-test")
OUTPUT_DIR.mkdir(exist_ok=True)

# ComfyUI 안정 설정 (NoobAI XL v-pred)
CHECKPOINT = "noobaiXLNAIXL_vPred10Version.safetensors"
STYLE_LORA = "noobai_vpred_1_flat_color_v2.safetensors"
LORA_STRENGTH = 0.7
WIDTH = 832
HEIGHT = 1216


def get_character_prompts(character_id: int) -> tuple[str, str]:
    """DB에서 캐릭터 프롬프트를 실서비스 파이프라인으로 조합."""
    db = SessionLocal()
    try:
        char = db.query(Character).filter(Character.id == character_id).first()
        if not char:
            raise ValueError(f"Character {character_id} not found")

        builder = next(get_prompt_builder())
        positive = builder.compose_for_reference(char)

        # LoRA 트리거 워드 추가 (flat color)
        if "flat color" not in positive:
            positive = "flat color, " + positive

        neg_parts = []
        if char.negative_prompt:
            neg_parts.append(char.negative_prompt)
        neg_parts.append(DEFAULT_REFERENCE_NEGATIVE_PROMPT)
        negative = ", ".join(neg_parts)

        return positive, negative
    finally:
        db.close()


def generate_reference(character_id: int, seed: int = -1) -> Path:
    """캐릭터 레퍼런스 이미지 생성."""
    positive, negative = get_character_prompts(character_id)

    if seed == -1:
        import random

        seed = random.randint(0, 2**32 - 1)

    print(f"캐릭터 ID: {character_id}")
    print(f"Positive: {positive[:80]}...")
    print(f"Seed: {seed}")

    start = time.time()
    images = run_workflow(
        "reference",
        {
            "positive": positive,
            "negative": negative,
            "checkpoint": CHECKPOINT,
            "lora_name": STYLE_LORA,
            "lora_strength": LORA_STRENGTH,
            "seed": seed,
            "width": WIDTH,
            "height": HEIGHT,
        },
    )

    elapsed = time.time() - start
    out_path = OUTPUT_DIR / f"ref_char{character_id}_seed{seed}.png"
    out_path.write_bytes(images[0])
    print(f"완료 ({elapsed:.1f}초) → {out_path}")
    return out_path


if __name__ == "__main__":
    char_id = int(sys.argv[1]) if len(sys.argv) > 1 else 35  # 기본: 하은
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else -1
    generate_reference(char_id, seed)
