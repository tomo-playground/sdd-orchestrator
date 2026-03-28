# /db Command

DB 마이그레이션 상태 확인 및 관리를 수행하는 원자적 명령입니다.

## 사용법

```
/db [action]
```

### Actions

| Action | 설명 |
|--------|------|
| (없음) | 현재 마이그레이션 버전 및 pending 여부 확인 |
| `migrate <message>` | 새 마이그레이션 생성 (autogenerate) |
| `upgrade` | pending 마이그레이션 적용 (head) |
| `downgrade` | 마지막 마이그레이션 롤백 (-1) |
| `history` | 마이그레이션 히스토리 조회 |
| `schema` | 현재 테이블 목록 및 요약 출력 |

## 실행 내용

### 상태 확인 (기본)
```bash
cd backend && uv run alembic current
cd backend && uv run alembic heads
```

### migrate
```bash
cd backend && uv run alembic revision --autogenerate -m "<message>"
```

### upgrade
```bash
cd backend && uv run alembic upgrade head
```

### downgrade
```bash
cd backend && uv run alembic downgrade -1
```

### history
```bash
cd backend && uv run alembic history --verbose
```

### schema
```bash
cd backend && uv run python -c "
from models.base import Base
for table in sorted(Base.metadata.tables.keys()):
    print(table)
"
```

## 출력 형식

```markdown
## DB 상태

### 현재 버전
- Head: abc123 (add_soft_delete_columns)
- Current: abc123 ✅ (최신)

### 테이블 (15개)
storyboards, scenes, characters, tags, loras, ...

### Pending 마이그레이션
없음
```

## 관련 파일
- `backend/alembic/` - 마이그레이션 디렉토리
- `backend/models/` - SQLAlchemy 모델
- `docs/03_engineering/architecture/DB_SCHEMA.md` - DB 스키마 문서
