# Agentic AI Pipeline (LangGraph Migration)

**상태**: 완료 (Phase 0~5E 전체 완료, 2026-02-17)
**출처**: 현행 파이프라인 구조 분석 (2026-02-13)
**핵심 질문**: 대본 생성 파이프라인을 LangGraph 기반 에이전틱 AI로 전환

---

## 1. 현행 구조의 문제점

### 1-1. Script Generation = 단일 Gemini 호출

```
현재: Topic → Jinja2 렌더링 → Gemini 1회 호출 → JSON 파싱 → 태그 후처리 → 끝
```

- 반복 개선(iterative refinement) 루프 없음
- 품질 불만족 시 전체 재생성만 가능
- 이전 생성 결과를 학습/참조하지 않음

### 1-2. Creative Lab = 커스텀 오케스트레이션

```
현재: 3x Architect 병렬 → Devil's Advocate → Director 평가 → 수렴 시 종료
      → Scriptwriter → Cinematographer → Sound Designer → Copyright Reviewer
```

- 자체 구현 상태 관리 (`context` JSONB 한 덩어리)
- Phase 1(토론) 중단 시 복구 불가
- Phase 2만 부분적 resume 지원
- 그래프 구조가 아닌 하드코딩 if/else 분기

### 1-3. 메모리 부재

| 필요한 메모리 | 현재 상태 |
|--------------|----------|
| **Conversational** (세션 내 대화 컨텍스트) | `creative_traces`에 로그만 저장 |
| **Long-term** (사용자 선호, 성공 패턴) | 없음 |
| **Episodic** (과거 경험 기반 판단) | 없음 |
| **Shared State** (에이전트 간 블랙보드) | `context` JSONB (단방향, 타입 없음) |

### 1-4. Script Generation vs Creative Lab 이원화

| | Script Generation | Creative Lab |
|---|---|---|
| 진입점 | `POST /scripts/generate` | `POST /lab/creative/sessions/{id}/run-debate` |
| 에이전트 수 | 0 (단일 호출) | 9 (멀티에이전트) |
| 코드 경로 | `script/gemini_generator.py` | `creative_shorts.py` + `creative_pipeline.py` |
| 코드 공유 | 없음 | 없음 |
| 메모리 | 없음 | 세션 내 라운드 기억만 |

두 시스템이 같은 목적(대본 생성)이지만 **완전히 분리된 코드 경로**를 가짐.

### 1-5. Script 탭 Manual/AI Agent 이중 모드

1-4의 Backend 이원화가 Frontend UI에도 그대로 노출:

| | Manual 모드 | AI Agent 모드 |
|---|---|---|
| API | `POST /scripts/generate` | `POST /lab/creative/sessions/{id}/run-debate` |
| 코드 경로 | `gemini_generator.py` | `creative_shorts.py` + `creative_pipeline.py` |
| Frontend 훅 | `useScriptEditor` | `useShortsSession` |
| 소요 시간 | ~30초 (Gemini 1회) | ~5-15분 (Debate + Pipeline) |

**문제**: 사용자가 "같은 목적, 다른 탭"을 선택해야 하는 혼란. 두 모드의 출력 포맷도 상이.

**해결 방향** (Phase 1): Manual 탭 제거 → 단일 AI 모드 + Quick/Full 선택.
- **Quick**: 기존 Manual과 동일 (Gemini 1회, ~30초) — Graph 2노드 (Draft→Finalize)
- **Full**: 기존 AI Agent Debate + Pipeline (~5-15분) — Phase 1.5에서 Graph 확장 노드로 전환

---

## 2. 목표 (To-Be)

### 2-1. 비전: 제어 스펙트럼 (Control Spectrum)

사용자가 **단계별로 AI 개입 수준을 독립 설정**하는 유연한 파이프라인.

```
Manual                 Assisted                Delegated
  │                      │                       │
  사람이 직접 작성        AI가 초안 → 사람이 검토    사람이 목표만 설정
  AI는 검증/제안만        핵심 결정은 사람            AI가 실행 + 자체 검토
                                                  확신 낮을 때만 질문
```

#### 단계별 제어 매핑

