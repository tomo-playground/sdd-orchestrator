"""noobai_xl_vpred_migration

NoobAI-XL V-Pred 전환:
- loras 테이블에 is_active 컬럼 추가
- sd_models: NoobAI-XL V-Pred 1.0 INSERT, SD1.5 체크포인트 비활성화
- embeddings: SDXL 임베딩 3건 INSERT, SD1.5 임베딩 비활성화
- style_profiles: 전체 프로필 NoobAI-XL 기반으로 업데이트
- loras: SD1.5 LoRA 전부 비활성화

Revision ID: 021a74624d6e
Revises: e0432dd57121
Create Date: 2026-03-14 15:48:46.197270

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '021a74624d6e'
down_revision: Union[str, Sequence[str], None] = 'e0432dd57121'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """NoobAI-XL V-Pred 전환: 스키마 변경 + 데이터 마이그레이션."""
    conn = op.get_bind()

    # ── 1. 스키마 변경: loras.is_active 컬럼 추가 ──
    op.add_column(
        "loras",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    # ── 2. sd_models: NoobAI-XL V-Pred 1.0 INSERT ──
    conn.execute(sa.text("""
        INSERT INTO sd_models (name, display_name, model_type, base_model, is_active)
        VALUES (
            'noobaiXLNAIXL_vPred10Version.safetensors',
            'NoobAI-XL V-Pred 1.0',
            'checkpoint',
            'SDXL',
            true
        )
    """))

    # SD1.5 체크포인트 비활성화
    conn.execute(sa.text("""
        UPDATE sd_models SET is_active = false WHERE base_model = 'SD1.5'
    """))

    # ── 3. embeddings: SDXL 임베딩 INSERT + SD1.5 비활성화 ──
    conn.execute(sa.text("""
        INSERT INTO embeddings (name, display_name, embedding_type, base_model, is_active)
        VALUES
            ('SmoothNoob_Negative', 'SmoothNoob 네거티브', 'negative', 'SDXL', true),
            ('SmoothNoob_Quality', 'SmoothNoob 퀄리티', 'positive', 'SDXL', true),
            ('SmoothNegative_Hands', 'SmoothNegative 핸드', 'negative', 'SDXL', true)
    """))

    # SD1.5 임베딩 비활성화
    conn.execute(sa.text("""
        UPDATE embeddings SET is_active = false WHERE base_model = 'SD1.5'
    """))

    # ── 4. style_profiles: NoobAI-XL 기반으로 업데이트 ──
    # 새 모델/임베딩 ID를 name 기반으로 조회
    noobai_id = conn.execute(sa.text(
        "SELECT id FROM sd_models WHERE name = 'noobaiXLNAIXL_vPred10Version.safetensors'"
    )).scalar_one()

    smooth_neg_id = conn.execute(sa.text(
        "SELECT id FROM embeddings WHERE name = 'SmoothNoob_Negative'"
    )).scalar_one()

    smooth_quality_id = conn.execute(sa.text(
        "SELECT id FROM embeddings WHERE name = 'SmoothNoob_Quality'"
    )).scalar_one()

    smooth_hands_id = conn.execute(sa.text(
        "SELECT id FROM embeddings WHERE name = 'SmoothNegative_Hands'"
    )).scalar_one()

    neg_embedding_ids = f"{{{smooth_neg_id},{smooth_hands_id}}}"
    pos_embedding_ids = f"{{{smooth_quality_id}}}"

    # 모든 style_profiles 공통 업데이트
    conn.execute(sa.text("""
        UPDATE style_profiles
        SET sd_model_id = :noobai_id,
            default_sampler_name = 'Euler',
            default_cfg_scale = 4.5,
            negative_embeddings = :neg_ids,
            positive_embeddings = :pos_ids,
            loras = '[]'::jsonb,
            updated_at = NOW()
    """), {
        "noobai_id": noobai_id,
        "neg_ids": neg_embedding_ids,
        "pos_ids": pos_embedding_ids,
    })

    # ── 5. loras: SD1.5 LoRA 전부 비활성화 ──
    conn.execute(sa.text("""
        UPDATE loras SET is_active = false WHERE base_model = 'SD1.5'
    """))


def downgrade() -> None:
    """NoobAI-XL V-Pred 전환 롤백."""
    conn = op.get_bind()

    # ── 5. loras: SD1.5 LoRA 복원 ──
    conn.execute(sa.text("""
        UPDATE loras SET is_active = true WHERE base_model = 'SD1.5'
    """))

    # ── 4. style_profiles: 원래 값으로 복원 ──
    # Realistic (id=2): sd_model_id=6, DPM++ SDE Karras, cfg=5, clip=1, steps=25
    conn.execute(sa.text("""
        UPDATE style_profiles
        SET sd_model_id = 6,
            default_sampler_name = 'DPM++ SDE Karras',
            default_cfg_scale = 5,
            negative_embeddings = '{8,9,11,14}',
            positive_embeddings = '{}',
            loras = '[{"weight": 0.4, "lora_id": 15}]'::jsonb,
            updated_at = NOW()
        WHERE name = 'Realistic'
    """))

    # Flat Color Anime (id=3): sd_model_id=5, DPM++ 2M Karras, cfg=6.5, clip=2, steps=28
    conn.execute(sa.text("""
        UPDATE style_profiles
        SET sd_model_id = 5,
            default_sampler_name = 'DPM++ 2M Karras',
            default_cfg_scale = 6.5,
            negative_embeddings = '{8,9,10,11,12,13}',
            positive_embeddings = '{}',
            loras = '[{"weight": 0.4, "lora_id": 19}, {"weight": 0.3, "lora_id": 15}]'::jsonb,
            updated_at = NOW()
        WHERE name = 'Flat Color Anime'
    """))

    # Studio Ghibli (id=5): sd_model_id=5, DPM++ 2M Karras, cfg=8, clip=2, steps=28
    conn.execute(sa.text("""
        UPDATE style_profiles
        SET sd_model_id = 5,
            default_sampler_name = 'DPM++ 2M Karras',
            default_cfg_scale = 8,
            negative_embeddings = '{8,9,10,11,12,13}',
            positive_embeddings = NULL,
            loras = '[{"weight": 0.7, "lora_id": 21}, {"weight": 0.25, "lora_id": 15}]'::jsonb,
            updated_at = NOW()
        WHERE name = 'Studio Ghibli'
    """))

    # Makoto Shinkai (id=7): sd_model_id=5, DPM++ 2M Karras, cfg=7, clip=2, steps=30
    conn.execute(sa.text("""
        UPDATE style_profiles
        SET sd_model_id = 5,
            default_sampler_name = 'DPM++ 2M Karras',
            default_cfg_scale = 7,
            negative_embeddings = '{8,9,10,11,12,13}',
            positive_embeddings = '{}',
            loras = '[{"weight": 0.7, "lora_id": 26}, {"weight": 0.25, "lora_id": 15}]'::jsonb,
            updated_at = NOW()
        WHERE name = 'Makoto Shinkai'
    """))

    # Default Anime (id=10): sd_model_id=5, DPM++ 2M Karras, cfg=6.5, clip=2, steps=28
    conn.execute(sa.text("""
        UPDATE style_profiles
        SET sd_model_id = 5,
            default_sampler_name = 'DPM++ 2M Karras',
            default_cfg_scale = 6.5,
            negative_embeddings = '{8,9,10,11,12,13}',
            positive_embeddings = '{}',
            loras = '[]'::jsonb,
            updated_at = NOW()
        WHERE name = 'Default Anime'
    """))

    # ── 3. embeddings: SDXL 임베딩 삭제 + SD1.5 복원 ──
    conn.execute(sa.text("""
        UPDATE embeddings SET is_active = true WHERE base_model = 'SD1.5'
    """))
    conn.execute(sa.text("""
        DELETE FROM embeddings WHERE name IN (
            'SmoothNoob_Negative', 'SmoothNoob_Quality', 'SmoothNegative_Hands'
        )
    """))

    # ── 2. sd_models: SD1.5 복원 + NoobAI 삭제 ──
    conn.execute(sa.text("""
        UPDATE sd_models SET is_active = true WHERE base_model = 'SD1.5'
    """))
    conn.execute(sa.text("""
        DELETE FROM sd_models WHERE name = 'noobaiXLNAIXL_vPred10Version.safetensors'
    """))

    # ── 1. 스키마 롤백: loras.is_active 컬럼 삭제 ──
    op.drop_column("loras", "is_active")
