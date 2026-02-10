# Lab-Studio 로직 통합 구현 계획서

**작성일**: 2026-02-08
**상태**: Ready for Implementation
**우선순위**: P0 (최우선)

---

## Executive Summary

### 문제
- Tag Lab이 Studio와 **완전히 다른 이미지 생성 로직** 사용
- Character LoRA, Style LoRA, Quality Tags를 **전혀 적용하지 않음**
- Lab 실험 결과가 **Studio 환경을 예측할 수 없어 무의미함**

### 해결
- **공통 Core 모듈** (`image_generation_core.py`) 생성
- Lab/Studio 모두 **동일한 V3 Prompt Engine + Style Profile** 사용
- **3단계 점진적 마이그레이션**: Tag Lab → Scene Lab → Studio

### 예상 효과
- ✅ Lab 실험 결과가 Studio 프로덕션 환경과 **100% 일치**
- ✅ Character/Style LoRA 효과 **정확한 측정** 가능
- ✅ Tag Effectiveness 데이터 **신뢰성 향상** (Match Rate 10-20% 개선 예상)

---

## 설계 결정 사항

### 1. Lab 소속 관계
**결정**: Lab 실험은 **Group 소속 필수** (`group_id NOT NULL`)

**근거**:
- Lab이 Group Config를 통해 Style Profile, LoRA를 사용
- 설정 소유권 원칙 준수 (Lab → Group Config → Style Profile)
- Analytics: Group별 실험 통계 집계 가능

### 2. Narrator 실험 처리
**결정**: **Frontend에서 Group 선택 필수**

**구현**:
- Tag Lab UI에 Group 선택 드롭다운 추가
- 기본값: 사용자의 첫 번째 Group
- Character 선택 시 해당 Character의 Project → Groups 필터링

### 3. 기존 데이터
**결정**: 테스트 데이터 (마이그레이션 실패 시 삭제 가능)

**백업 계획**:
```sql
-- 마이그레이션 전 백업 (선택)
CREATE TABLE lab_experiments_backup AS
SELECT * FROM lab_experiments;
```

### 4. Analytics 요구사항
**결정**: **Group별 집계 필요** (인덱스 추가)

**쿼리 예시**:
```sql
-- Group별 평균 Match Rate
SELECT
    g.name,
    COUNT(le.id) AS total_experiments,
    AVG(le.match_rate) AS avg_match_rate
FROM lab_experiments le
JOIN groups g ON le.group_id = g.id
WHERE le.status = 'completed'
GROUP BY g.id, g.name
ORDER BY avg_match_rate DESC;
```

---

## Phase 1: Tag Lab 통합 (우선순위 P0)

### 1.1 Core 모듈 생성

**파일**: `backend/services/image_generation_core.py`

