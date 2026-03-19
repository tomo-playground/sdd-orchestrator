## 무엇을
Structure/Language Enum ID 정규화 (Sprint A) — Title Case → snake_case SSOT

## 왜
`"narrated_dialogue"` vs `"Narrated Dialogue"` 불일치로 Narrator 버그 발생. `.lower().replace("_"," ")` 방어 패턴 47+곳 산재.

## 완료 기준 (DoD)
- [x] config.py SSOT (StructureMeta/LanguageMeta + coerce 함수)
- [x] 중복 상수 6곳 → MULTI_CHAR_STRUCTURES 통합
- [x] normalize_structure() 삭제
- [x] .lower().replace 패턴 47+곳 제거
- [x] Agent 노드 14개 + Prompt Builders + Presets + Schemas 정규화
- [x] Frontend 최소 변경 (constants, store, utils)
- [x] 테스트 통과 (3765 passed, 0 failed)
- [x] Frontend build PASS
- [x] Tech Lead 리뷰 PASS
- [x] 기존 regression 없음

## 결과
- 커밋: b890f686, 2de15841, 435ec99f, 6d91b2f4 (main 직접)
- 변경: 376파일, +4,828 / -3,472
- 테스트: coerce 단위 33건 추가, 기존 테스트 6건 수정
- 완료일: 2026-03-19
