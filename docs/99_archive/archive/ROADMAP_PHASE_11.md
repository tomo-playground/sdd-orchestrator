# Phase 11: Scene Diversity & Frontal Bias Fix — 아카이브

**완료일**: 2026-02-20
**목표**: 이미지 생성 시 정면(looking_at_viewer) 편향 해소 + 포즈/앵글/시선 다양성 보장.

**배경**: Cinematographer 템플릿/도구에 정면 편향 유발 요소 10개 발견. 장면 다양성 보장 메커니즘 부재. Danbooru 데이터 기반 `looking_at_viewer` 430만 건 vs 2위 33만 건 (13배 차이)으로 SD 모델 자체도 정면 prior 강함.

---

## P0 — 템플릿/태그 즉시 수정

| 순위 | 작업 | 상태 | 효과 |
|------|------|------|------|
| 1 | `cinematographer.j2` gaze/pose 다양성 규칙 + 시너지 표 추가 | [x] 02-20 | 높음 |
| 2 | `create_storyboard.j2` Narrative Function별 gaze 가이드 추가 | [x] 02-20 | 높음 |
| 3 | `patterns.py` 버그 수정 (`averted_gaze`→`averting_eyes`, 누락 태그 추가) | [x] 02-20 | 중간 |

## P1 — 도구/평가 기준 개선

| 순위 | 작업 | 상태 | 효과 |
|------|------|------|------|
| 4 | `search_similar_compositions()` mood별 gaze 분기 (portrait=정면 하드코딩 제거) | [x] 02-20 | 중간 |
| 5 | `scene_expand.j2` 예시 다양화 (looking_at_viewer → 다양한 gaze) | [x] 02-20 | 낮음 |
| 6 | `director_step_qc.j2` 평가 기준에 Pose & Gaze Diversity 추가 | [x] 02-20 | 중간 |

## P2 — QC 검증 강화

| 순위 | 작업 | 상태 | 효과 |
|------|------|------|------|
| 7 | `validate_visuals()` QC에 gaze/pose 다양성 WARN 추가 | [x] 02-20 | 중간 |
| 8 | 비정면 gaze 가중치 부스트 (L7 1.1x → 1.25x, IP-Adapter 보상) | [x] 02-20 | 중간 |

## P2+ — 프롬프트 품질 후속 보강

| 순위 | 작업 | 상태 | 효과 |
|------|------|------|------|
| 8-1 | Gaze 태그 34개 `default_layer` 통일 → LAYER_EXPRESSION(7) (Alembic 마이그레이션) | [x] 02-20 | 중간 |
| 8-2 | Cinematographer에 `style` 변수 전달 + Anime/Chibi/Realistic 스타일별 태그 규칙 | [x] 02-20 | 높음 |
| 8-3 | `_NON_FRONTAL_GAZE` 누락 태그 5개 추가 (averted_gaze, downcast_eyes, closed_eyes 등) | [x] 02-20 | 중간 |
| 8-4 | Writer/Revise description 과적 → `pipeline_context` dict 분리 (템플릿 독립 섹션) | [x] 02-20 | 중간 |