```python
"""
Unified image generation core for Lab + Studio.
Provides single source of truth for V3 Prompt Engine + SD integration.
"""

from __future__ import annotations

import base64
import json
from typing import Literal

import httpx
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config import SD_TIMEOUT_SECONDS, SD_TXT2IMG_URL, logger
from services.prompt.v3_composition import V3PromptBuilder


class ImageGenerationResult(BaseModel):
    """Unified response for Lab + Studio image generation."""

    image: str  # base64
    seed: int
    final_prompt: str
    final_negative_prompt: str

    # LoRA metadata
    loras_applied: list[dict] = Field(default_factory=list)
    # [{"name": "...", "weight": 0.7, "source": "character|style", "type": "character|style"}]

    # ControlNet metadata (Studio only)
    controlnet_pose: str | None = None
    ip_adapter_reference: str | None = None
    environment_reference_id: int | None = None

    # Warnings
    warnings: list[str] = Field(default_factory=list)


async def generate_image_with_v3(
    db: Session,
    prompt: str | list[str],
    character_id: int | None = None,
    storyboard_id: int | None = None,
    group_id: int | None = None,
    style_loras: list[dict] | None = None,
    sd_params: dict | None = None,
    controlnet_config: dict | None = None,
    mode: Literal["studio", "lab"] = "studio",
) -> ImageGenerationResult:
    """
    Generate image using V3 Prompt Engine + SD.

    Args:
        db: Database session
        prompt: Tag list (list[str]) or composed prompt (str)
        character_id: Character ID for Character LoRA
        storyboard_id: Storyboard ID for Style Profile (Studio)
        group_id: Group ID for Style Profile (Lab)
        style_loras: Explicit Style LoRA override
        sd_params: SD parameters (steps, cfg_scale, etc)
        controlnet_config: ControlNet/IP-Adapter config (Studio only)
        mode: "studio" or "lab"

    Returns:
        ImageGenerationResult with image, metadata, and warnings
    """
    mode_prefix = "🎬 [Studio]" if mode == "studio" else "🧪 [Lab]"
    logger.info(
        f"{mode_prefix} Generating image: character_id={character_id}, "
        f"group_id={group_id}, storyboard_id={storyboard_id}"
    )

    # 1. Normalize prompt
    if isinstance(prompt, list):
        scene_tags = prompt
        prompt_str = ", ".join(prompt)
        logger.debug(f"{mode_prefix} Prompt type: list[str] → joined")
    else:
        prompt_str = prompt
        scene_tags = _split_prompt_tokens(prompt)
        logger.debug(f"{mode_prefix} Prompt type: str")

    # 2. Resolve Style LoRAs
    if not style_loras:
        if group_id:
            style_loras = resolve_style_loras_from_group(group_id, db)
            logger.debug(f"{mode_prefix} Resolved {len(style_loras)} Style LoRAs from Group {group_id}")
        elif storyboard_id:
            style_loras = resolve_style_loras_from_storyboard(storyboard_id, db)
            logger.debug(f"{mode_prefix} Resolved {len(style_loras)} Style LoRAs from Storyboard {storyboard_id}")
        else:
            style_loras = []
            logger.warning(f"{mode_prefix} No group_id or storyboard_id, skipping Style LoRAs")

    # 3. V3 Composition (Character LoRA + Scene Tags + Style LoRAs)
    warnings = []
    if character_id:
        try:
            builder = V3PromptBuilder(db)
            final_prompt = builder.compose_for_character(
                character_id=character_id,
                scene_tags=scene_tags,
                style_loras=style_loras,
            )
            logger.debug(f"{mode_prefix} V3 composition complete")
        except Exception as e:
            logger.error(f"{mode_prefix} V3 composition failed: {e}")
            if mode == "studio":
                raise
            else:
                # Lab: fallback to prompt without V3
                final_prompt = prompt_str
                warnings.append(f"V3 composition failed: {e}")
    else:
        final_prompt = prompt_str
        logger.debug(f"{mode_prefix} No character_id, using prompt as-is")

    # 4. Apply Style Profile (Quality Tags + Negative)
    negative_prompt = sd_params.get("negative_prompt", "") if sd_params else ""
    if storyboard_id or group_id:
        from services.generation import apply_style_profile_to_prompt
        try:
            final_prompt, negative_prompt = apply_style_profile_to_prompt(
                final_prompt,
                negative_prompt,
                storyboard_id or group_id,
                db,
                skip_loras=True,  # V3 already applied LoRAs
            )
            logger.debug(f"{mode_prefix} Style Profile applied")
        except Exception as e:
            logger.warning(f"{mode_prefix} Style Profile failed: {e}")
            warnings.append(f"Style Profile failed: {e}")

    # 5. Build SD payload
    payload = {
        "prompt": final_prompt,
        "negative_prompt": negative_prompt,
        "steps": sd_params.get("steps", 28) if sd_params else 28,
        "cfg_scale": sd_params.get("cfg_scale", 7.0) if sd_params else 7.0,
        "sampler_name": sd_params.get("sampler", "DPM++ 2M Karras") if sd_params else "DPM++ 2M Karras",
        "width": sd_params.get("width", 512) if sd_params else 512,
        "height": sd_params.get("height", 768) if sd_params else 768,
        "seed": sd_params.get("seed", -1) if sd_params else -1,
    }

    # 6. Apply ControlNet/IP-Adapter (Studio only)
    if mode == "studio" and controlnet_config:
        # TODO: Integrate ControlNet/IP-Adapter logic
        pass

    # 7. Call SD API
    try:
        async with httpx.AsyncClient(timeout=SD_TIMEOUT_SECONDS) as client:
            resp = await client.post(SD_TXT2IMG_URL, json=payload)

        if resp.status_code != 200:
            msg = f"SD API error: {resp.status_code}"
            logger.error(f"{mode_prefix} {msg}")
            raise RuntimeError(msg)

        data = resp.json()
        info = json.loads(data.get("info", "{}"))
        resolved_seed = info.get("seed", payload["seed"])

        logger.info(f"{mode_prefix} Image generated successfully (seed={resolved_seed})")

        return ImageGenerationResult(
            image=data["images"][0],
            seed=resolved_seed,
            final_prompt=final_prompt,
            final_negative_prompt=negative_prompt,
            loras_applied=_extract_loras_from_prompt(final_prompt),
            warnings=warnings,
        )

    except Exception as e:
        logger.exception(f"{mode_prefix} SD API call failed")
        if mode == "studio":
            raise
        else:
            # Lab: return partial result
            return ImageGenerationResult(
                image="",
                seed=-1,
                final_prompt=final_prompt,
                final_negative_prompt=negative_prompt,
                warnings=[f"SD API failed: {e}"],
            )


def resolve_style_loras_from_group(group_id: int, db: Session) -> list[dict]:
    """Resolve Style LoRAs from Group Config."""
    from models import LoRA, StyleProfile
    from models.group import Group, GroupConfig

    group = db.query(Group).filter(Group.id == group_id).first()
    if not group or not group.config:
        logger.warning(f"Group {group_id} has no config")
        return []

    config: GroupConfig = group.config
    if not config.style_profile_id:
        logger.warning(f"Group {group_id} has no style_profile_id")
        return []

    profile = db.query(StyleProfile).filter(StyleProfile.id == config.style_profile_id).first()
    if not profile or not profile.loras:
        return []

    result = []
    for lora_config in profile.loras:
        lora_id = lora_config.get("lora_id")
        weight = lora_config.get("weight", 0.7)
        if not lora_id:
            continue
        lora_obj = db.query(LoRA).filter(LoRA.id == lora_id).first()
        if not lora_obj:
            continue
        result.append({
            "name": lora_obj.name,
            "weight": weight,
            "trigger_words": list(lora_obj.trigger_words) if lora_obj.trigger_words else [],
        })

    logger.debug(f"Resolved {len(result)} Style LoRAs from Group {group_id}")
    return result


def resolve_style_loras_from_storyboard(storyboard_id: int, db: Session) -> list[dict]:
    """Resolve Style LoRAs from Storyboard (via Group Config)."""
    from models import Storyboard

    storyboard = db.query(Storyboard).filter(Storyboard.id == storyboard_id).first()
    if not storyboard or not storyboard.group_id:
        logger.warning(f"Storyboard {storyboard_id} has no group_id")
        return []

    return resolve_style_loras_from_group(storyboard.group_id, db)


def _split_prompt_tokens(prompt: str) -> list[str]:
    """Split prompt string into tag tokens."""
    return [t.strip() for t in prompt.split(",") if t.strip()]


def _extract_loras_from_prompt(prompt: str) -> list[dict]:
    """Extract LoRA metadata from final prompt."""
    import re

    loras = []
    pattern = r"<lora:([^:]+):([0-9.]+)>"
    for match in re.finditer(pattern, prompt):
        name = match.group(1)
        weight = float(match.group(2))
        loras.append({
            "name": name,
            "weight": weight,
            "source": "character" if "character" in name.lower() else "style",
        })
    return loras
```

