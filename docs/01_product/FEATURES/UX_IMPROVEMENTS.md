# UX 개선 모음

> 소규모 UX 개선 태스크를 묶어서 관리

## 간소화 진입점 재설계 (Quick Start Flow)

> 상태: **완료** (7-1 #1)

### 구현 완료 사항
- +New Story Lazy Creation: 첫 Save/Generate 시 DB 저장 (불필요한 빈 스토리보드 방지)
- PlanTab 설정/스토리 재설계
- 인라인 StyleProfile 셀렉터

### 수락 기준
- [x] 3단계 이내로 영상 생성 시작 가능
- [x] 기존 Custom Start와 공존

---

## ~~Setup Wizard~~ — N/A (2026-02-13)

> 상태: **취소** — 기존 기능으로 대체됨

후속 개발에서 개별적으로 더 나은 형태로 구현 완료:
- **ConnectionGuard** (7-5): Backend 연결 끊기면 전면 차단 UI
- **MaterialsCheck + Preflight** (7-5): 렌더 전 5개 항목 자동 검증
- **Style Profile Onboarding** (7-1): 새 스토리보드 진입 시 자동 안내
- 남은 갭(SD WebUI 상태 표시)은 Feature Backlog 소항목으로 이동
