# Technical Debt 모음

> 리팩토링/기술 부채 태스크를 묶어서 관리

## Hook Extraction

> 상태: 부분 완료

### 배경
`useManageState` 등 대형 커스텀 훅이 컴포넌트에 인라인으로 존재.

### 목표
- 커스텀 훅을 독립 파일로 분리
- 테스트 가능한 단위로 격리

### 수정 대상
- `app/manage/` 내 상태 관리 로직 → `hooks/useManageState.ts`
- 기타 인라인 훅 식별 및 분리

---

## Common UI Toolkit

> 상태: 미착수

### 배경
버튼, 인풋, 모달 등 공통 컴포넌트가 각 페이지에 중복 구현.

### 목표
- 재사용 가능한 공통 컴포넌트 라이브러리화
- 일관된 디자인 시스템 적용

### 범위
- Button, Input, Modal, Toast, Badge 등 기본 UI 요소
- `app/components/ui/` 디렉토리

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
