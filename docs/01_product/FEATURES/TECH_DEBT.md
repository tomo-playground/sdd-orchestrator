# Technical Debt 모음

> 리팩토링/기술 부채 태스크를 묶어서 관리

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

> 상태: 미착수 (Nice-to-Have)

### 배경
V3 12-Layer Prompt Builder에서 레이어 간 동일 태그 중복 출력.
`_flatten_layers`의 `seen` set이 레이어별로 초기화되어 발생.

### 고려사항
- 레이어 간 중복이 의도적 강조 효과일 수 있음
- 제거 시 레이어 우선순위 전략 필요 (상위 레이어 보존)
- `BREAK` 구분자 전후 중복은 SD 특성상 별도 처리 필요

### 수정 대상
- `backend/services/prompt/v3_composition.py`