| 단계 | Manual | Assisted | Delegated |
|------|--------|----------|-----------|
| **컨셉/주제** | 사람이 직접 입력 | AI가 3안 제시 → 사람 선택 | AI가 자동 선택 |
| **대본 작성** | 사람이 씬별 직접 작성 | AI 초안 → 사람 씬별 수정 | AI 작성 + 자체 리뷰 |
| **이미지 프롬프트** | 사람이 태그 직접 편집 | AI 제안 → 사람 미세 조정 | AI 생성 + 품질 자동 검증 |
| **이미지 생성** | 사람이 씬별 수동 생성 | 일괄 생성 → 사람이 골라냄 | AI 생성 + match_rate 자동 재생성 |
| **렌더링** | 설정 직접 조정 | AI 추천 설정 → 사람 확인 | 원클릭 렌더 |

> **핵심 원칙**: "AI 서포트를 통해 사람이 훌륭한 작품을 만든다." AI는 도구이며, 사람이 창작의 주체.
> 사람은 자신이 집중하고 싶은 단계는 Manual/Assisted로, 반복 작업은 Delegated로 위임할 수 있다.

### 2-2. 핵심 가치

| 가치 | 설명 |
|------|------|
| **반복 개선** | 한 번에 완성이 아닌, 생성 → 검토 → 수정 루프 |
| **메모리** | 세션 간 학습. "이 캐릭터는 이런 톤이 잘 맞았다" 기억 |
| **Checkpoint** | 어디서든 중단/재개 가능. 네트워크 끊김에도 안전 |
| **Human-in-the-loop** | 핵심 결정 포인트에서 사용자 승인/수정 개입 |
| **파이프라인 통합** | Script Generation과 Creative Lab을 하나의 그래프로 통합 |
| **제어 스펙트럼** | 단계별 Manual/Assisted/Delegated 독립 설정. 사람이 창작 주체 |

---

## 3. 아키텍처 설계 (결정: 2026-02-13)

### 3-1. 기술 스택

| 컴포넌트 | 선택 | 비고 |
|----------|------|------|
| **워크플로우 엔진** | LangGraph (`langgraph` + `langchain-core` 자동 포함) | 풀 LangChain 불필요, LangGraph만 최소 설치 |
| **LLM Provider** | Gemini — 기존 `google-genai` 유지 | 노드 안에서 기존 호출 래핑. LangChain wrapper 전환 불필요 |
| **Checkpointer** | `AsyncPostgresSaver` (langgraph-checkpoint-postgres) | 기존 PostgreSQL 활용, `setup()` 자동 테이블 생성 |
| **Memory Store** | `AsyncPostgresStore` (langgraph-store-postgres) | 키-값 기반 장기 메모리. Phase 1: 키 조회, Phase 2: 벡터 검색(pgvector) |
| **Observability** | LangFuse (셀프호스팅, Docker) | Phase 0에서 도입. 전용 PostgreSQL DB 분리, `docker-compose.langfuse.yml` |
| **Frontend 연동** | SSE (기존 패턴 재활용) | LangGraph `astream` → SSE 변환. Human-in-the-loop 재개는 POST |
| **메시지 큐** | Phase 0-1: 불필요 (asyncio 충분) | Phase 4 분산 실행 시 Redis/Celery 검토 |

### 3-2. 인프라 결정 사항

| # | 질문 | 결정 | 근거 |
|---|------|------|------|
| D1 | LangFuse DB | **별도 PostgreSQL** | LangFuse 자체 마이그레이션 실행 → 비즈니스 DB와 분리. LangGraph Checkpoint/Store는 기존 DB 공유 |
| D2 | Docker Compose | **별도 `docker-compose.langfuse.yml`** | 독립 서비스, 필요 시에만 기동 |
| D3 | DB 커넥션 풀 | **기본 `max_connections=100`** | SQLAlchemy 풀 5 + LangGraph 풀 5 + LangFuse = 여유. 로컬 개발 환경 충분 |

### 3-3. Phase 1 설계 결정 사항

