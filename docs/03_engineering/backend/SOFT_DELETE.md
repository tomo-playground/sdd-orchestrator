# Soft Delete 기술 설계

> 기능 명세: [FEATURES/SOFT_DELETE.md](../../01_product/FEATURES/SOFT_DELETE.md)

## 1. SoftDeleteMixin

`backend/models/base.py`의 기존 `TimestampMixin` 옆에 추가:

```python
class SoftDeleteMixin:
    """Soft delete support. deleted_at이 NOT NULL이면 삭제된 레코드."""
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None, index=True
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
```

적용 모델: `Storyboard`, `Character`, `PromptHistory`

---

## 2. 엔드포인트 변경

### Storyboard 기준 (Character, PromptHistory 동일 패턴)

| 동작 | Method | Endpoint | 설명 |
|------|--------|----------|------|
| Soft Delete | `DELETE` | `/{id}` | `deleted_at = now()` |
| 목록 조회 | `GET` | `/` | `deleted_at IS NULL` 필터 (기본) |
| 휴지통 | `GET` | `/trash` | `deleted_at IS NOT NULL` 필터 |
| 복원 | `POST` | `/{id}/restore` | `deleted_at = NULL` |
| 영구 삭제 | `DELETE` | `/{id}/permanent` | 기존 hard delete 로직 |

### 쿼리 패턴

```python
# 기본 조회
db.query(Storyboard).filter(Storyboard.deleted_at.is_(None))

# 휴지통
db.query(Storyboard).filter(Storyboard.deleted_at.isnot(None))

# 복원
storyboard.deleted_at = None
db.commit()
```

### CASCADE 동작

- Soft delete 시 하위 Scene **삭제하지 않음** (부모 필터로 자동 제외)
- 복원 시 하위 데이터 그대로 복원
- 영구 삭제 시에만 기존 CASCADE + Asset cleanup 실행

---

## 3. Alembic Migration

```python
def upgrade():
    op.add_column('storyboards', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('characters', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('prompt_histories', sa.Column('deleted_at', sa.DateTime(), nullable=True))

    op.create_index('ix_storyboards_deleted_at', 'storyboards', ['deleted_at'])
    op.create_index('ix_characters_deleted_at', 'characters', ['deleted_at'])
    op.create_index('ix_prompt_histories_deleted_at', 'prompt_histories', ['deleted_at'])

def downgrade():
    op.drop_index('ix_prompt_histories_deleted_at')
    op.drop_index('ix_characters_deleted_at')
    op.drop_index('ix_storyboards_deleted_at')

    op.drop_column('prompt_histories', 'deleted_at')
    op.drop_column('characters', 'deleted_at')
    op.drop_column('storyboards', 'deleted_at')
```

---

## 4. 수정 파일

### Backend

| 파일 | 변경 |
|------|------|
| `models/base.py` | `SoftDeleteMixin` 추가 |
| `models/storyboard.py` | Mixin 상속 |
| `models/character.py` | Mixin 상속 |
| `models/prompt_history.py` | Mixin 상속 |
| `routers/storyboard.py` | soft delete + trash/restore/permanent |
| `routers/characters.py` | soft delete + trash/restore/permanent |
| `routers/prompt_histories.py` | soft delete + trash/restore/permanent |
| `schemas.py` | `deleted_at` 필드 추가 |
| `alembic/versions/` | 마이그레이션 생성 |

### Frontend

| 파일 | 변경 |
|------|------|
| `app/types/index.ts` | `deleted_at` 타입 추가 |
| `app/manage/` | Trash 탭 컴포넌트 |
| `app/store/` | restore, permanentDelete 액션 |
