# LangFuse 활용 가이드

**최종 업데이트**: 2026-03-18
**관련 문서**: `TRACE_NAMING_GUIDE.md`, `FEATURES/LANGFUSE_SCORING.md`, `FEATURES/LANGFUSE_PROMPT_OPS.md`

---

## 1. 개요

LangFuse는 이 프로젝트에서 3가지 역할을 담당한다.

| 역할 | 설명 | 상태 |
|------|------|------|
| **Prompt Management** | 28개 프롬프트 chat 타입 관리 (system/user 분리) | ✅ 운영 중 |
| **Observability** | 파이프라인 Trace/Span/Generation 추적 | ✅ 운영 중 |
| **Scoring** | 품질 지표 기록/추적/비교 (9개 Score, Phase 38) | ✅ 운영 중 |

---

## 2. 인프라 구성

```
셀프호스팅 (Docker Compose)
├── LangFuse Server (Web UI + API)
├── PostgreSQL (메타데이터)
├── ClickHouse (이벤트 저장소)
└── Redis (캐시)
```

환경 변수 (`backend/.env`):
```
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3001
```

---

## 3. Prompt Management

### 3-1. 구조

```
LangFuse UI → 프롬프트 편집 (production 라벨)
     ↓
compile_prompt("creative/director") → CompiledPrompt(system, user)
     ↓
Gemini API (system_instruction / contents)
```

### 3-2. 네이밍 규칙

| 코드 이름 | LangFuse 이름 | 용도 |
|----------|--------------|------|
| `creative/director` | `pipeline/director` | Director ReAct 루프 |
| `creative/cinematographer` | `pipeline/cinematographer` | 씬별 비주얼 구성 (Single fallback 경량 프롬프트) |
| `creative/cinematographer/framing` | `pipeline/cinematographer/framing` | Team: 카메라, 시선, Ken Burns |
| `creative/cinematographer/action` | `pipeline/cinematographer/action` | Team: 감정, 포즈, 액션, 소품 |
| `creative/cinematographer/atmosphere` | `pipeline/cinematographer/atmosphere` | Team: 환경, 시네마틱 |
| `creative/cinematographer/compositor` | `pipeline/cinematographer/compositor` | Team: 통합 + 태그 검증 |
| `storyboard/dialogue` | `storyboard/dialogue` | Dialogue 대본 생성 |
| `tool/analyze-topic` | `tool/analyze-topic` | 주제 분석 |

전체 매핑: `langfuse_prompt.py`의 `_TEMPLATE_TO_LANGFUSE` dict

### 3-3. 프롬프트 vs 빌더 역할 분리

| 구분 | 위치 | 내용 |
|------|------|------|
| **정적 규칙/지시문** | LangFuse 프롬프트 (system/user) | 변경 시 LangFuse UI에서 새 버전 생성 |
| **동적 데이터** | `prompt_builders*.py` | 런타임 데이터를 `{{변수}}`에 주입 |

판단 기준: "프롬프트 버전 변경 없이 바뀔 수 있는가?" → Yes: 빌더, No: LangFuse

### 3-4. 프롬프트 수정 체크리스트

1. LangFuse UI에서 프롬프트 수정 → 새 버전 생성
2. `{{변수}}`를 추가한 경우 → 코드의 `compile_prompt()` 호출부에 해당 키 추가
3. `production` 라벨 지정 → 즉시 반영 (코드 배포 불필요)
4. 미치환 변수 경고 확인: `[LangFuse] 미치환 변수 감지` 로그 모니터링

---

## 4. Observability (Tracing)

### 4-1. 계층 구조

```
Trace (storyboard.generate)          ← 파이프라인 1회 = 1 Trace
  └─ Root Span (pipeline.generate)   ← 실행 단위
       ├─ Generation (generate_content director_plan)   ← LLM 호출
       ├─ Generation (generate_content writer)
       ├─ Generation (generate_content review)
       └─ ...
```

### 4-2. Session 그룹핑

```python
session_id = f"storyboard-{storyboard_id}"  # 동일 스토리보드의 generate/resume 묶기
```

- `generate-stream`: `_resolve_session_id(request.storyboard_id)` 전달
- `resume`: `_resolve_session_id(request.storyboard_id)` 전달 (최근 수정)

### 4-3. 핵심 파일

| 파일 | 역할 |
|------|------|
| `observability.py` | Trace/Span/Generation 관리, Score 헬퍼 (예정) |
| `langfuse_prompt.py` | 프롬프트 compile + 네이밍 매핑 |
| `routers/scripts.py` | `create_langfuse_handler()` 호출, session_id 설정 |

