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

## Setup Wizard

> 상태: 미착수

### 배경
초기 설정(SD WebUI 연결, 모델 확인, 에셋 상태)을 안내하는 UI 부재.

### 목표
- 첫 실행 시 필수 설정 가이드 제공
- SD WebUI 연결, 모델/LoRA 존재 확인, DB 상태 점검

### 수락 기준
- [ ] 첫 실행 시 Wizard 자동 표시
- [ ] SD WebUI 연결 상태 확인
- [ ] 필수 에셋 존재 여부 점검
