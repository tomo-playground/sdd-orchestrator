---
id: SP-012
priority: P1
scope: backend
branch: feat/SP-012-context-tag-soft-validation
created: 2026-03-20
status: done
depends_on:
label: enhancement
assignee: stopper2008
---

## 무엇을
context_tags 검증을 엄격 삭제(whitelist)에서 소프트 통과(prefer)로 전환

## 왜
- SDXL(NoobAI) 모델은 비표준 태그도 상당 수준 이해 가능
- 현재 파이프라인이 Gemini의 풍부한 연출을 Danbooru 필터에서 삭제 → 기본값(standing, looking_at_viewer) 반복 → 영상 단조로움
- 태그 테스트 결과: 비표준 태그가 때로 Danbooru보다 좋은 결과 (씬3 슬픔), 자연어는 분위기 강하지만 텍스트 아티팩트 위험

## 수정 전략
1. **Danbooru alias 매핑 유지**: 표준 태그가 있으면 변환 (더 안정적)
2. **alias 없는 비표준 태그: 삭제 대신 통과**: SDXL이 해석하게 둠
3. **텍스트 아티팩트 블랙리스트**: `talking`, `speech`, `reading` 등 텍스트 유발 태그만 필터

## 관련 파일
- `backend/services/agent/nodes/_context_tag_utils.py` — validate_context_tag_categories() 수정
- `backend/services/agent/nodes/finalize.py` — _inject_default_context_tags() 검토
- `backend/services/keywords/patterns.py` — 패턴 추가 (이미 완료)

## 완료 기준 (DoD)
- [ ] validate에서 비표준 태그 삭제 대신 통과
- [ ] 텍스트 유발 블랙리스트 적용
- [ ] alias 매핑 정상 작동
- [ ] 기존 테스트 통과
- [ ] finalize.py is None / not 정리
