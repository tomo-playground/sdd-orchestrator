# LangFuse Prompt Ops — 2차 개선 계획

**상태**: 백로그
**프로젝트 우선순위**: P2 (Infrastructure)
**선행 완료**: LangFuse Prompt Management 전체 이전 (28개 chat 타입, Phase 0~2)
**목적**: 프롬프트 이관 인프라를 활용한 **데이터 기반 프롬프트 최적화 사이클** 구축

---

## 배경

Phase 0~2에서 28개 프롬프트를 LangFuse chat 타입으로 이관하고, runtime fetch + fallback 인프라를 구축했다. 그러나 현재는 **프롬프트를 변경해도 품질이 개선되었는지 정량적으로 확인할 수 없고**, 변경이 기존 품질을 훼손하는지 검증할 방법이 없다.

2차 개선은 이 인프라 위에 **실험(A/B) → 측정(Score) → 검증(Dataset)** 사이클을 구축하여, 프롬프트 개선을 데이터 기반으로 수행하는 것이 목표다.

> 관련 명세: [PROJECT_GROUP.md §3-3](PROJECT_GROUP.md) (분석 대시보드), 파이프라인 이상 탐지 (ROADMAP Infrastructure)

---

## 현재 상태 (Phase 2 완료)

| 항목 | 상태 |
|------|------|
| 28개 프롬프트 LangFuse chat 타입 관리 | ✅ |
| runtime fetch + 로컬 fallback | ✅ |
| `prompt_partials.py` 파셜 Python 전환 | ✅ |
| `observability.py` 트레이싱 (trace → span → generation) | ✅ |
| 업로드 스크립트 (`upload_prompts_to_langfuse.py`) | ✅ |
| 29개 단위 테스트 | ✅ |

---

## 데이터 소유권 정리 (이원화 해소)

### 원칙: **LLM 관련 지표는 LangFuse SSOT, 이미지/도메인 지표는 DB SSOT**

프로젝트 DB(ActivityLog)와 LangFuse가 일부 기능에서 겹친다. 이원화 방지를 위해 데이터 소유권을 명확히 분리한다.

| 지표 | SSOT | 이유 |
|------|------|------|
| **Token Usage / LLM 비용** | LangFuse | generation에서 `usage_metadata` 자동 수집. DB 수동 기록 불필요 |
| **LLM 호출 에러율** | LangFuse | generation `level="ERROR"` 자동 기록 → 대시보드 필터 |
| **프롬프트 버전별 성능** | LangFuse | Score + Prompt 버전 연결 = LangFuse 내장 분석 |
| **노드별 레이턴시** | LangFuse | span/generation `duration` 자동 수집 |
| **Match Rate (WD14)** | DB | 로컬 ML 이미지 분석 — LangFuse와 무관 |
| **이미지 생성 이력 (seed, params)** | DB (ActivityLog) | SD 파라미터, 재현용 — LLM이 아닌 이미지 도메인 |
| **사용자 승인/거부 이력** | DB | 비즈니스 데이터 — LangFuse에는 score로 미러링만 |

### 현재 겹침 & 해소 방향

| 항목 | 현재 상태 | 해소 방향 |
|------|----------|----------|
| Gemini 편집 비용 (`gemini_cost_usd`) | DB 수동 기록 | **LangFuse로 위임** — token usage 자동 집계 활용. DB 필드는 레거시 유지 (쓰기 중단). 기존 Analytics API 참조 지점 사전 조사 필요 |
| 에러 추적 | DB `status="fail"` + LangFuse `level="ERROR"` 이중 | **DB는 도메인 상태만** (이미지 생성 성공/실패). LLM 에러 분석은 LangFuse 대시보드 |
| Analytics API (`/admin/analytics/gemini-edits`) | DB 기반 커스텀 쿼리 | **유지** — 사용자 정의 도메인 분석. LangFuse 대시보드와 상호 보완 |

### 삭제 대상 (자체 evaluation 시스템)

- `evaluation_runs` 테이블: **이미 삭제됨** (Phase 6-4.4, 사용 0건)
- 향후 평가/회귀 테스트는 LangFuse Datasets 기능 사용 → DB 테이블 신규 생성 금지

---

## Sprint 1: A/B 테스트 & 버전 관리

**목적**: 프롬프트 변경을 안전하게 실험하고 비교하는 체계

### 1-1. Label 기반 버전 분기

현재 `get_prompt_template()`은 항상 `label="production"`을 fetch한다.

**변경**:
- `get_prompt_template(template_name, *, label="production")` 파라미터 추가
- 파이프라인 실행 시 `staging` 라벨 지정 가능
- LangFuse UI에서 프롬프트 버전별 `production` / `staging` / `latest` 라벨 관리

**label 전파 메커니즘**: `ScriptState`에 `prompt_label: str = "production"` 필드를 추가하여 LangGraph 상태로 전파. 각 노드에서 `state["prompt_label"]`을 읽어 `get_prompt_template()`에 전달. `run_production_step()` 경유 호출과 직접 호출(`cinematographer.py`, `research.py`, `review.py`, `location_planner.py`) 모두 커버.

