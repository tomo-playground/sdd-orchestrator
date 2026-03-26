# Backlog

> 미착수 태스크 큐. 우선순위 순서대로 진행.
> 착수 → `current/`로 이동 (이 파일에서 제거). 완료 → `done/`이 SSOT.

---

## P0 (진행 중)


## P1 (최우선)

- [ ] SP-023 — 캐릭터 일관성 V3 — ComfyUI 네이티브 기반 4-Module 파이프라인 | depends: SP-084
- [ ] SP-085 — 코딩 엔진 통합 — sdd-run/sdd-fix/sentry-autofix를 단일 엔진 + 모드 구조로 리팩토링 (범용 분리 준비) | scope: infra
- [ ] SP-078 — 학습 루프 — 실패 PR 원인 기록 + 다음 설계 자동 반영 (같은 실수 반복 방지) | scope: infra
- [ ] SP-079 — 자기 평가 대시보드 — 태스크 소요 시간, self-heal 횟수, 리뷰 라운드 수 추적 → Slack 주간 리포트 | scope: infra
- [ ] SP-070 — 옵저버빌리티 구멍 메우기 | scope: infra

## P2 (기능 확장)

- [ ] SP-081 — 서비스 Slack 알림 — 렌더링 완료/파이프라인 실패/SD 다운/스토리보드 생성 완료 알림 | scope: backend+infra
- [ ] SP-024 — VEO Clip — Video Generation 통합
- [ ] SP-025 — Profile Export/Import — Style Profile 공유
- [ ] SP-026 — Storyboard Version History — 저장 시점별 스냅샷 조회/복원
- [ ] SP-029 — Script Canvas 분할 뷰

## IA Redesign (정보 구조 개선)

> 명세: `docs/01_product/FEATURES/IA_REDESIGN.md`

### Phase A: Quick Wins (병렬, 1~2일)
- [ ] SP-104 — UI 라벨 한국어화 + Dev 제거 — NavBar/Studio/Library/Settings 전체 한국어화 (13~15파일, 문자열 교체) | scope: frontend
- [ ] SP-088 — Ghost Route/컴포넌트 삭제 — /scripts, /storyboards redirect + AppMobileTabBar 삭제 | scope: frontend
- [ ] SP-089 — Materials 팝오버 Library 직접 링크 — Characters/Style Missing 시 Library 이동 | scope: frontend

### Phase B: 중규모 (병렬, 1~2주)
- [ ] SP-090 — ContextBar 개선 — h-8→h-10, 아이콘, Library/Settings 숨기기, 단일 채널 자동 숨기기 | scope: frontend
- [ ] SP-091 — Settings 재배치: Trash → Library 이동 | scope: frontend
- [ ] SP-092 — Publish 탭에 YouTube 연동 진입점 추가 | scope: frontend
- [ ] SP-093 — Home 대시보드 개선 — 빠른 시작 + ContinueWorking 진행 상태 | scope: frontend

### Phase C: Direct 3패널 (순차, 2~3주) — 크리티컬 패스: SP-021 완료 필요
- [ ] SP-094 — Direct 탭 E2E 테스트 보강 — Phase C 리팩토링 전 안전망 | scope: frontend
- [ ] SP-095 — SceneContext Provider 도입 — 기존 SceneContext.tsx 활성화 + TTS 4필드 추가 | scope: frontend | depends: SP-021
- [ ] SP-096 — Props → Context 전환 — SceneCard props 40개→5개, 서브컴포넌트 Context 소비 | scope: frontend | depends: SP-095
- [ ] SP-097 — 속성 패널 컴포넌트 — 기본/고급 분리, 독립 컴포넌트 | scope: frontend | depends: SP-096
- [ ] SP-098 — Direct 3패널 레이아웃 통합 — 씬 목록|씬 카드|속성 패널 + feature flag | scope: frontend | depends: SP-096, SP-097

### Phase D: Library 통일 (1~2주)
- [ ] SP-099 — Master-Detail 공통 레이아웃 컴포넌트 — LibraryMasterDetail 신규 | scope: frontend
- [ ] SP-100 — Styles → Master-Detail 전환 | scope: frontend | depends: SP-099
- [ ] SP-101 — Voices → Master-Detail 전환 | scope: frontend | depends: SP-099
- [ ] SP-102 — Music → Master-Detail 전환 | scope: frontend | depends: SP-099
- [ ] SP-103 — LoRAs 탭 제거 + Admin 이전 | scope: frontend | depends: SP-100

## P2-SDD (코딩머신 강화)

- [ ] SP-033 — DoD 검증 자동화
- [ ] SP-034 — PR 엣지 케이스 체크리스트
- [ ] SP-051 — SDD 2인 확장 플랜

## P3 (인프라/자동화)

- [ ] Tag Intelligence — 채널별 태그 정책 + 데이터 기반 추천
- [ ] Series Intelligence — 에피소드 연결 + 성공 패턴 학습
- [ ] LangFuse SDK v4 + 서버 업그레이드
- [ ] LiteLLM SDK 도입
- [ ] PipelineControl 커스텀 + 분산 큐 (Celery/Redis)
- [ ] 배치 렌더링 + 큐
- [ ] 브랜딩 시스템
- [ ] 분석 대시보드
- [ ] 파이프라인 이상 탐지 자동화
- [ ] PostgreSQL 통합 테스트 인프라
- [ ] 클라우드 TTS/BGM 전환
- [ ] 씬 단위 순차 생성
- [ ] ControlNet 포즈 에셋 재활용 검토
- [ ] 캐릭터 LoRA 학습 파이프라인
