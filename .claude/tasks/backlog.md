# Backlog

> 실행 가능한 태스크 큐. 우선순위 순서대로 진행.
> Roadmap(Phase/마일스톤)은 여기에 쓰지 않는다.

---

## 완료

- [x] ~~SP-011~~ | ~~SP-014~~ | ~~SP-015~~ | ~~SP-016~~ | ~~SP-035~~ | ~~SP-036~~ | ~~SP-039~~ (P0 버그)
- [x] ~~SP-010~~ | ~~SP-017~~ | ~~SP-018~~ | ~~SP-030~~ | ~~SP-031~~ | ~~SP-032~~ | ~~SP-037~~ (P1 인프라)
- [x] ~~SP-019~~ (AI QA 순찰) | ~~SP-038~~ (Store resilience) | ~~SP-040~~ (세션 충돌 방지)
- [x] ~~SP-041~~ (SSE heartbeat) | ~~SP-042~~ (LangFuse 트레이스) | ~~SP-043~~ (모델 최적화)
- [x] ~~SP-044~~ (Sentry autofix) | ~~SP-045~~ (autoSave 이미지) | ~~SP-027~~ (Direct 탭 연출 컨트롤)
- [x] ~~SP-046~~ (Cinematographer 팀 분해) | ~~SP-047~~ (Direct 리뷰 후속) | ~~SP-048~~ (Direct UX)
- [x] ~~SP-054~~ (AutoRun 배치 API 제거) | ~~SP-055~~ (TTS/BGM 통일) | ~~SP-060~~ (Voice Preset 캐시)
- [x] ~~SP-056~~ (Structure 재설계 A) | ~~SP-057~~ (모드 단순화) | ~~SP-028~~ (Studio 탭 URI)
- [x] ~~SP-059~~ (multi 씬) | ~~SP-061~~ (대사 품질 L2) | ~~SP-062~~ (프롬프트/태그 검증) | ~~SP-063~~ (렌더링 함수 연결)
- [x] ~~SP-064~~ (Narrative per-scene 평가) | ~~SP-065~~ (렌더링 품질 보강) | ~~SP-053~~ (파이프라인 진행 가시성) | ~~SP-071~~ (대사 구체성 평가)

## P0 (진행 중)

- [ ] SP-066 — SDD 오케스트레이터 Phase 1: 뼈대 — Agent SDK 기반 상주 프로세스, 커스텀 도구, 상태 관리 | scope: infra
- [ ] SP-067 — SDD 오케스트레이터 Phase 2: 자동 실행 — approved 태스크 자동 /sdd-run + PR 모니터링 + 자동 머지 | scope: infra | depends: SP-066
- [ ] SP-068 — SDD 오케스트레이터 Phase 3: 자동 설계 — pending 태스크 자동 설계 + BLOCKER 없으면 자동 승인 | scope: infra | depends: SP-067
- [ ] SP-069 — SDD 오케스트레이터 Phase 4: Sentry + 알림 — Sentry 연동 + Slack 알림 + GHA 제어 통합 | scope: infra | depends: SP-068

## P1 (최우선)

- [ ] SP-070 — 옵저버빌리티 구멍 메우기 — health-check Slack 알림, 크론 실패 알림, Actions 실패 알림, Sentry 실시간 연동 | scope: infra | [가이드](../../docs/04_operations/OBSERVABILITY.md)
- [ ] SP-058 — Structure 재설계 C: Intake 노드 — Guided 모드 소크라테스 질문으로 structure/tone/캐릭터 확정 | [명세](../../docs/01_product/FEATURES/STRUCTURE_SYSTEM_REDESIGN.md) §5 | **approved** | depends: ~~SP-056~~ ✅
- [ ] SP-020 — Enum ID 정규화 — structure/language/style ID 분리 + DB 마이그레이션 | [명세](../../docs/01_product/FEATURES/ENUM_ID_NORMALIZATION.md)
- [ ] SP-021 — Speaker 동적 역할 Phase A — 정적 A/B/Narrator → speaker_1/speaker_2/narrator 전환 | [명세](../../docs/01_product/FEATURES/SPEAKER_DYNAMIC_ROLE.md) | depends: SP-020, ~~SP-056~~ ✅
- [ ] SP-022 — ComfyUI 마이그레이션 — ForgeUI→ComfyUI + SD Client 추상화 | [명세](../../docs/01_product/FEATURES/COMFYUI_MIGRATION.md)
- [ ] SP-023 — 캐릭터 일관성 V3 — ComfyUI 전환 후 착수. 4-Module 파이프라인 | [명세](../../docs/01_product/FEATURES/CHARACTER_CONSISTENCY_V3.md)