---

### 1.2 DB 마이그레이션

**Alembic 스크립트**: `alembic/versions/XXXX_add_group_id_to_lab_experiments.py`

```python
"""Add group_id and V3 metadata to lab_experiments

Revision ID: XXXX
Revises: YYYY
Create Date: 2026-02-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


def upgrade():
    # 1. Add columns (nullable first)
    op.add_column('lab_experiments',
        sa.Column('group_id', sa.Integer(), nullable=True))
    op.add_column('lab_experiments',
        sa.Column('final_prompt', sa.Text(), nullable=True))
    op.add_column('lab_experiments',
        sa.Column('loras_applied', JSONB(), nullable=True))

    # 2. Migrate existing data: character → project → group
    op.execute("""
        UPDATE lab_experiments le
        SET group_id = (
            SELECT g.id
            FROM groups g
            JOIN characters c ON c.project_id = g.project_id
            WHERE c.id = le.character_id
            ORDER BY g.created_at ASC
            LIMIT 1
        )
        WHERE le.character_id IS NOT NULL
    """)

    # 3. For records without character_id, assign first group
    op.execute("""
        UPDATE lab_experiments
        SET group_id = (SELECT id FROM groups ORDER BY id ASC LIMIT 1)
        WHERE group_id IS NULL
    """)

    # 4. Make group_id NOT NULL
    op.alter_column('lab_experiments', 'group_id', nullable=False)

    # 5. Add FK constraint
    op.create_foreign_key(
        'fk_lab_experiments_group_id',
        'lab_experiments', 'groups',
        ['group_id'], ['id'],
        ondelete='CASCADE'
    )

    # 6. Add indexes
    op.create_index(
        'idx_lab_experiments_group_id',
        'lab_experiments',
        ['group_id']
    )
    op.create_index(
        'idx_lab_experiments_group_status',
        'lab_experiments',
        ['group_id', 'status'],
        postgresql_where=sa.text("status = 'completed'")
    )


def downgrade():
    # Drop in reverse order
    op.drop_index('idx_lab_experiments_group_status')
    op.drop_index('idx_lab_experiments_group_id')
    op.drop_constraint('fk_lab_experiments_group_id', 'lab_experiments')
    op.drop_column('lab_experiments', 'loras_applied')
    op.drop_column('lab_experiments', 'final_prompt')
    op.drop_column('lab_experiments', 'group_id')
```