**코드 변경점**:
```
langfuse_prompt.py   — label 파라미터 전파
_production_utils.py — run_production_step()에 label 옵션 추가
state.py             — ScriptState에 prompt_label 필드 추가
cinematographer.py, research.py, review.py, location_planner.py — state에서 label 읽기
```

### 1-2. 실험 모드

기존 파이프라인 실행 엔드포인트에 `prompt_label` 파라미터를 추가하여 staging 실험 지원. 별도 API 신설보다 기존 엔드포인트 확장이 깔끔하다.

### 1-3. 버전 비교 (LangFuse 내장 활용)

LangFuse UI의 기존 기능 활용 — 추가 개발 없음:
- 프롬프트 버전별 trace 필터링
- 버전별 평균 latency / token usage 비교

**프롬프트 캐싱 고려**: label 추가 시 production/staging 두 벌 캐시 필요. 파이프라인 retry 시 동일 프롬프트 반복 fetch 방지를 위해 TTL 기반 애플리케이션 레벨 캐시 설계 권장.

---

## Sprint 2: Evaluation & Scoring

**목적**: 프롬프트 출력 품질을 정량화하여 개선 방향 수립
**의존성**: Sprint 1과 **병렬 착수 가능** (score 기록에 label이 필수가 아님)

### 2-0. 전제조건: trace_id 보존

사용자 피드백 score(2-2)를 기록하려면, 스토리보드가 어떤 trace_id로 생성되었는지 알아야 한다. 현재 `_current_trace_id`는 요청 종료 시 소멸하므로:

- `storyboards` 테이블에 `langfuse_trace_id` 컬럼 추가 (Alembic 마이그레이션)
- 파이프라인 완료 시 trace_id를 스토리보드에 저장
- 이 스키마 변경이 Sprint 2의 전제조건

### 2-1. 자동 스코어링

파이프라인 완료 시 trace에 자동으로 score를 기록한다. **DB가 아닌 LangFuse에 기록**.

| Score 이름 | 타입 | 산출 기준 | 기록 시점 |
|-----------|------|----------|----------|
| `json_parse_success` | Boolean | Gemini 출력 JSON 파싱 성공 여부 | 파이프라인 완료 즉시 |
| `scene_count_match` | Numeric (0~1) | 요청 씬 수 vs 실제 생성 씬 수 비율 | 파이프라인 완료 즉시 |
| `speaker_balance` | Numeric (0~1) | 캐릭터별 대사 배분 균등도 | 파이프라인 완료 즉시 |
| `tag_validity` | Numeric (0~1) | WD14 기준 유효 태그 비율 (Match Rate) | **이미지 생성 완료 후 비동기** |
| `tts_success_rate` | Numeric (0~1) | TTS 생성 성공 씬 비율 | **TTS 완료 후 비동기** |

**타이밍 분리**: `tag_validity`와 `tts_success_rate`는 파이프라인(LLM 단계) 완료 후 별도 프로세스(이미지 생성, TTS)에서 실행된다. 이 스코어는 해당 프로세스 완료 시 `langfuse_trace_id`를 기반으로 비동기 기록.

**score 유실 방어**: LangFuse 서버 장애 시 score 기록 실패를 로그로 남기고, 도메인 로직에 영향을 주지 않는다.

**코드 변경점**:
```
observability.py         — score_trace(name, value, trace_id) 함수 추가
nodes/finalize.py        — 파이프라인 완료 후 즉시 스코어링 (3종)
services/video/scene_processing.py — 이미지/TTS 완료 후 비동기 스코어링 (2종)
```

### 2-2. 사용자 피드백 스코어

스토리보드 승인/거부 시 해당 trace에 score 기록:

| Score 이름 | 타입 | 트리거 |
|-----------|------|--------|
| `user_approval` | Boolean | 스토리보드 최종 승인 |
| `user_rating` | Numeric (1~5) | (향후) 사용자 만족도 평점 |

**데이터 흐름**: DB(승인 이력) → `storyboards.langfuse_trace_id`로 trace 참조 → LangFuse score 미러링. 원본은 DB, LangFuse는 분석용.

### 2-3. 프롬프트 버전별 점수 추이 (LangFuse 내장 활용)

LangFuse 대시보드에서 확인 — 추가 개발 없음:
- 프롬프트 이름 × 버전별 score 평균
- 시계열 추이 (품질 회귀 감지)

---

## Sprint 3: Dataset & Regression Test

**목적**: 프롬프트 변경 시 기존 품질을 보장하는 자동 회귀 테스트
**의존성**: Sprint 2 (자동 스코어링 필요)

### 3-1. 골든 데이터셋 구축

**LangFuse Datasets 기능 사용** — DB 테이블 신규 생성 금지.

| 데이터셋 | 케이스 수 | 입력 예시 |
|---------|----------|----------|
| `storyboard-basic` | 5 | 감성 고백, 일상 에피소드, 여행 브이로그 |
| `storyboard-dialogue` | 3 | 2인 대화, 나레이터 포함 |
| `cinematographer` | 5 | 다양한 캐릭터 × 스타일 조합 |
| `review-unified` | 3 | 씬 품질 검증 시나리오 |

