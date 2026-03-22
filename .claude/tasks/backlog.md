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

## P1 (최우선)

- [ ] SP-048 — Direct 탭 UX 미세 조정 — 액션 피드백 2건 + 정보 불일치 3건 (음성톤/BGM 토스트, 전체적용 로딩, Speaker 이름, Consistency 모순, 화풍 중복)
- [ ] SP-047 — Direct 컨트롤 리뷰 후속 수정 — PR #126 미수정 WARNING 4건 + INFO 3건 (null 가드, 토스트 집계, 주석 불일치)
- [ ] SP-046 — Cinematographer 팀 분해 — 350줄 1인 다역 → 4 서브 에이전트 (Framing/Action/Atmosphere/Compositor)
- [ ] SP-020 — Enum ID 정규화 — structure/language/style ID 분리 + DB 마이그레이션 | [명세](../../docs/01_product/FEATURES/ENUM_ID_NORMALIZATION.md)
- [ ] SP-021 — Speaker 동적 역할 Phase A — 정적 A/B/Narrator → speaker_1/speaker_2/narrator 전환 | [명세](../../docs/01_product/FEATURES/SPEAKER_DYNAMIC_ROLE.md)
- [ ] SP-022 — ComfyUI 마이그레이션 — ForgeUI→ComfyUI + SD Client 추상화 | [명세](../../docs/01_product/FEATURES/COMFYUI_MIGRATION.md)
- [ ] SP-023 — 캐릭터 일관성 V3 — ComfyUI 전환 후 착수. 4-Module 파이프라인 | [명세](../../docs/01_product/FEATURES/CHARACTER_CONSISTENCY_V3.md)

## P2 (기능 확장)

- [ ] SP-024 — VEO Clip — Video Generation 통합 | [명세](../../docs/01_product/FEATURES/VEO_CLIP.md)
- [ ] SP-025 — Profile Export/Import — Style Profile 공유 | [명세](../../docs/01_product/FEATURES/PROFILE_EXPORT_IMPORT.md)
- [ ] SP-026 — Storyboard Version History — 저장 시점별 스냅샷 조회/복원
- [x] ~~SP-027~~ — Direct 탭 연출 컨트롤 — TTS 톤 조정 + BGM 프리셋 일괄 적용 | [명세](../../docs/01_product/FEATURES/DIRECT_TAB_DIRECTOR_CONTROL.md)
- [ ] SP-028 — Studio 탭 URI 표현 — ?tab=script/stage/direct/publish 딥링크
- [ ] SP-029 — Script Canvas 분할 뷰 — 좌 채팅 + 우 씬 프리뷰 | [명세](../../docs/99_archive/features/SCRIPT_COLLABORATIVE_UX.md) §P2

## P2-SDD (SDD 프로세스 개선)

- [ ] SP-033 — DoD 검증 자동화
- [ ] SP-034 — PR 엣지 케이스 체크리스트
- [ ] SP-049 — SDD 태스크 구조 개선 — 디렉토리 기반 태스크 (spec.md + design.md) + /sdd-run 매칭 로직 대응
- [ ] SP-051 — SDD 2인 확장 플랜 — 설계 리뷰/태스크 관리를 GitHub Issue 기반으로 전환 (로컬→GitHub 마이그레이션 가이드)

## P3 (인프라/자동화)

- [ ] SP-050 — DirectorControlPanel 프리셋 Backend SSOT 전환 — EMOTION_PRESETS/BGM_MOOD_PRESETS 하드코딩 → /presets API 소비

- [ ] Tag Intelligence — 채널별 태그 정책 + 데이터 기반 추천 | [명세](../../docs/01_product/FEATURES/PROJECT_GROUP.md) §3-1
- [ ] Series Intelligence — 에피소드 연결 + 성공 패턴 학습 | [명세](../../docs/01_product/FEATURES/PROJECT_GROUP.md) §3-2
- [ ] LoRA Calibration Automation
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
