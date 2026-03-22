---
id: SP-056
priority: P1
scope: fullstack
branch: feat/SP-056-structure-confession-tone
created: 2026-03-22
status: done
approved_at: 2026-03-23
depends_on:
label: feat
---

## 무엇을 (What)
confession structure를 제거하고 tone 시스템을 도입하여, structure(파이프라인 분기)와 tone(프롬프트 분위기)을 분리한다.

## 왜 (Why)
confession은 monologue와 파이프라인 동작이 동일하고 LangFuse 프롬프트 톤만 다르다. structure는 "파이프라인이 다르게 동작하는 분기점"이어야 하는데, confession은 이 기준에 맞지 않는다. tone을 별도 축으로 분리하면 structure x tone 조합이 가능해진다 (예: dialogue + humorous).

## 완료 기준 (DoD)

### confession 제거
- [x] `config.py` STRUCTURE_METADATA에서 confession 항목 제거 (3종: monologue, dialogue, narrated_dialogue)
- [x] `presets.py` confession 프리셋 제거 또는 monologue + emotional 매핑으로 전환
- [x] `coerce_structure_id()`가 "confession" 입력 시 "monologue" 반환 (하위 호환)
- [x] confession 참조 테스트 케이스를 monologue + emotional로 갱신

### tone 시스템 추가
- [x] `config.py`에 `ToneMeta` 데이터클래스 + `TONE_METADATA` 정의 (intimate, emotional, dynamic, humorous, suspense)
- [x] `storyboards` 테이블에 `tone: String(30), default="intimate"` 컬럼 추가 (Alembic 마이그레이션)
- [x] Storyboard ORM 모델에 `tone` 필드 추가
- [x] `/presets` API 응답에 `tones` 목록 포함
- [x] Writer 노드에서 tone 값을 LangFuse 프롬프트 변수로 주입

### DB 마이그레이션
- [x] `storyboards.structure = 'confession'` → `'monologue'` + `tone = 'emotional'` 데이터 마이그레이션
- [x] 기존 non-confession 스토리보드는 `tone = 'intimate'` (기본값)

### 품질 게이트
- [x] 기존 테스트 regression 없음
- [x] 린트 통과

## 영향 분석
- `backend/config.py` — StructureMeta, STRUCTURE_METADATA, 파생 상수
- `backend/services/presets.py` — PRESETS dict
- `backend/models/storyboard.py` — tone 필드 추가
- `backend/alembic/` — 마이그레이션 스크립트
- `backend/services/agent/nodes/writer.py` — tone 변수 주입
- `backend/services/agent/prompt_builders_writer.py` — tone 반영
- `backend/schemas.py` — Storyboard 스키마에 tone 추가
- `docs/03_engineering/architecture/DB_SCHEMA.md` — tone 컬럼 문서화

## 제약 (Boundaries)
- LangFuse `storyboard/confession` 프롬프트 내용은 보존 (tone=emotional 조건으로 활용)
- structure 3종 외 추가 금지 (이 태스크 범위)
- tone 목록은 config.py SSOT, 확장 가능한 구조로 설계

## 상세 설계 (How)
> [design.md](./design.md) 참조 (착수 시 작성)
