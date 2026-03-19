# Backlog

> 실행 가능한 태스크 큐. 우선순위 순서대로 진행.
> Roadmap(Phase/마일스톤)은 여기에 쓰지 않는다.

---

## P0 (긴급)

- [ ] Storyboard Data Integrity — 씬 데이터 무결성 보장 (SB 1128: UI 7씬/DB 0씬, FK 위반) | [명세](../../docs/01_product/FEATURES/STORYBOARD_DATA_INTEGRITY.md)

## P1 (최우선)

- [ ] Enum ID 정규화 — structure/language/style 디스플레이 이름→ID 분리, DB 마이그레이션 | [명세](../../docs/01_product/FEATURES/ENUM_ID_NORMALIZATION.md)
- [ ] Speaker 동적 역할 Phase A — 정적 A/B/Narrator → speaker_1/speaker_2/narrator 전환 | [명세](../../docs/01_product/FEATURES/SPEAKER_DYNAMIC_ROLE.md)
- [ ] ComfyUI 마이그레이션 — ForgeUI→ComfyUI + SD Client 추상화 | [명세](../../docs/01_product/FEATURES/COMFYUI_MIGRATION.md)
- [ ] 캐릭터 일관성 V3 — ComfyUI 전환 후 착수. 4-Module 파이프라인 | [명세](../../docs/01_product/FEATURES/CHARACTER_CONSISTENCY_V3.md)

## P2 (기능 확장)

- [ ] VEO Clip — Video Generation 통합 | [명세](../../docs/01_product/FEATURES/VEO_CLIP.md)
- [ ] Profile Export/Import — Style Profile 공유 | [명세](../../docs/01_product/FEATURES/PROFILE_EXPORT_IMPORT.md)
- [ ] Storyboard Version History
- [ ] Direct 탭 연출 컨트롤 — TTS 톤 조정 + BGM 프리셋 일괄 적용 | [명세](../../docs/01_product/FEATURES/DIRECT_TAB_DIRECTOR_CONTROL.md)
- [ ] Studio 탭 URI 표현 — ?tab=script/stage/direct/publish 딥링크
- [ ] Script Canvas 분할 뷰 — 좌 채팅 + 우 씬 프리뷰 | [명세](../../docs/01_product/FEATURES/SCRIPT_COLLABORATIVE_UX.md) §P2

## P3 (인프라/자동화)

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