**실행**:
```bash
cd backend
alembic revision -m "Add group_id and V3 metadata to lab_experiments"
# 위 코드를 생성된 파일에 붙여넣기
alembic upgrade head
```

---

### 1.3 모델 업데이트

**파일**: `backend/models/lab.py`

```python
class LabExperiment(Base, TimestampMixin):
    __tablename__ = "lab_experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # ✅ Group 소속 (필수)
    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Batch ID
    batch_id: Mapped[str | None] = mapped_column(String(50), index=True)

    # Experiment metadata
    experiment_type: Mapped[str] = mapped_column(
        String(20),
        default="tag_render",
        server_default="tag_render"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending"
    )

    # Input
    character_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("characters.id", ondelete="SET NULL"),
        nullable=True
    )
    prompt_used: Mapped[str] = mapped_column(Text)
    negative_prompt: Mapped[str | None] = mapped_column(Text)
    target_tags: Mapped[list[str]] = mapped_column(ARRAY(String))
    sd_params: Mapped[dict | None] = mapped_column(JSON)
    seed: Mapped[int | None] = mapped_column(Integer)
    scene_description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    # ✅ V3 Metadata
    final_prompt: Mapped[str | None] = mapped_column(Text)
    loras_applied: Mapped[dict | None] = mapped_column(JSONB)

    # Output
    match_rate: Mapped[float | None] = mapped_column(Float)
    wd14_result: Mapped[dict | None] = mapped_column(JSON)

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="lab_experiments")
    character: Mapped["Character"] = relationship("Character")
```

---

### 1.4 Lab 서비스 수정

**파일**: `backend/services/lab.py`

