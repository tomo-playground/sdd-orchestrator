"""delete_sd15_loras_insert_sdxl_loras

SD1.5 LoRA 13건 삭제 + SDXL LoRA 3건 등록:
- DELETE: id 15~27 (SD1.5, is_active=false)
- INSERT: Flat Color v2.0, Detailer, MeMaXL (SDXL V-Pred)

Revision ID: c802651d6ede
Revises: 021a74624d6e
Create Date: 2026-03-14 17:16:56.362339

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c802651d6ede"
down_revision: str | Sequence[str] | None = "021a74624d6e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# SD1.5 LoRA IDs to delete
SD15_LORA_IDS = list(range(15, 28))  # 15~27

# SDXL LoRA definitions
SDXL_LORAS = [
    {
        "name": "noobai_vpred_1_flat_color_v2",
        "display_name": "플랫 컬러 v2 (SDXL)",
        "lora_type": "style",
        "trigger_words": "{flat color}",
        "default_weight": 0.60,
        "weight_min": 0.40,
        "weight_max": 0.80,
        "base_model": "SDXL",
        "is_active": True,
        "civitai_url": "https://civitai.com/models/834089",
    },
    {
        "name": "NOOB_vp1_detailer_by_volnovik_v1",
        "display_name": "디테일 강화 (SDXL)",
        "lora_type": "style",
        "trigger_words": "{}",
        "default_weight": 0.40,
        "weight_min": 0.20,
        "weight_max": 0.60,
        "base_model": "SDXL",
        "is_active": True,
        "civitai_url": "https://civitai.com/models/859463",
    },
    {
        "name": "MeMaXL4",
        "display_name": "MeMaXL 플랫 애니 (SDXL)",
        "lora_type": "style",
        "trigger_words": "{memaxl}",
        "default_weight": 0.60,
        "weight_min": 0.40,
        "weight_max": 0.80,
        "base_model": "SDXL",
        "is_active": True,
        "civitai_url": "https://civitai.com/models/723781",
    },
]


def upgrade() -> None:
    """SD1.5 LoRA 삭제 + SDXL LoRA 등록."""
    conn = op.get_bind()

    # 1. SD1.5 LoRA 13건 삭제
    conn.execute(
        sa.text("DELETE FROM loras WHERE id = ANY(:ids)"),
        {"ids": SD15_LORA_IDS},
    )

    # 2. SDXL LoRA 3건 등록
    for lora in SDXL_LORAS:
        conn.execute(
            sa.text("""
                INSERT INTO loras (name, display_name, lora_type, trigger_words,
                    default_weight, weight_min, weight_max, base_model,
                    is_active, civitai_url)
                VALUES (:name, :display_name, :lora_type,
                    :trigger_words, :default_weight, :weight_min, :weight_max,
                    :base_model, :is_active, :civitai_url)
            """),
            lora,
        )


def downgrade() -> None:
    """SDXL LoRA 삭제 + SD1.5 LoRA 복원."""
    conn = op.get_bind()

    # 1. SDXL LoRA 삭제
    for lora in SDXL_LORAS:
        conn.execute(
            sa.text("DELETE FROM loras WHERE name = :name"),
            {"name": lora["name"]},
        )

    # 2. SD1.5 LoRA 복원 (is_active=false로)
    sd15_loras = [
        (15, "add_detail", "디테일 강화", "style", "{}", 0.50),
        (16, "blindbox_v1_mix", "블라인드박스 치비", "style", "{blindbox,chibi}", 0.70),
        (17, "chibi-laugh", "치비 웃음", "style", "{chibi}", 0.70),
        (18, "eureka_v9", "에우레카", "style", "{}", 0.60),
        (19, "flat_color", "플랫 컬러", "style", "{flat color}", 0.40),
        (20, "Gentle_Cubism_Light", "큐비즘 라이트", "style", "{cubism style}", 0.60),
        (21, "ghibli_style_offset", "지브리 스타일", "style", "{ghibli style}", 0.70),
        (22, "harukaze-doremi-casual", "하루카제 도레미", "character", "{hrkzdrm_cs}", 0.70),
        (23, "ip-adapter-faceid-plusv2_sd15_lora", "IP-Adapter FaceID LoRA", "style", "{}", 0.50),
        (24, "J_huiben", "그림책", "style", "{J_huiben}", 0.80),
        (25, "mha_midoriya-10", "미도리야 이즈쿠", "character", "{Midoriya_Izuku}", 0.70),
        (26, "shinkai_makoto_offset", "신카이 마코토", "style", "{shinkai makoto}", 1.00),
        (27, "Usagi_Drop_-_Nitani_Yukari", "니타니 유카리", "character", "{nitani_yukari}", 0.70),
    ]
    for lid, name, display, ltype, triggers, weight in sd15_loras:
        conn.execute(
            sa.text("""
                INSERT INTO loras (id, name, display_name, lora_type, trigger_words,
                    default_weight, base_model, is_active)
                VALUES (:id, :name, :display_name, :lora_type,
                    :trigger_words, :default_weight, 'SD1.5', false)
            """),
            {
                "id": lid,
                "name": name,
                "display_name": display,
                "lora_type": ltype,
                "trigger_words": triggers,
                "default_weight": weight,
            },
        )
