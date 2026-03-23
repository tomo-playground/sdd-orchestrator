---
id: SP-020
priority: P1
scope: fullstack
branch: feat/SP-020-enum-id-normalization
created: 2026-03-23
status: pending
depends_on:
label: enhancement
assignee: stopper2008
---

## 무엇을 (What)
Structure/Language 필드의 디스플레이 이름(`"Monologue"`, `"Korean"`)을 정규화된 ID(`"monologue"`, `"korean"`)로 통일한다. DB 마이그레이션 포함.

## 왜 (Why)
- 디스플레이 이름이 데이터 ID로 사용되는 안티패턴 → `"narrated_dialogue"` vs `"narrated dialogue"` vs `"Narrated Dialogue"` 포맷 불일치
- 방어적 정규화(`.lower().replace("_", " ")`)가 47+ 파일에 산재
- 실제 버그 발생: Narrator 씬에 "Actor A" 표시 (SP-072에서도 연관), TTS language 불일치
- SP-021(Speaker 동적 역할)의 선행 태스크

## 완료 기준 (DoD)

### A. config.py SSOT 정의
- [ ] `STRUCTURES` = `[{id, label}]` 리스트 정의 (monologue, dialogue, narrated_dialogue, confession)
- [ ] `DEFAULT_STRUCTURE = "monologue"` (snake_case)
- [ ] `MULTI_CHAR_STRUCTURES = frozenset({"dialogue", "narrated_dialogue"})`
- [ ] `LANGUAGES` = `[{id, label}]` 리스트 정의 (korean, english, japanese)
- [ ] `DEFAULT_LANGUAGE = "korean"` (lowercase)
- [ ] 중복 상수 제거: `_DIALOGUE_STRUCTURES`, `_TWO_CHAR_STRUCTURES` (2곳) → config SSOT 참조

### B. Backend 코드 정규화
- [ ] `.lower().replace("_", " ")` 패턴 전수 제거 (직접 `==` 비교)
- [ ] `normalize_structure()` 함수 제거
- [ ] `coerce_structure_id()` 함수가 레거시 포맷을 ID로 변환 (후방 호환)
- [ ] Prompt builders: Title Case 비교 → snake_case 비교
- [ ] presets.py: 프리셋 정의 ID 통일

### C. DB 마이그레이션
- [ ] `storyboards.structure` 컬럼: Title Case → snake_case 일괄 UPDATE
- [ ] `storyboards.language` 컬럼: Title Case → lowercase 일괄 UPDATE
- [ ] Alembic 마이그레이션 파일 생성 (reversible)

### D. Frontend 동기화
- [ ] `DEFAULT_STRUCTURE` 상수 제거 (API에서 수신)
- [ ] structure 비교 로직 정규화 (이미 `isMultiCharStructure()`에 방어 있음 — 확인)

### E. LangFuse 프롬프트 검사
- [ ] 프롬프트 본문에 `"Monologue"`, `"Korean"` 등 리터럴 존재 시 업데이트

### F. 테스트
- [ ] Structure 관련 테스트 하드코딩 문자열 업데이트 (~158건)
- [ ] Language 관련 테스트 하드코딩 문자열 업데이트 (~135건)
- [ ] 기존 테스트 regression 없음
- [ ] 린트 통과

## 참조
- [상세 명세](../../docs/01_product/FEATURES/ENUM_ID_NORMALIZATION.md)