```python
async def run_experiment(
    db: Session,
    target_tags: list[str],
    group_id: int,  # ✅ 필수
    character_id: int | None = None,
    negative_prompt: str | None = None,
    sd_params: dict | None = None,
    seed: int | None = None,
    experiment_type: str = "tag_render",
    scene_description: str | None = None,
    notes: str | None = None,
    batch_id: str | None = None,
) -> LabExperiment:
    """Run a single experiment: SD generation -> WD14 validation -> DB record."""
    from services.image_generation_core import generate_image_with_v3

    # Create experiment record
    experiment = LabExperiment(
        group_id=group_id,  # ✅ 필수
        batch_id=batch_id,
        experiment_type=experiment_type,
        status="running",
        character_id=character_id,
        prompt_used=", ".join(target_tags),
        negative_prompt=negative_prompt,
        target_tags=target_tags,
        sd_params=sd_params or {},
        seed=seed,
        scene_description=scene_description,
        notes=notes,
    )
    db.add(experiment)
    db.flush()

    try:
        # ✅ Use unified Core module
        result = await generate_image_with_v3(
            db=db,
            prompt=target_tags,  # list[str]
            character_id=character_id,
            group_id=group_id,
            sd_params={
                "negative_prompt": negative_prompt,
                "seed": seed if seed and seed > 0 else -1,
                **(sd_params or {}),
            },
            mode="lab",
        )

        # Save image
        image_bytes = base64.b64decode(result.image)
        save_experiment_image(experiment.id, image_bytes)

        # WD14 validation (Lab-specific)
        image = Image.open(BytesIO(image_bytes))
        tags = wd14_predict_tags(image)
        comparison = compare_prompt_to_tags(result.final_prompt, tags)
        match_rate = _calc_match_rate(comparison)

        # Update experiment
        experiment.status = "completed"
        experiment.seed = result.seed
        experiment.final_prompt = result.final_prompt  # ✅ V3 메타데이터
        experiment.loras_applied = result.loras_applied  # ✅ LoRA 메타데이터
        experiment.match_rate = match_rate
        experiment.wd14_result = _build_wd14_result(comparison, tags)

    except Exception as e:
        logger.error("[Lab] Experiment %s failed: %s", experiment.id, e)
        experiment.status = "failed"
        experiment.notes = (experiment.notes or "") + f"\nError: {e}"

    db.commit()
    return experiment
```

---

### 1.5 API 스키마 업데이트

**파일**: `backend/schemas_lab.py`

```python
class LabExperimentRunRequest(BaseModel):
    """Lab experiment run request."""
    target_tags: list[str] = Field(..., min_length=1)
    group_id: int  # ✅ 필수
    character_id: int | None = None
    negative_prompt: str | None = None
    sd_params: dict | None = None
    seed: int | None = None
    notes: str | None = None
    experiment_type: str = "tag_render"
    scene_description: str | None = None


class LabExperimentResponse(BaseModel):
    """Lab experiment response with V3 metadata."""
    id: int
    group_id: int  # ✅ 추가
    character_id: int | None
    experiment_type: str
    status: str

    # Input
    prompt_used: str
    target_tags: list[str]
    seed: int | None

    # ✅ V3 Metadata
    final_prompt: str | None
    loras_applied: list[dict] = Field(default_factory=list)

    # Output
    match_rate: float | None
    wd14_result: dict | None

    # Warnings
    warnings: list[str] = Field(default_factory=list)

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

---

### 1.6 테스트

**파일**: `backend/tests/services/test_image_generation_core.py`

```python
import pytest
from services.image_generation_core import generate_image_with_v3


@pytest.mark.asyncio
async def test_generate_image_lab_mode_with_character(db):
    """Lab mode: list[str] prompt + character LoRA."""
    result = await generate_image_with_v3(
        db=db,
        prompt=["1girl", "long_hair", "school_uniform"],
        character_id=1,
        group_id=1,
        mode="lab",
    )

    assert result.image
    assert result.seed > 0
    assert result.final_prompt
    assert "1girl" in result.final_prompt
    assert "<lora:" in result.final_prompt  # Character LoRA applied
    assert len(result.loras_applied) > 0
    assert any(lora["source"] == "character" for lora in result.loras_applied)