| # | 질문 | 결정 | 근거 |
|---|------|------|------|
| D4 | Review 노드 평가 | **규칙 + Gemini 혼합**: 규칙 기반(길이/태그/구조) 먼저 → 통과 시 Gemini 스킵, 실패 시 Gemini 평가 | 비용 절감 (대부분 규칙만으로 충분) |
| D5 | 제어 모드 | **단계별 3모드**: Manual (사람 직접) / Assisted (AI 초안→사람 검토) / Delegated (AI 자동, 확신 낮을 때만 interrupt). 단계별 독립 설정 | 전역 quick/full 이분법 → 단계별 세분화 |
| D6 | Jinja2 템플릿 | **기존 유지** (노드에서 `render_template()` 호출) | 검증된 템플릿 6종 재활용, 전환 리스크 제거 |
| D7 | API 호환 전략 | **기존 `/scripts/generate` 내부를 Graph로 교체** (request/response 계약 유지) | Frontend 변경 최소화 |
| D8 | Thread ID | **`storyboard_id`를 thread_id로 사용** | 자연스러운 매핑, 별도 ID 관리 불필요 |
| D9 | Graph 실행 모드 | **`astream` SSE** (stream_mode=`["custom", "updates"]`) | 기존 SSE 패턴 재활용, 노드 진행 실시간 표시 |
| D10 | Script 탭 모드 통합 | **Manual 탭 제거 → Quick/Full 단일 모드**. Quick=Graph 2노드(Draft→Finalize), Full=Phase 1.5 확장 노드. `useScriptEditor` 제거, `useShortsSession` 통합 | UI 이원화 해소, "항상 Graph" 원칙(Q5) 실현 |

### 3-4. 스트리밍 전략

| 레벨 | 구현 | UX | Phase |
|------|------|-----|-------|
| **노드 진행률** | `get_stream_writer()` + SSE ("Research → Draft(3/5) → Review") | 어떤 단계 실행 중인지 실시간 표시 | **Phase 1** |
| **씬 단위** | JSON 파싱 후 씬마다 emit | 씬이 하나씩 카드에 나타남 | Phase 1 후반 검토 |
| ~~토큰 스트리밍~~ | ~~`generate_content_stream`~~ | ~~부분 JSON 표시 불가~~ | **불채택** (구조화 JSON 출력이라 UX 가치 없음) |

> **근거**: Gemini 응답이 구조화 JSON (씬 배열 + 태그)이므로 토큰 단위 스트리밍은 의미 없음. 노드 진행률 스트리밍이 실용적.

### 3-5. 제어 분기 로직

각 단계(concept/script/prompts/images/render)에서 `PipelineControl` 값에 따라 분기:

- **Manual**: `interrupt()` → 빈 템플릿/편집 UI 제공 → 사람이 직접 작성/수정
- **Assisted**: AI가 초안 생성 → `interrupt()` → 사람이 검토/승인/수정
- **Delegated**: AI가 생성 + 자체 리뷰 → `quality_score ≥ auto_review_threshold`면 자동 통과, 미달 시 자동 Revise (최대 `MAX_REVISIONS`회). 모든 자동 수정 실패 시 fallback으로 `interrupt()`

> **Pause / Take Over**: Delegated 실행 중에도 사람이 언제든 개입 가능 (`interrupt` 강제 트리거).

### 3-2. State 설계 (초안)

```python
class PipelineControl(TypedDict):
    concept: Literal["manual", "assisted", "delegated"]
    script: Literal["manual", "assisted", "delegated"]
    prompts: Literal["manual", "assisted", "delegated"]
    images: Literal["manual", "assisted", "delegated"]
    render: Literal["manual", "assisted", "delegated"]

class ScriptState(TypedDict):
    # 입력
    topic: str
    duration: int
    structure: str  # Monologue / Dialogue / NarratedDialogue
    language: str
    character_ids: list[int]

    # 제어 스펙트럼
    control: PipelineControl          # 단계별 개입 수준
    current_phase: str                # 현재 실행 단계
    auto_review_threshold: float      # 0.7 — Delegated 자동 통과 기준

    # 중간 상태
    research_brief: str | None
    draft_scenes: list[dict] | None
    review_feedback: str | None
    revision_count: int               # 최대 MAX_REVISIONS=2

    # 메모리 참조
    memory_context: list[dict]

    # 최종
    final_scenes: list[dict] | None
    quality_score: float | None
```

