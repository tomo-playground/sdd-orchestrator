# Phase 19~20 + DB Schema Cleanup — Archive

---

## Phase 19: Studio 탭 페르소나 재배치

**완료일**: 02-28
**목표**: Film Production 메타포에 따라 탭별 소유권을 명확히 하고, Direct의 편집 공간을 극대화.
**명세**: [STUDIO_TAB_PERSONA_REORGANIZATION.md](../../01_product/FEATURES/STUDIO_TAB_PERSONA_REORGANIZATION.md)

### Phase 19-1: Stage 강화 + Express/Direct 안전망 (9항목)

| # | 항목 | 상태 |
|---|------|------|
| 1 | Stage "Visual Style" 섹션 추가 (StyleProfileSelector 이동) | ✅ (02-28) |
| 2 | StageCharactersSection에 CharacterSelector 통합 (선택 가능) | ✅ (02-28) |
| 3 | Stage Base Prompts 읽기전용 요약 + 캐릭터 페이지 편집 링크 | ✅ (02-28) |
| 4 | Stage "Generation Settings" 토글 섹션 추가 | ✅ (02-28) |
| 5 | StageReadinessBar "Style" 카테고리 + useMaterialsCheck 확장 | ✅ (02-28) |
| 6 | MaterialsPopover Characters→stage-tab + Style 항목 추가 | ✅ (02-28) |
| 7 | Express 모드: ScriptTab Express 분기를 Stage 경유로 변경 | ✅ (02-28) |
| 8 | Direct Context Strip (32px 읽기 전용 배지 + Stage 딥링크) | ✅ (02-28) |
| 9 | Direct에서 ImageSettingsContent + Settings 제거 | ✅ (02-28) |

### Phase 19-2: Publish SSOT 분리 (2항목)

| # | 항목 | 상태 |
|---|------|------|
| 1 | Publish Voice/BGM 프리셋 → 읽기 전용 + 볼륨/덕킹 슬라이더 유지 | ✅ (02-28) |
| 2 | "Stage에서 변경" 링크 버튼 추가 | ✅ (02-28) |

### Phase 19-3: 정리 및 검증 (4항목)

| # | 항목 | 상태 |
|---|------|------|
| 1 | Dead code 삭제 (6파일) | ✅ (02-28) |
| 2 | Dead import 정리 | ✅ (02-28) |
| 3 | VRT 베이스라인 갱신 (Direct, Stage, Publish) | ✅ (02-28) |
| 4 | Build 검증 (next build PASS, 0 new TS errors) | ✅ (02-28) |

**총 15항목 완료**

---

## Phase 20: Agent-Aware Inventory Pipeline (Director 캐스팅)

**완료일**: 02-28
**목표**: Director Agent가 캐릭터/구조/스타일 인벤토리를 인지하고 토픽에 최적인 조합을 자율 추천.
**명세**: [AGENT_AWARE_INVENTORY_PIPELINE.md](../../01_product/FEATURES/AGENT_AWARE_INVENTORY_PIPELINE.md)

### Phase 20-A: Director Inventory Awareness (9항목)

| # | 항목 | 상태 |
|---|------|------|
| 1 | `inventory.py` 인벤토리 로딩 서비스 (캐릭터 프루닝 20명) | ✅ (02-28) |
| 2 | `director_plan.j2` 템플릿 인벤토리 섹션 + CoT 캐스팅 가이드 | ✅ (02-28) |
| 3 | `CastingRecommendation` Pydantic + `DirectorPlanOutput.casting` 확장 | ✅ (02-28) |
| 4 | `ScriptState`에 `casting_recommendation` + `valid_character_ids` 추가 | ✅ (02-28) |
| 5 | `inventory_resolve` 노드 (user override 병합 + 5항목 유효성 검증) | ✅ (02-28) |
| 6 | Graph 엣지: `director_plan → inventory_resolve → research` | ✅ (02-28) |
| 7 | SSE `node_result` 기반 캐스팅 전달 + `_NODE_META` 등록 | ✅ (02-28) |
| 8 | 후방 호환성 검증 (기존 character_id 선택, Express/Quick 불변) | ✅ (02-28) |
| 9 | 최소 Frontend 토스트 (캐스팅 추천 표시) | ✅ (02-28) |