@pytest.mark.asyncio
async def test_generate_image_lab_mode_narrator(db):
    """Lab mode: Narrator (no character) with Style LoRA from Group."""
    result = await generate_image_with_v3(
        db=db,
        prompt=["sunset", "mountain", "dramatic_lighting"],
        character_id=None,
        group_id=1,
        mode="lab",
    )

    assert result.image
    assert result.final_prompt
    # Should have Style LoRAs from Group Config
    assert len(result.loras_applied) > 0 or len(result.warnings) > 0


@pytest.mark.asyncio
async def test_resolve_style_loras_from_group(db):
    """Test Style LoRA resolution from Group Config."""
    from services.image_generation_core import resolve_style_loras_from_group

    loras = resolve_style_loras_from_group(group_id=1, db=db)

    assert isinstance(loras, list)
    if loras:
        assert "name" in loras[0]
        assert "weight" in loras[0]
        assert "trigger_words" in loras[0]
```

---

## Phase 2: Scene Lab 통합 (우선순위 P1)

**목표**: Gemini 프롬프트 생성 로직 재사용

**변경 파일**: `backend/services/lab.py`

```python
async def compose_and_run(
    db: Session,
    scene_description: str,
    character_id: int,
    group_id: int,  # ✅ 추가
    negative_prompt: str | None = None,
    sd_params: dict | None = None,
    seed: int | None = None,
    notes: str | None = None,
) -> LabExperiment:
    """Scene Lab: Gemini composition → V3 → SD → WD14."""
    from services.storyboard import generate_scene_prompt_with_gemini  # TODO: 추출

    # 1. Gemini로 image_prompt 생성 (Studio와 동일)
    gemini_result = await generate_scene_prompt_with_gemini(
        db=db,
        scene_description=scene_description,
        character_id=character_id,
    )

    # 2. V3 Core 사용
    from services.image_generation_core import generate_image_with_v3

    result = await generate_image_with_v3(
        db=db,
        prompt=gemini_result["image_prompt"],  # Gemini 생성 프롬프트
        character_id=character_id,
        group_id=group_id,
        sd_params=sd_params,
        mode="lab",
    )

    # 3. WD14 검증 (기존 로직)
    # ...
```

---

## Phase 3: Studio 마이그레이션 (우선순위 P2, 선택)

**시기**: Phase 1 안정화 후 1주일 검증 완료 시

**변경 파일**: `backend/services/generation.py`

```python
async def _generate_scene_image_with_db(
    request: SceneGenerateRequest,
    db: Session,
) -> dict:
    """Generate scene image (Studio)."""
    from services.image_generation_core import generate_image_with_v3

    result = await generate_image_with_v3(
        db=db,
        prompt=request.prompt,
        character_id=request.character_id,
        storyboard_id=request.storyboard_id,
        sd_params={
            "negative_prompt": request.negative_prompt,
            "steps": request.steps,
            "cfg_scale": request.cfg_scale,
            "sampler": request.sampler,
            "width": request.width,
            "height": request.height,
            "seed": request.seed,
        },
        controlnet_config={
            "use_controlnet": request.use_controlnet,
            "controlnet_weight": request.controlnet_weight,
            # ...
        },
        mode="studio",
    )

    return result.model_dump()