### 3-3. 그래프 구조 (초안)

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           ↓
                    ┌─────────────┐
                    │  Research   │ ← Memory Store 조회
                    └──────┬──────┘   (캐릭터 히스토리, 성공 패턴)
                           ↓
                    ┌─────────────┐
                    │   Draft     │ ← Gemini 대본 생성
                    └──────┬──────┘
                           ↓
                    ┌─────────────┐
              ┌─────│   Review    │ ← 품질 평가 (자동)
              │     └──────┬──────┘
              │            ↓
         score < 0.7  score >= 0.7
              │            ↓
              │     ┌─────────────┐
              │     │ Human Gate  │ ← interrupt() 사용자 확인
              │     └──────┬──────┘
              │            ↓
              ↓       approve / revise
        ┌──────────┐       │
        │  Revise   │←──revise
        └──────┬───┘
               │
               ↓ (max 3회)
          Draft로 복귀

              approve
                ↓
        ┌─────────────┐
        │  Finalize    │ ← 태그 후처리, 검증
        └──────┬──────┘
               ↓
        ┌─────────────┐
        │   Learn     │ → Memory Store 저장
        └──────┬──────┘   (결과 + 사용자 피드백)
               ↓
            ┌──────┐
            │  END │
            └──────┘
```

---

## 4. 단계별 마이그레이션 계획

> **원칙**: "동등 전환 먼저, 기능 확장은 안정화 후." Phase 1은 기존 파이프라인과 동일한 출력을 보장하는 것이 유일한 목표.

### Phase 0: Foundation (1-2일)

**목표**: "LangGraph가 기존 코드 위에서 동작하는가?" 검증.

| # | 작업 | 비고 | 상태 |
|---|------|------|------|
| 1 | `langgraph` + `langgraph-checkpoint-postgres` + `psycopg[binary]` 의존성 추가 | psycopg2와 공존 (별도 네임스페이스). **Store/LangFuse는 제외** | [x] |
| 2 | AsyncPostgresSaver 설정 (기존 DATABASE_URL 재사용, `setup()` 자동 테이블) | Alembic autogenerate에서 LangGraph 테이블 exclude. DB 테이블 4개 생성 확인 | [x] |
| 3 | 기존 `/scripts/generate` 입출력 스냅샷 10건 확보 | `tests/snapshots/` 10건 (3구조×3언어×다양한 파라미터). 회귀 테스트 23건 PASS | [x] |
| 4 | 최소 PoC: 2-노드 그래프 (Draft → Finalize) + Checkpoint 재개 확인 | 단위 3건 + Integration 1건 PASS. FastAPI lifespan 초기화 완료 | [x] |

**Phase 0 DoD**: PoC 그래프가 기존 Gemini 호출을 래핑하여 동일 JSON 출력 생성. Checkpoint로 중단/재개 동작.

**Phase 0에서 제외** (PM 판단):
- ~~AsyncPostgresStore~~ → Phase 2 Memory와 함께
- ~~LangFuse Docker~~ → Phase 2 Observability와 함께. Phase 0-1은 Python `logging` + `time.perf_counter()`로 충분

### Phase 1: 동등 전환 (3-5일) — **완료** (2026-02-15)

**목표**: "기존 Autopilot과 동일하게 동작한다." 새 기능 없음. 기존 API 계약 100% 유지.

| # | 작업 | 비고 | 상태 |
|---|------|------|------|
| 1 | `ScriptState` TypedDict 확정 (최소 필드만) | `mode: "quick"` 단일 모드로 시작. PipelineControl 5단계는 Phase 1.5 | [x] |
| 2 | Draft 노드 (`gemini_generator.py` 래핑) | **기존 Jinja2 템플릿 유지**, `render_template()` 호출 | [x] |
| 3 | Review 노드 (**규칙 기반만**: 길이/태그/구조 검증) | Gemini 평가는 Phase 1.5. 규칙 통과 시 자동 진행 | [x] |
| 4 | Finalize 노드 (태그 후처리) | 기존 후처리 로직 그대로 재활용 | [x] |
| 5 | `/scripts/generate` 내부를 Graph로 교체 | **API 계약 유지** (request/response 동일), `storyboard_id` = thread_id | [x] |
| 6 | SSE 노드 진행률 스트리밍 | `/scripts/generate-stream` SSE 엔드포인트, `astream(stream_mode="updates")` | [x] |
| 7 | 스냅샷 10건 회귀 테스트 통과 | Backend 1,567 passed (13 skipped) | [x] |
| 8 | Script 탭 모드 통합 (Manual→Quick + AI Agent 유지) | `useScriptEditor` SSE 전환 + progress 상태. Quick/AI Agent 탭 유지 (Full 모드 UI는 Phase 1.5) | [x] |

**Phase 1 DoD**: 기존 Autopilot 동작이 LangGraph 위에서 동일하게 작동. Backend 테스트 전량 통과. Script 탭 Manual→Quick 명칭 변경 + SSE 진행률 바 추가. AI Agent 모드(Lab Creative Sessions)는 Phase 1.5 흡수까지 유지.

**Phase 1에서 제외** (PM 판단):
- ~~Research 노드~~ → Memory Store 없이 의미 없음 → Phase 2
- ~~Revise 노드~~ → 반복 루프는 Phase 1.5
- ~~Human Gate (interrupt)~~ → Assisted/Manual 모드는 Phase 1.5
- ~~PipelineControl 5단계~~ → YAGNI. Phase 1.5에서 Preset 3개로 시작

---

### Phase 1.5: 기능 확장 — 반복 개선 + 제어 스펙트럼 (2-3일)

**목표**: 동등 전환 안정화 후, 새 기능 추가. "AI가 자동 수정" + "사람이 검토" 패턴 도입.

| # | 작업 | 비고 | 상태 |
|---|------|------|------|
| 1 | Revise 노드 + Review → Revise → Draft 루프 | `MAX_REVISIONS=2`, 규칙 + Gemini 혼합 평가 | [ ] |
| 2 | Human Gate (`interrupt`) — Assisted 모드 | `mode:"full"` = interrupt, `mode:"quick"` = 기존 동작 | [ ] |
| 3 | Full 모드 Graph 확장 (기존 Creative Lab Debate→Pipeline 흡수) | Quick(2노드) + Full(7노드: Research→Debate→Draft→Review→Revise→Finalize→Learn) | [ ] |
| 4 | Preset 3개 Backend: Full Auto / Creator / Manual | `mode` 파라미터 1개로 시작. 5단계 세분화는 각 단계 Graph화 시 추가 | [ ] |
| 5 | reasoning 필드 추가 (Gemini 출력에 `narrative_function`, `why`, `alternatives`) | Jinja2 템플릿 수정만. 추가 Gemini 호출 없음 | [ ] |
| 6 | Frontend: Quick/Full 모드 선택 UI + 승인/수정 + [왜?] 읽기 전용 표시 | Script 탭에 모드 토글 + reasoning 패널 | [ ] |
| 7 | Frontend: Preset 선택 드롭다운 | Script Generator에 preset 선택 추가 | [ ] |

**Phase 1.5 DoD**: Quick/Full 모드 선택 가능. Full 모드에서 Review→Revise 루프 + Human Gate 동작. [왜?] 버튼으로 씬별 AI 판단 근거 확인 가능.

**Phase 1.5에서 제외**:
- ~~Explain Node (대화형 Q&A)~~ → 범위 제외. 1단계(읽기 전용 reasoning)만 포함
- ~~PipelineControl 5단계 커스텀~~ → Preset 3개로 시작, 커스텀은 향후 필요 시

### Phase 2: Memory + Observability (3-5일)

**목표**: 세션 간 학습 + 실행 추적 인프라.

| # | 작업 | 비고 | 상태 |
|---|------|------|------|
| 1 | `langgraph-store-postgres` 의존성 + AsyncPostgresStore 설정 | 키-값 기반 장기 메모리 | [ ] |
| 2 | LangFuse Docker 셀프호스팅 + LangGraph 콜백 연동 | 별도 `docker-compose.langfuse.yml`, 전용 PostgreSQL | [ ] |
| 3 | Memory 네임스페이스 설계 + Research 노드 (Memory 조회) | `("character", id)`, `("user", "preferences")` 등 | [ ] |
| 4 | Learn 노드 (결과 + 사용자 피드백 → Memory 저장) | 최소 범위: 성공/실패 패턴 + 사용자 수정 이력 | [ ] |
| 5 | 피드백 수집 UI (생성 결과에 좋아요/수정) | Frontend | [ ] |
| 6 | Memory 관리 API (조회/삭제) | Manage 페이지 | [ ] |

**Phase 2 DoD**: 10회 이상 생성 후 Memory 기반 품질 향상 확인. LangFuse에서 노드별 실행 트레이스 조회 가능.

### Phase 3: Creative 재평가 (Phase 2 완료 후 결정)

**목표**: 데이터 기반으로 Creative Lab 향후 방향 결정. "전환"이 아닌 "재평가".

Phase 2 완료 시점에 아래 질문에 답한 후 결정:
- Creative Lab이 실제로 사용되고 있는가? (`activity_logs` 기준)
- Script Generation Graph만으로 충분하지 않은가?
- 전환 비용 (10파일 2,651줄 재작성) 대비 레거시 유지 비용이 높은가?

| 선택지 | 조건 |
|--------|------|
| **A: Graph 서브그래프 전환** | Creative Lab 활발 사용 + Script Graph로 불충분 |
| **B: 레거시 유지** | 사용 빈도 낮지만 삭제 리스크 있음 |
| **C: 폐기** | 사용 빈도 매우 낮음 + Script Graph로 대체 가능 |

### Phase 4: 고도화 (잔여)

| # | 작업 | 상태 |
|---|------|------|
| 1 | 5단계 PipelineControl 커스텀 UI (Preset → 단계별 세분화) | [ ] |
| 2 | 분산 실행 (Redis/Celery 큐 연동) | [ ] |
| 3 | A/B 테스트 (그래프 버전 분기) | [ ] |
| 4 | Self-improving 에이전트 (메모리 기반 프롬프트 자동 최적화) | [ ] |

### Phase 5: Script Quality & AI Transparency (설계 완료: 2026-02-17)

**목표**: 대본 품질을 높이고, AI 생성 과정을 투명하게 만들어 사용자가 효과적으로 피드백할 수 있게 한다.
**설계 근거**: 4-Agent 크로스 분석 합의 — Multi-draft(3x) 반대, Concept Gate 방식 채택.
**명세**: [SCRIPT_QUALITY_UX.md](SCRIPT_QUALITY_UX.md)

| Sub-Phase | 핵심 | 주요 작업 | 상태 |
|-----------|------|----------|------|
| **5A. Narrative Quality** | 서사 품질 | Hook 구조 가이드(템플릿), `NarrativeScore` 평가(Review 확장), 서사 피드백→Revise 주입. Hook(40%)+감정(25%)+반전(20%)+톤(10%)+정합성(5%) | [ ] |
| **5B. Concept Gate** | 컨셉 선택 | Critic 3컨셉 사용자 노출, `concept_gate` 노드(Creator: interrupt, Full Auto: pass-through), Writer가 선택된 컨셉으로 생성. 14→15노드 | [ ] |
| **5C. AI Transparency** | 투명성 UX | Pipeline Stepper(노드별 진행 시각화), Agent Reasoning 확장 패널, Narrative Score 바 차트, Explain 결과 표시 개선 | [ ] |
| **5D. Interactive Feedback** | 피드백 | Human Gate 프리셋 피드백 버튼 5종(후킹 강화/더 극적으로/톤 변경/짧게 줄이기/직접 수정), Concept Gate 피드백(선택/재생성/직접입력) | [ ] |

**Phase 5 설계 결정 사항** (2026-02-17):

| # | 질문 | 결정 | 근거 |
|---|------|------|------|
| D11 | Multi-draft vs Concept Gate | **Concept Gate** | 같은 템플릿에서 3개 뽑아도 다양성 부족. 비용/지연 3배. 컨셉(1-2줄) 비교가 전체 대본 비교보다 효율적 |
| D12 | 서사 평가 위치 | **Review 노드 확장** (별도 노드 X) | 기존 규칙 검증 후 서사 평가 순차 실행. 노드 수 증가 최소화 |
| D13 | 서사 평가 대상 모드 | **Full 모드만** | Quick 모드는 비용 절감 목적이므로 추가 Gemini 호출 배제 |
| D14 | 피드백 방식 | **프리셋 우선 + 자유 입력 보조** | 사용자가 "뭘 수정할지 모르는" 문제 해결. 원클릭으로 structured feedback 주입 |
| D15 | Concept Gate 적용 범위 | **Creator만 interrupt, Full Auto는 자동** | Full Auto의 "완전 자동" 약속 유지 |

---

## 5. 아키텍처 결정 사항 (Decided: 2026-02-13)

### 아키텍처 레벨

| # | 질문 | 결정 | 근거 |
|---|------|------|------|
| Q1 | LangChain 의존성 범위 | **A: LangGraph만** | `langchain-core`는 자동 포함. 풀 LangChain 체인/에이전트 추상화 불필요 |
| Q2 | Gemini 호출 방식 | **A: google-genai 유지** | 기존 Jinja2 템플릿 6종 + 후처리 재활용. 노드에서 래핑만 |
| Q3 | 기존 Creative 테이블 | **C: 점진적 deprecated** | Phase 0-2는 병행, Phase 3에서 Graph 서브그래프로 통합 |
| Q4 | Frontend 연동 | **A: SSE** | 기존 렌더링/이미지 SSE 패턴 재활용. 양방향 불필요 |
| Q5 | 단일 생성도 Graph? | **A: 항상 Graph** | 이원화 방지. quick 모드는 Graph 내 조건 분기 (Review/Revise 스킵) |
| Q9 | Observability | **LangFuse (셀프호스팅)** | 로컬 인프라 원칙 유지. **Phase 2에서 도입** (Phase 0-1은 Python logging) |

### 비용/성능 레벨

| # | 질문 | 결정 | 근거 |
|---|------|------|------|
| Q6 | Gemini 호출 증가 | **최대 3회** (Draft 1 + Revise 2) | `MAX_REVISIONS=2`. 쇼츠 렌더링 대비 Gemini 비용 미미 |
| Q7 | Checkpoint 빈도 | **매 노드** (기본값) | 노드당 DB write 1회, 오버헤드 무시 가능 |
| Q8 | Memory 쿼리 지연 | **Phase 1: 키 기반** (< 10ms) → **Phase 2: 벡터 검색** | pgvector는 필요 시 도입 |

---

## 6. 영향 범위

### Phase별 영향 범위

**Phase 0-1 (동등 전환)**:

| 파일/모듈 | 변경 내용 |
|-----------|----------|
| `pyproject.toml` | `langgraph`, `langgraph-checkpoint-postgres`, `psycopg[binary]` 추가 |
| `services/agent/` (신규) | `graph_manager.py`, `script_graph.py`, `nodes/draft.py`, `nodes/review.py`, `nodes/finalize.py` |
| `services/script/gemini_generator.py` | Draft 노드에서 래핑 (기존 코드 유지, 노드가 호출) |
| `routers/scripts.py` | 내부를 Graph 실행으로 교체 (API 계약 유지) |
| `config.py` | LangGraph 관련 상수 (`MAX_REVISIONS`, `AUTO_REVIEW_THRESHOLD` 등) |
| Alembic `env.py` | LangGraph 자동 생성 테이블 exclude 처리 |
| Frontend Script 탭 | Manual/AI Agent 탭 분리 제거 → Quick 단일 모드 UI. `useScriptEditor` 제거, `useShortsSession` 통합. SSE 진행률 추가 |

**Phase 1.5 (기능 확장)**:

| 파일/모듈 | 변경 내용 |
|-----------|----------|
| `services/agent/nodes/revise.py` (신규) | Revise 노드 + Review→Revise 루프 |
| `services/agent/nodes/human_gate.py` (신규) | `interrupt()` 기반 Human-in-the-loop |
| `services/agent/nodes/debate.py` (신규) | Creative Lab Debate 로직 Graph 노드화 (Full 모드 전용) |
| Jinja2 템플릿 | `reasoning` 필드 출력 지시 추가 |
| Frontend Script 탭 | Quick/Full 모드 토글 + 승인/수정 UI + [왜?] 읽기 전용 패널 + Preset 드롭다운 |

**Phase 2 (Memory + Observability)**:

| 파일/모듈 | 변경 내용 |
|-----------|----------|
| `pyproject.toml` | `langgraph-store-postgres`, `langfuse` 추가 |
| `docker-compose.langfuse.yml` (신규) | LangFuse + 전용 PostgreSQL |
| `services/agent/nodes/research.py` (신규) | Memory Store 조회 |
| `services/agent/nodes/learn.py` (신규) | Memory Store 저장 |
| Frontend | 피드백 수집 UI (좋아요/수정) |

### DB 변경

| 테이블 | Phase | 비고 |
|--------|-------|------|
| `langgraph_checkpoints` (자동) | Phase 0 | AsyncPostgresSaver `setup()` 시 생성 |
| `langgraph_store` (자동) | Phase 2 | AsyncPostgresStore `setup()` 시 생성 |
| `creative_sessions` | Phase 3 재평가 | Phase 2까지 병행 |

---

## 7. 참고 자료

- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [LangGraph Persistence](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [LangGraph Memory Store](https://langchain-ai.github.io/langgraph/concepts/memory/)
- [LangGraph Human-in-the-loop](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)
- [LangFuse Self-Hosting](https://langfuse.com/docs/deployment/self-host)
- [LangFuse + LangGraph Integration](https://langfuse.com/docs/integrations/langchain/tracing)