### Phase 20-B: Casting UX (5항목)

| # | 항목 | 상태 |
|---|------|------|
| 1 | CharacterSelector "AI Recommended" 그룹 + Sparkles 배지 | ✅ (02-28) |
| 2 | Script 탭 캐스팅 배너 (추천 수신 → 수락/무시 CTA) | ✅ (02-28) |
| 3 | `StageCastingCompareCard.tsx` 비교 카드 | ✅ (02-28) |
| 4 | character_id Optional → Director 자율 캐스팅 | ✅ (02-28) |
| 5 | `pipelineSteps.ts` "리서치/캐스팅" 스텝 라벨 변경 | ✅ (02-28) |

### Phase 20-C: Autonomous Express (5항목)

| # | 항목 | 상태 |
|---|------|------|
| 1 | `director_plan_lite` 경량 노드 (Flash, 캐릭터 10명 제한) | ✅ (02-28) |
| 2 | Express 라우팅 3분기 | ✅ (02-28) |
| 3 | One-Click Express UI (2단계 확인 + AI 결정 요약 카드) | ✅ (02-28) |
| 4 | 자율 결정 로그 SSE 스트림 | ✅ (02-28) |
| 5 | Fallback 전략 (최근 사용 캐릭터 + monologue) | ✅ (02-28) |

### Phase 20-D: Script 탭 캐스팅 UX 잔여 (3항목)

| # | 항목 | 상태 |
|---|------|------|
| 1 | CharacterSelectSection optgroup AI 추천 분리 | ✅ (02-28) |
| 2 | StoryboardGeneratorPanel Structure 추천 배지 | ✅ (02-28) |
| 3 | pipelineSteps.ts Standard 모드 `inventory_resolve` 매핑 | ✅ (02-28) |

**총 22항목 완료**

---

## DB Schema Cleanup — 미사용 컬럼/테이블 감사 및 정리

**완료일**: 02-28
**목표**: DB Schema v3.30 기준, 전체 테이블/컬럼의 실제 사용 현황을 DB 데이터 + 코드 참조 양면에서 감사하고 정리.
**명세**: [DB_SCHEMA_CLEANUP.md](../../01_product/FEATURES/DB_SCHEMA_CLEANUP.md)

### Sprint A: FIX FIRST + DOC FIX (7/7)

| # | 항목 | 상태 |
|---|------|------|
| 1-1 | `activity_logs` Gemini 편집 추적 INSERT 누락 수정 | ✅ (02-28) |
| 1-2 | `tags.valence` 일괄 시딩 실행 | ✅ (02-28) |
| 1-3 | `scene_quality_scores.identity_score` 저장 경로 수정 | ✅ (02-28) |
| 1-4 | `storyboards.base_seed` 자동 할당 추가 | ✅ (02-28) |
| 1-5 | `media_assets.checksum` 쓰기 로직 보완 | ✅ (02-28) |
| 4-1 | DB_SCHEMA.md 문서 불일치 4건 수정 | ✅ (02-28) |
| 5-2 | `ANALYZE` 실행 (pg_stat 통계 갱신) | ✅ (02-28) |

### Sprint B: DROP + INFRA (3/4, 1건 취소)

| # | 항목 | 상태 |
|---|------|------|
| 2-1 | `characters.reference_source_type` DROP | ✅ (02-28) |
| 2-2 | `scenes.multi_gen_enabled` DROP | ❌ 취소 (FE 활발 사용) |
| 2-3 | `scenes.last_seed` DROP | ✅ (02-28) |
| 5-1 | LangGraph Checkpoint GC 배치 구현 | ✅ (02-28) |

**총 10/11항목 완료 (1건 취소)**
