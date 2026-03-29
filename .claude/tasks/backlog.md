# Backlog

> 미착수 태스크 큐. 우선순위 순서대로 진행.
> 착수 → `current/`로 이동 (이 파일에서 제거). 완료 → `done/`이 SSOT.

---

## P0 (긴급)

- [x] SP-115 — 배경/캐릭터 분리 IP-Adapter 파이프라인 통합 → `current/` 착수

## P1 (최우선)

- [ ] SP-085 — 코딩 엔진 통합 — sdd-run/sdd-fix/sentry-autofix를 단일 엔진 + 모드 구조로 리팩토링 (범용 분리 준비) | scope: infra
- [ ] SP-078 — 학습 루프 — 실패 PR 원인 기록 + 다음 설계 자동 반영 (같은 실수 반복 방지) | scope: infra
- [ ] SP-079 — 자기 평가 대시보드 — 태스크 소요 시간, self-heal 횟수, 리뷰 라운드 수 추적 → Slack 주간 리포트 | scope: infra
- [ ] SP-070 — 옵저버빌리티 구멍 메우기 | scope: infra

## P2 (기능 확장)

- [ ] SP-117 — v-pred → epsilon 체크포인트 전환 — v-pred 배경 파란빛 이슈 해결. NoobAI XL epsilon 1.1로 전환, CFG/워크플로우 조정 | scope: backend
- [ ] SP-116 — IP-Adapter 파라미터 서버 자동화 — weight 슬라이더 제거, 캐릭터 preset weight 서버 자동 적용, 토글도 서버 자동 판단으로 전환 | scope: frontend+backend | depends: SP-115

- [ ] SP-081 — 서비스 Slack 알림 — 렌더링 완료/파이프라인 실패/SD 다운/스토리보드 생성 완료 알림 | scope: backend+infra
- [ ] SP-024 — VEO Clip — Video Generation 통합
- [ ] SP-025 — Profile Export/Import — Style Profile 공유
- [ ] SP-026 — Storyboard Version History — 저장 시점별 스냅샷 조회/복원
- [ ] SP-029 — Script Canvas 분할 뷰

## IA Redesign (정보 구조 개선)

> 명세: `docs/01_product/FEATURES/IA_REDESIGN.md`

### Phase A: Quick Wins (병렬, 1~2일)
- [ ] SP-089 — Materials 팝오버 Library 직접 링크 — Characters/Style Missing 시 Library 이동 | scope: frontend

### Phase B: 중규모 (병렬, 1~2주)
- [ ] SP-090 — ContextBar 개선 — h-8→h-10, 아이콘, Library/Settings 숨기기, 단일 채널 자동 숨기기 | scope: frontend

### Phase C: Direct 3패널 ✅ 완료 (SP-094~098)

### Phase D: Library 통일 — SP-099, SP-100, SP-102 완료

## P2-SDD (코딩머신 강화)

- [ ] SP-114 — SDD Orchestrator PyPI 배포 — 안정화 후 `pip install sdd-orchestrator`로 설치 가능하게 패키징. PyPI 퍼블리시 + npm wrapper(`npx @tomo/sdd-kit init`) + 프로젝트 타입별 프리셋 | scope: infra
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
