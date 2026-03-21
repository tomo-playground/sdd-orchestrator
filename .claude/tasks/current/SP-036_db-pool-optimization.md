---
id: SP-036
priority: P0
scope: backend
branch: feat/SP-036-db-pool-optimization
created: 2026-03-21
status: running
depends_on:
label: bug
assignee: stopper2008
---

## 무엇을
SQLAlchemy DB Connection Pool 최적화 — stale connection 방지

## 왜
- pool_recycle, pool_pre_ping 미설정 → 장시간 운영 시 "connection closed" 에러 발생 가능
- pool_size 기본값(5) → 동시 요청 + 파이프라인 + 배경 작업 시 부족 가능

## 수정 범위
`backend/database.py`의 create_engine에 pool 옵션 추가:
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    pool_pre_ping=True,
)
```

## 완료 기준 (DoD)
- [ ] pool_size=10, pool_recycle=1800, pool_pre_ping=True 적용
- [ ] 기존 테스트 통과
- [ ] 장시간 운영 후 connection 에러 미발생