### 4-4. SDK v3 호환 (2026-03-18 전환)

| SDK v2 (제거됨) | SDK v3 (현재) |
|----------------|--------------|
| `Langfuse.trace()` | `start_as_current_span()` + `update_current_trace()` |
| `start_generation()` | `start_observation(as_type='generation')` |
| `CallbackHandler(trace_context=)` | 유지 (호환) |

OTel 컨텍스트 제약으로 `update_current_trace()`가 동작하지 않는 경우 `_patch_trace()` (Ingestion API 직접 호출)로 대체.

---

## 5. Scoring (계획 중)

### 5-1. Tier 분류

| Tier | 소스 | 신뢰도 | 활용 |
|------|------|--------|------|
| **Tier 1** | 코드 결정론적 측정 | 높음 | 절대값 비교, 회귀 감지 |
| **Tier 2** | LLM 자기평가 | 낮음 | 추이 비교만 (절대값 무의미) |
| **Tier 3** | 사용자 피드백 | 최고 | Ground truth (향후) |

### 5-2. Score 기록 방법

```python
from services.agent.observability import record_score  # 예정

# Tier 1: 객관적 지표
record_score("first_pass", True, data_type="BOOLEAN")
record_score("revision_count", 2, data_type="NUMERIC")

# Tier 2: LLM 평가 (comment에 세부 JSON)
record_score("narrative_overall", 0.81, comment='{"hook":0.8,"emotional_arc":0.7,...}')
```

### 5-3. Score Config

LangFuse UI에서 Score Config를 사전 등록하면:
- 값 범위 자동 검증 (min/max)
- 대시보드에서 자동 차트 생성
- 프롬프트 버전별 Score 비교 가능

상세: `FEATURES/LANGFUSE_SCORING.md`

---

## 6. 대시보드 활용

### 6-1. Traces 탭

- **필터**: session_id(storyboard별), name(generate/resume), 시간 범위
- **용도**: 특정 스토리보드의 파이프라인 실행 이력 추적

### 6-2. Prompts 탭

- **버전 비교**: 프롬프트 변경 전/후 성능 비교
- **변수 확인**: 프롬프트에 정의된 `{{변수}}` 목록 확인

### 6-3. Scores 탭 (도입 후)

- **추이 그래프**: first_pass rate, revision_count 평균 시간별 추이
- **프롬프트별 비교**: Writer v3 vs v4의 narrative_overall 분포
- **모드별 분석**: full vs fasttrack 품질 차이

### 6-4. Sessions 탭

- **storyboard별 그룹핑**: 같은 스토리보드의 generate + resume trace 묶어 보기
- **세션 품질**: 세션별 총 LLM 호출 수, 총 토큰, 소요 시간

---

## 7. 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `[LangFuse] 미치환 변수 감지` | 프롬프트 `{{변수}}`와 코드 template_vars 키 불일치 | 프롬프트 변수명과 코드 키 동기화 |
| `'Langfuse' object has no attribute 'trace'` | SDK v3에서 trace() 제거됨 | `start_as_current_span()` 사용 |
| `start_generation is deprecated` | SDK v3 deprecation | `start_observation(as_type='generation')` 사용 |
| Trace name이 비어있음 | `start_span()`만으로는 trace 메타 미설정 | `_patch_trace()` 또는 `update_current_trace()` 병행 |
| Session에 trace가 묶이지 않음 | resume 경로에 session_id 미전달 | `storyboard_id` 기반 `_resolve_session_id()` 전달 |
| Score 탭이 비어있음 | `create_score()` 호출 미구현 | `LANGFUSE_SCORING.md` Sprint A-D 구현 필요 |

---

## 8. 변경 이력

| 날짜 | 변경 |
|------|------|
| 2026-03-17 | Jinja2→LangFuse compile() 전환 완료 (28개 프롬프트) |
| 2026-03-17 | OTel GenAI Semantic Conventions 기반 Trace 네이밍 |
| 2026-03-18 | Phase 36: 프롬프트 33개 전수 품질 강화 |
| 2026-03-18 | SDK v3 호환: trace()→start_span, start_generation→start_observation |
| 2026-03-18 | resume session_id 누락 수정 (storyboard_id 전달) |
| 2026-03-18 | 미치환 변수 3건 수정 (Phase 36 프롬프트↔코드 동기화) |
| 2026-03-18 | Scoring 시스템 명세 작성 (LANGFUSE_SCORING.md) |