## P2 (기능 확장)

- [ ] SP-052 — Direct 탭 레이아웃/편의성 개선 — 씬 카드 빈 공간 활용, 상태 아이콘 가독성, Context Strip sticky, TTS prompt 잘림, 키보드 씬 전환, SceneCard props 분리
- [ ] SP-024 — VEO Clip — Video Generation 통합 | [명세](../../docs/01_product/FEATURES/VEO_CLIP.md)
- [ ] SP-025 — Profile Export/Import — Style Profile 공유 | [명세](../../docs/01_product/FEATURES/PROFILE_EXPORT_IMPORT.md)
- [ ] SP-026 — Storyboard Version History — 저장 시점별 스냅샷 조회/복원
- [ ] SP-029 — Script Canvas 분할 뷰 — 좌 채팅 + 우 씬 프리뷰 | [명세](../../docs/99_archive/features/SCRIPT_COLLABORATIVE_UX.md) §P2

## P2-SDD (SDD 프로세스 개선)

- [ ] SP-033 — DoD 검증 자동화
- [ ] SP-034 — PR 엣지 케이스 체크리스트
- [ ] SP-051 — SDD 2인 확장 플랜 — 설계 리뷰/태스크 관리를 GitHub Issue 기반으로 전환 (로컬→GitHub 마이그레이션 가이드)

## P3 (인프라/자동화)

- [ ] SP-050 — DirectorControlPanel 프리셋 Backend SSOT 전환 — EMOTION_PRESETS/BGM_MOOD_PRESETS 하드코딩 → /presets API 소비

- [ ] Tag Intelligence — 채널별 태그 정책 + 데이터 기반 추천 | [명세](../../docs/01_product/FEATURES/PROJECT_GROUP.md) §3-1
- [ ] Series Intelligence — 에피소드 연결 + 성공 패턴 학습 | [명세](../../docs/01_product/FEATURES/PROJECT_GROUP.md) §3-2
- [ ] LoRA Calibration Automation
- [ ] LangFuse SDK v4 + 서버 업그레이드 — Python SDK 3.14→4.x + 셀프호스팅 서버 동시 업그레이드. CallbackHandler API 변경, OpenTelemetry 기반 전환. interrupt ERROR 이슈는 미해결
- [ ] LiteLLM SDK 도입 — Gemini 외 Provider 실제 도입 시 착수
- [ ] PipelineControl 커스텀 + 분산 큐 (Celery/Redis)
- [ ] 배치 렌더링 + 큐 — 그룹 일괄 렌더, WebSocket 진행률 | [명세](../../docs/01_product/FEATURES/PROJECT_GROUP.md) §3-3
- [ ] 브랜딩 시스템 — 로고/워터마크, 인트로/아웃트로, 플랫폼별 출력 | [명세](../../docs/01_product/FEATURES/PROJECT_GROUP.md) §3-3
- [ ] 분석 대시보드 — Match Rate 추이, 프로젝트 간 비교 | [명세](../../docs/01_product/FEATURES/PROJECT_GROUP.md) §3-3
- [ ] 파이프라인 이상 탐지 자동화 — health API, 자동 검증, GPU VRAM 모니터링
- [ ] PostgreSQL 통합 테스트 인프라 — pytest-postgresql 또는 testcontainers
- [ ] 클라우드 TTS/BGM 전환 — Replicate 또는 ElevenLabs/Suno
- [ ] 씬 단위 순차 생성 — IMAGE→TTS 씬별 처리, GPU 순차 독점 해소
- [ ] ControlNet 포즈 에셋 재활용 검토 — ComfyUI 2-Step 또는 레퍼런스 전용
- [ ] 캐릭터 LoRA 학습 파이프라인 — 레퍼런스 9세트 + 학습 자동화