```

---

## 구현 체크리스트

### Phase 1: Tag Lab (예상 2-3일)

**Day 1: Core + DB**
- [ ] `services/image_generation_core.py` 생성
  - [ ] `ImageGenerationResult` 스키마
  - [ ] `generate_image_with_v3()` 함수
  - [ ] `resolve_style_loras_from_group()` 함수
  - [ ] Helper 함수들
- [ ] Alembic 마이그레이션 스크립트 작성
- [ ] `models/lab.py` 업데이트
- [ ] 마이그레이션 실행 (Dev DB)
  ```bash
  alembic upgrade head
  ```

**Day 2: Lab Service + API**
- [ ] `services/lab.py` 수정
  - [ ] `run_experiment()` → Core 호출
  - [ ] `run_batch()` 업데이트
- [ ] `schemas_lab.py` 업데이트
- [ ] `routers/lab.py` 확인 (변경 불필요)
- [ ] 테스트 작성
  - [ ] `tests/services/test_image_generation_core.py`
  - [ ] `tests/services/test_lab.py` 업데이트

**Day 3: 검증 + 문서**
- [ ] 통합 테스트 실행
  ```bash
  /test backend tests/services/test_image_generation_core.py
  /test backend tests/services/test_lab.py
  ```
- [ ] Lab UI 수동 테스트
  - [ ] Group 선택 → Character 선택 → 실험 실행
  - [ ] `final_prompt`에 `<lora:...>` 포함 확인
  - [ ] `loras_applied` 필드 확인
  - [ ] Match Rate 기존 대비 변화 측정
- [ ] 문서 업데이트
  - [ ] `DB_SCHEMA.md`: `lab_experiments` 테이블 업데이트
  - [ ] `REST_API.md`: Lab API 스키마 업데이트

---

### Phase 2: Scene Lab (예상 1-2일)

- [ ] Gemini 함수 추출 (`services/storyboard.py`)
- [ ] `compose_and_run()` 수정
- [ ] 테스트 업데이트
- [ ] Scene Lab UI 테스트

---

### Phase 3: Studio (예상 3-5일, 선택)

- [ ] `_generate_scene_image_with_db()` 수정
- [ ] E2E 테스트 전수 검사
- [ ] VRT 검증
- [ ] Canary Deploy (Feature Flag)

---

## 성공 기준

### Phase 1 완료 조건

| 항목 | 기준 | 검증 방법 |
|------|------|----------|
| **기능** | Tag Lab에서 Character + Style LoRA 모두 적용 | `final_prompt` 확인, `loras_applied` 필드 확인 |
| **성능** | Lab 단일 실험 +1초 이하 오버헤드 | Before/After 벤치마크 |
| **Match Rate** | 기존 대비 10-20% 향상 | 동일 프롬프트 비교 실험 |
| **데이터 무결성** | 기존 3개 레코드 모두 `group_id` 할당 | SQL 쿼리 확인 |
| **테스트 커버리지** | Core 모듈 80% 이상 | pytest coverage 리포트 |

---

## 롤백 계획

### 마이그레이션 롤백
```bash
alembic downgrade -1
```

### 코드 롤백 (Feature Flag)
```python
# config.py
USE_IMAGE_GENERATION_CORE = os.getenv("USE_V3_CORE", "true") == "true"

# lab.py
if USE_IMAGE_GENERATION_CORE:
    result = await generate_image_with_v3(...)
else:
    image_b64, seed = await _generate_image(...)  # 기존 로직
```

---

## 참고 문서

- `docs/03_engineering/architecture/DB_SCHEMA.md`
- `docs/03_engineering/api/REST_API.md`
- `docs/03_engineering/backend/PROMPT_SPEC_V2.md`
- CLAUDE.md (설정 SSOT 원칙, Lab 목적)

---

## 리뷰 이력

- **2026-02-08**: Tech Lead, Backend Dev, DBA 리뷰 완료
- **2026-02-08**: 설계 결정 확정 (group_id 필수, Analytics 인덱스 등)

---

## 다음 단계

✅ **Phase 1 구현 시작** (예상 2-3일)

1. Core 모듈 생성 (`image_generation_core.py`)
2. DB 마이그레이션 실행
3. Lab 서비스 수정
4. 테스트 작성 및 검증

**시작 명령**:
```bash
cd /Users/tomo/Workspace/shorts-producer/backend

# 1. 마이그레이션 생성
alembic revision -m "Add group_id and V3 metadata to lab_experiments"

# 2. Core 모듈 생성
touch services/image_generation_core.py

# 3. 테스트 파일 생성
touch tests/services/test_image_generation_core.py
```
