# Backlog

> 태스크 큐. 우선순위 순서대로 진행.
> 코딩머신이 이 파일을 스캔하여 자동 실행.

---

## P0 (진행 중)

- [ ] SP-077 — SD Client 추상화 — SD WebUI 직접 호출 24곳 → SDClientBase 통합 (ComfyUI 전환 선행) | scope: backend
- [x] ~~SP-058~~ — Intake 노드 — Guided 모드 소크라테스 질문으로 structure/tone/캐릭터 확정 | scope: backend | **approved**
- [x] ~~SP-072~~ — Narrator 씬 지능형 no_humans 판단 — script 의미 기반 군중/빈 공간 구분 | scope: backend | **approved**
- [x] ~~SP-074~~ — Frontend 하드코딩 SSOT 전환 | scope: frontend | **approved**
- [ ] SP-020 — Enum ID 정규화 — structure/language/style ID 분리 + DB 마이그레이션 | scope: backend

## P1 (최우선)

- [ ] SP-022 — ComfyUI 마이그레이션 — ForgeUI→ComfyUI 워크플로우 전환 | depends: SP-077
- [ ] SP-021 — Speaker 동적 역할 — 정적 A/B/Narrator → speaker_1/speaker_2/narrator 전환 | depends: SP-020
- [ ] SP-075 — 지식DB 스토리 카드 | scope: backend
- [ ] SP-023 — 캐릭터 일관성 V3 — ComfyUI 전환 후 착수. 4-Module 파이프라인 | depends: SP-022
- [x] ~~SP-076~~ — Slack Bot 양방향 연동 — Slack에서 명령 수신 + 코딩머신 제어 | scope: infra
- [ ] SP-080 — 자동 롤백 — 머지 후 5분 내 Sentry 에러 급증 시 자동 revert PR 생성 | scope: infra
- [ ] SP-078 — 학습 루프 — 실패 PR 원인 기록 + 다음 설계 자동 반영 (같은 실수 반복 방지) | scope: infra
- [ ] SP-079 — 자기 평가 대시보드 — 태스크 소요 시간, self-heal 횟수, 리뷰 라운드 수 추적 → Slack 주간 리포트 | scope: infra
- [ ] SP-070 — 옵저버빌리티 구멍 메우기 | scope: infra

## P2 (기능 확장)

- [ ] SP-081 — 서비스 Slack 알림 — 렌더링 완료/파이프라인 실패/SD 다운/스토리보드 생성 완료 알림 | scope: backend+infra
- [ ] SP-082 — Slack Bot 자연어 명령 — Ollama(3B) 의도 분류 + 키워드 매칭 폴백 | scope: infra
- [ ] SP-052 — Direct 탭 레이아웃/편의성 개선
- [ ] SP-024 — VEO Clip — Video Generation 통합
- [ ] SP-025 — Profile Export/Import — Style Profile 공유
- [ ] SP-026 — Storyboard Version History — 저장 시점별 스냅샷 조회/복원
- [ ] SP-029 — Script Canvas 분할 뷰

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

---

## 완료 이력

- [x] ~~SP-011~~ | ~~SP-014~~ | ~~SP-015~~ | ~~SP-016~~ | ~~SP-035~~ | ~~SP-036~~ | ~~SP-039~~ (P0 버그)
- [x] ~~SP-010~~ | ~~SP-017~~ | ~~SP-018~~ | ~~SP-030~~ | ~~SP-031~~ | ~~SP-032~~ | ~~SP-037~~ (P1 인프라)
- [x] ~~SP-019~~ | ~~SP-038~~ | ~~SP-040~~ | ~~SP-041~~ | ~~SP-042~~ | ~~SP-043~~
- [x] ~~SP-044~~ | ~~SP-045~~ | ~~SP-027~~ | ~~SP-046~~ | ~~SP-047~~ | ~~SP-048~~
- [x] ~~SP-054~~ | ~~SP-055~~ | ~~SP-060~~ | ~~SP-056~~ | ~~SP-057~~ | ~~SP-028~~
- [x] ~~SP-059~~ | ~~SP-061~~ | ~~SP-062~~ | ~~SP-063~~ | ~~SP-064~~ | ~~SP-065~~ | ~~SP-053~~ | ~~SP-071~~
- [x] ~~SP-066~~ | ~~SP-067~~ | ~~SP-068~~ | ~~SP-069~~ | ~~SP-073~~