### 3-2. 회귀 테스트 (2가지 모드)

**전체 파이프라인 테스트** (비용 높음):
```bash
python scripts/run_prompt_regression.py \
  --dataset storyboard-basic \
  --label staging
```

**노드 단위 격리 테스트** (비용 효율적, 권장):
```bash
python scripts/run_prompt_regression.py \
  --dataset cinematographer \
  --node-only cinematographer \
  --label staging
```

- 개별 노드에 입력을 직접 주입하여 프롬프트 변경의 영향을 정밀 측정
- 전체 파이프라인 실행 대비 비용 1/5~1/10

**LangFuse link 연결**: `item.link()`는 generation 객체가 필요하나 LangGraph는 state dict를 반환하므로, `_current_trace_id` 기반 커스텀 link 로직으로 연결.

### 3-3. CI 통합 (선택)

프롬프트 변경 PR 시 자동 회귀 테스트 실행.
- 비용이 발생하므로 수동 트리거 (`workflow_dispatch`) 권장
- 결과를 PR 코멘트로 리포트

---

## Sprint 4: 비-Agent 프롬프트 확장

**목적**: Agent 파이프라인 외 Gemini 호출도 LangFuse 관리 범위에 포함
**의존성**: 없음 (독립)

### 4-1. 대상 프롬프트

| 파일 | 프롬프트 | 현재 상태 |
|------|---------|----------|
| `script/gemini_generator.py` | 스토리보드 생성 system instruction | 인라인 하드코딩 |
| `validation_gemini.py` | 태그 검증 외 추가 검증 | 인라인 하드코딩 |
| `nodes/critic.py` 등 Creative Lab | 에이전트 역할 프롬프트 | config dict |

### 4-2. 이관 방식

기존 Phase 1~2와 동일한 패턴:
1. `LANGFUSE_MANAGED_TEMPLATES`에 추가
2. `upload_prompts_to_langfuse.py` SYSTEM_INSTRUCTIONS에 매핑 추가
3. 호출부에서 `get_prompt_template()` 사용
4. 기존 인라인 프롬프트는 fallback으로 유지

---

## 구현 우선순위 요약

> Sprint 내부 우선순위(P1~P3)는 기능 내 상대 순서이며, 프로젝트 전체 우선순위(P2)와 별개다.

| Sprint | 핵심 가치 | 코드 변경량 | 의존성 | 내부 우선순위 |
|--------|----------|------------|--------|-------------|
| **1. A/B 테스트** | 안전한 프롬프트 실험 | 중 (~120줄) | 없음 | P1 |
| **2. Evaluation** | 품질 정량화 | 중 (~200줄 + 마이그레이션) | 선택적 (Sprint 1 없이도 가능) | P1 |
| **3. Dataset** | 회귀 방지 | 중~대 (~250줄 + 데이터) | Sprint 2 | P2 |
| **4. 비-Agent 확장** | 관리 범위 확대 | 소 (~100줄) | 없음 (독립) | P3 |

---

## 수락 기준 (DoD)

| # | Sprint | 기준 |
|---|--------|------|
| 1 | S1 | staging 라벨 프롬프트로 파이프라인 실행 후 trace에 prompt_label 메타데이터 기록 |
| 2 | S1 | production vs staging 결과를 LangFuse 대시보드에서 필터링 비교 가능 |
| 3 | S2 | 파이프라인 완료 시 3종 즉시 score(`json_parse_success`, `scene_count_match`, `speaker_balance`)가 trace에 자동 기록 |
| 4 | S2 | 이미지/TTS 완료 후 2종 비동기 score(`tag_validity`, `tts_success_rate`)가 trace에 기록 |
| 5 | S2 | 스토리보드 승인 시 `user_approval` score가 LangFuse에 미러링 |
| 6 | S3 | 골든 데이터셋 4종(16 케이스)이 LangFuse Datasets에 등록 |
| 7 | S3 | 회귀 테스트 스크립트가 staging vs production score 차이 리포트 출력 |
| 8 | S4 | 3개 비-Agent 프롬프트가 LangFuse 관리 + runtime fetch 동작 |

---

## 테스트 계획

| Sprint | 예상 테스트 | 범위 |
|--------|-----------|------|
| S1 | ~8개 | label 전파, staging fetch, fallback |
| S2 | ~12개 | score_trace() 함수, 자동 스코어링, 비동기 기록, 유실 방어 |
| S3 | ~6개 | 데이터셋 로드, 노드 격리 실행, 비교 리포트 |
| S4 | ~4개 | 신규 템플릿 fetch + fallback |

---

## 비-목표 (Out of Scope)

- LiteLLM 도입: 별도 항목 (LLM Provider 추상화 Phase F)
- 파이프라인 이상 탐지: 별도 항목 (파이프라인 이상 탐지 자동화) — LangFuse Alert 기능 활용 예정
- LangFuse 인프라 변경: 현재 셀프호스팅 v3 유지
- 자체 evaluation DB 테이블 신규 생성: LangFuse Datasets/Scores로 대체
- Jinja2 SandboxedEnvironment 전환: 보안 개선이나 별도 이슈로 관리
