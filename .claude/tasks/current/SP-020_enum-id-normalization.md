---
id: SP-020
priority: P1
scope: fullstack
branch: feat/SP-020-enum-id-normalization
created: 2026-03-21
status: pending
depends_on:
label: enhancement
assignee: stopper2008
---

## 무엇을
Structure / Language / Style enum-like 필드의 디스플레이 이름→ID 분리 + DB 마이그레이션

## 왜
- `"Monologue"` vs `"monologue"` 포맷 불일치 → Narrator 씬에 "Actor A" 배지 표시 버그
- 코드 전반에 `structure.lower().replace("_", " ")` 같은 방어적 정규화 난무
- 디스플레이 이름이 DB 저장값으로 사용되는 안티패턴

## 구현 범위
- Sprint A (완료됨): Frontend 컴포넌트 ID 기반 전환
- **Sprint B**: Backend config.py ID 전환 + Alembic 마이그레이션 + 방어적 정규화 코드 제거

## 완료 기준 (DoD)
- [ ] `config.py`의 `DEFAULT_STRUCTURE`, `STORYBOARD_LANGUAGES` 등 ID 기반 전환
- [ ] Alembic 마이그레이션으로 기존 DB 데이터 ID 변환
- [ ] `normalize_structure()`, `.lower().replace("_", " ")` 등 방어 코드 제거
- [ ] Frontend/Backend 양방향 ID 기반 통신 확인
- [ ] 기존 기능 regression 없음 (빌드 + 테스트 통과)

## 제약
- 변경 파일 10개 이하 목표
- 건드리면 안 되는 것: LangFuse 프롬프트 (별도 업데이트)
- DB 마이그레이션 포함 → DBA 리뷰 필수

## 힌트
- 명세: `docs/01_product/FEATURES/ENUM_ID_NORMALIZATION.md`
- Sprint A 완료 이력: `.claude/tasks/done/SP-000_enum-id-normalization-sprint-a.md`
- 관련 파일: `backend/config.py`, `backend/services/presets.py`, `backend/models/storyboard.py`
