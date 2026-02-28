# Technical Debt 모음

> 상태: 완료 | 리팩토링/기술 부채 태스크를 묶어서 관리

## Hook Extraction

> 상태: **완료** (Phase 6-7 #9)

### 구현 완료 사항
- Manage 페이지: 5개 탭 커스텀 Hook 분리 (`manage/hooks/` 12파일)
- Studio: `useStudioInitialization`, `useStudioOnboarding` 등 11개 독립 Hook
- 테스트 가능한 단위로 격리 완료

---

## Common UI Toolkit

> 상태: **완료** (Phase 6-7 #7-8)

### 구현 완료 사항
- `app/components/ui/` 디렉토리: Button, Modal, ConfirmDialog, Toast, Badge, Popover, TagAutocomplete 등 16개 공통 컴포넌트
- z-index 통합 관리 (Tailwind 설정, `constants/index.ts`에서 Z_INDEX 관리)
- 일관된 디자인 시스템 적용

---

## Inter-Layer Prompt Deduplication

> 상태: **완료** (이미 구현됨, 2026-02-23 확인)

### 결론
`_flatten_layers()`의 `global_seen: set[str]`이 12-Layer **전체**를 관통하며 중복 제거 수행.
TECH_DEBT 작성 당시의 "레이어별 초기화" 문제는 이미 해결됨.

### 구현 현황
- `global_seen` set: 한 번 초기화, 전 레이어 유지 (v3_composition.py:801)
- `_dedup_key()`: 가중치/LoRA/공백 정규화 후 비교
- `TagRuleCache.is_conflicting()`: 의미 충돌 검사 (brown_hair vs blonde_hair)
- `_distribute_tags()`: exclusive group(hair_color 등) 캐릭터 우선 사전 필터링
- BREAK 미사용: 단일 attention context로 통합