**검증 결과** (Storyboard #442 vs #441):
- `realistic` 태그: 9/9 → **0/9** (완전 해소)
- Gaze 종류: 2종 → **5종**, 반영률 45% → **100%**
- Camera 종류: 0종 → **3종** (upper_body/cowboy_shot/close-up)
- 정면 비율: 2/9 = 22% (≤30% 기준 충족)

## P3 — 파이프라인 구조

| 순위 | 작업 | 상태 | 효과 |
|------|------|------|------|
| 9 | Cinematographer 연속 씬 gaze 비중복 규칙 | [x] 02-20 | 높음 |
| 10 | Director → Cinematographer 피드백에 QC 다양성 결과 자동 주입 | [x] 02-20 | 높음 |

---

## Tier 2 — Pipeline 고도화 (전체 완료 02-19)

| 순위 | 작업 | 상태 | 근거 |
|------|------|------|------|
| 1 | Revision history 누적 (review→revise 루프 히스토리 보존) | [x] 02-19 | 동일 실패 반복 방지, revision 성공률 향상 |
| 2 | Checkpoint score → routing 연결 (점수 기반 분기) | [x] 02-19 | score 기반 decision override 안전망 |
| 3 | Human gate snapshot (중간 결과물 정리) | [x] 02-19 | Creator 모드 UX 개선 |
| 4 | Pydantic 모델 전환 (LLM 출력 검증) | [x] 02-19 | 검증 함수 중복 제거, 에러 메시지 품질 |
| 5 | Research 되돌리기 분기 (저점수 → research 재실행) | [x] 02-19 | 점수 기반 조건부 엣지, MAX_RETRIES 가드레일 |

---

## 최근 작업 로그 (02-19 ~ 02-20)

- **Cinematographer 한글 장면설명 표시** (02-20): `CinematographerSection`에 `image_prompt_ko` 표시 추가
- **Gemini 코드 리뷰 + BLOCKER 수정** (02-20): `gemini_generator.py` preset.system_prompt AttributeError 수정, scriptwriter.j2/script_qc.j2 한국어 표준어 규칙 추가, Frontend UI 패딩/레이아웃 일관성 개선
- **Phase 11-P3 완료 + 렌더링/UI 수정** (02-20): 연속 씬 gaze 비중복 검출, QC→Director 피드백 자동 주입, TTS 마지막 씬 음성 소실 수정. 16개 테스트 추가
- **프롬프트 품질 후속 수정** (02-20): _NON_FRONTAL_GAZE 누락 태그 5개, Cinematographer style 전달, gaze 태그 34개 default_layer 통일, pipeline_context 분리
- **Pipeline Resume 오류 + SSE 에러 알림 수정** (02-20): writer.py description 2000자 초과 해소, Frontend SSE 에러 전환 + resume() warning 토스트
- **Scene Diversity & Frontal Bias Fix P0~P2** (02-20): 정면 편향 해소 8건. 기존 133개 테스트 PASS
- **Character UI/UX 4대 개선** (02-20): Tag Show More, 섹션 접기/펼치기, Builder Prompts Step 4, 중복 태그 경고. 9개 테스트 추가
- **Composed Negative Preview** (02-20): 씬 편집기 네거티브 프롬프트 합성 미리보기. 8개 테스트 추가
- **실사풍 StyleProfile 호환성 + Negative Prompt 수정** (02-20): quality tag fallback StyleProfile SSOT 전환. 25개 테스트 추가
- **Video Gallery 개선** (02-19): 타입별 8개 표시 + View All 가로 스크롤 레이아웃
- **홈 화면 개선** (02-19): Continue Working 가로 스크롤, Video Gallery 타입별 2줄 레이아웃
- **Research 되돌리기 분기** (02-19): 품질 점수 기반 research 재실행 라우팅. 6개 테스트 추가
- **Research 품질 점수 체계** (02-19): 규칙 기반 4-메트릭 산출. 26개 테스트 추가
- **Cinematographer 빈 응답 fallback + retry** (02-19): 5개 테스트 추가
- **Pydantic LLM 출력 검증 전환** (02-19): 25개 테스트 추가
- **Non-Danbooru 태그 오탐 수정** (02-19): CATEGORY_PATTERNS 전체 태그 allowlist 추가
- **Human Gate Snapshot 보강** (02-19): 8개 테스트 추가
- **Gemini Safety Preflight Check** (02-19): 6개 테스트 추가
- **렌더링 영상 새로고침 소실 버그 수정** (02-19)
- **문서 일괄 동기화** (02-19): 17-노드 파이프라인 기준 6개 문서 업데이트
- **Pipeline 고도화: Revision History + Score-Based Routing** (02-19): 7개 테스트 추가
- **Tag Effectiveness 안정화** (02-19): identity 태그 death spiral 방지
- **Agentic Pipeline 안정화** (02-19): 33개 테스트 추가
- **Director-as-Orchestrator** (02-19): 15→17노드 그래프
- **HOME 레이아웃 재구성** (02-19)
- **QA TC 매트릭스** (02-19): 커버리지 62%→74%
- **Studio UX 개선** (02-19): 1-column, SSE 노출, Scene 번호 1-based
- **렌더링 품질 개선** (02-14~17): 52개 테스트
