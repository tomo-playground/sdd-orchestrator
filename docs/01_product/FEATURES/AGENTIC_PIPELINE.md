# Agentic AI Pipeline (LangGraph Migration)

**상태**: 논의 중 (Discussion)
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

---

## 2. 목표 (To-Be)

### 2-1. 비전

```
Topic + Context
    ↓
[Research Node] ← Memory Store (과거 성공 패턴, 사용자 선호)
    ↓
[Draft Node] → [Review Node] → (품질 < 기준?) → [Revise Node] ↺
    ↓                                ↓
[Human Review] ← interrupt()     [Checkpoint] ← PostgreSQL Saver
    ↓
[Finalize Node] → 최종 대본
    ↓
[Learn Node] → Memory Store 업데이트
```

### 2-2. 핵심 가치

| 가치 | 설명 |
|------|------|
| **반복 개선** | 한 번에 완성이 아닌, 생성 → 검토 → 수정 루프 |
| **메모리** | 세션 간 학습. "이 캐릭터는 이런 톤이 잘 맞았다" 기억 |
| **Checkpoint** | 어디서든 중단/재개 가능. 네트워크 끊김에도 안전 |
| **Human-in-the-loop** | 핵심 결정 포인트에서 사용자 승인/수정 개입 |
| **파이프라인 통합** | Script Generation과 Creative Lab을 하나의 그래프로 통합 |

---

## 3. 아키텍처 설계 (논의 필요)

### 3-1. 기술 스택

| 컴포넌트 | 후보 | 논의 포인트 |
|----------|------|------------|
| **워크플로우 엔진** | LangGraph | LangChain 의존성 범위? 최소 설치 가능? |
| **LLM Provider** | Gemini (기존) | LangChain Gemini wrapper vs 직접 호출 유지? |
| **Checkpointer** | `PostgresSaver` (langgraph-checkpoint-postgres) | 기존 PostgreSQL 활용, 별도 테이블 |
| **Memory Store** | `PostgresStore` (langgraph-store) | 키-값 기반 장기 메모리 |
| **메시지 큐** | 미정 | BackgroundTask 유지? Celery? Redis Queue? |

### 3-2. State 설계 (초안)

```python
# 논의 필요: 어떤 필드가 State에 들어가야 하는지
class ScriptState(TypedDict):
    # 입력
    topic: str
    duration: int
    structure: str  # Monologue / Dialogue / NarratedDialogue
    language: str
    character_ids: list[int]

    # 중간 상태
    research_brief: str | None        # Research 노드 결과
    draft_scenes: list[dict] | None   # Draft 노드 결과
    review_feedback: str | None       # Review 노드 피드백
    revision_count: int               # 수정 횟수

    # 메모리 참조
    memory_context: list[dict]        # 장기 메모리에서 가져온 관련 경험

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

### Phase 0: Foundation (인프라 준비)

| # | 작업 | 논의 포인트 | 상태 |
|---|------|------------|------|
| 1 | LangGraph + langgraph-checkpoint-postgres 의존성 추가 | 버전 고정, 기존 의존성 충돌 확인 | [ ] |
| 2 | PostgresSaver 설정 (기존 DB 연결 재사용) | 별도 DB? 기존 DB 내 테이블? | [ ] |
| 3 | PostgresStore 설정 (장기 메모리 테이블) | 메모리 네임스페이스 설계 | [ ] |
| 4 | 최소 PoC: 단순 2-노드 그래프 (Draft → Review) 동작 확인 | - | [ ] |

**논의 필요**:
- [ ] LangGraph 버전: 최신 안정판 기준? (현재 0.3.x)
- [ ] 기존 `creative_sessions` / `creative_traces` 테이블과의 관계 — 병행? 마이그레이션?
- [ ] Gemini 호출: LangChain `ChatGoogleGenerativeAI` wrapper vs 기존 `google-genai` 직접 호출 유지?

### Phase 1: Script Generation Graph (핵심 파이프라인 전환)

| # | 작업 | 논의 포인트 | 상태 |
|---|------|------------|------|
| 1 | `ScriptState` TypedDict 확정 | 위 초안 기반 필드 논의 | [ ] |
| 2 | Research 노드 구현 (Memory Store 조회 + 캐릭터 컨텍스트 로드) | 기존 `_load_character_context` 재활용 | [ ] |
| 3 | Draft 노드 구현 (기존 Gemini 호출 래핑) | Jinja2 템플릿 유지? LangGraph prompt로 전환? | [ ] |
| 4 | Review 노드 구현 (자동 품질 평가) | 평가 기준: match_rate? 별도 Gemini 평가? 규칙 기반? | [ ] |
| 5 | Revise 노드 구현 (피드백 기반 재생성) | Review 결과를 Draft 프롬프트에 주입 | [ ] |
| 6 | Human Gate (interrupt) 구현 | Frontend SSE 연동 방식 | [ ] |
| 7 | Finalize 노드 (태그 후처리 파이프라인 이동) | 기존 후처리 로직 그대로 재활용 | [ ] |
| 8 | `/scripts/generate` 엔드포인트를 Graph 실행으로 교체 | 기존 API 계약 유지 (하위 호환) | [ ] |

**논의 필요**:
- [ ] Review 노드의 평가 방법 — Gemini 자체 평가? 규칙 기반? WD14 검증 연계?
- [ ] 수정 최대 횟수 (max_revisions) — 비용 vs 품질 트레이드오프
- [ ] Human Gate 범위 — 항상? 품질 낮을 때만? 설정 가능?
- [ ] Jinja2 템플릿 유지 여부 — LangGraph의 프롬프트 관리와 공존?

### Phase 2: Memory Layer (학습 시스템)

| # | 작업 | 논의 포인트 | 상태 |
|---|------|------------|------|
| 1 | Memory 네임스페이스 설계 | `character:{id}`, `style:{profile}`, `user:preferences` 등 | [ ] |
| 2 | Learn 노드 구현 (결과 + 피드백 → Memory 저장) | 어떤 정보를 기억할지 | [ ] |
| 3 | Research 노드에 Memory 조회 연결 | 유사도 검색? 키 기반? | [ ] |
| 4 | 사용자 피드백 수집 UI (Frontend) | 생성 결과에 좋아요/수정/코멘트 | [ ] |
| 5 | Memory 관리 API (조회/삭제/초기화) | Admin 페이지? 설정 페이지? | [ ] |

**논의 필요**:
- [ ] 메모리에 저장할 데이터 범위
  - 선택지 A: 최소 — 성공/실패 프롬프트 패턴만
  - 선택지 B: 중간 — + 캐릭터별 선호 스타일, 사용자 수정 이력
  - 선택지 C: 최대 — + 에피소드 기억 (시나리오 흐름, 감정 곡선 패턴)
- [ ] 메모리 만료 정책 — 무제한? TTL? 용량 제한?
- [ ] 기존 `activity_logs` 데이터를 초기 메모리로 마이그레이션?

### Phase 3: Creative Pipeline 통합 (선택)

| # | 작업 | 논의 포인트 | 상태 |
|---|------|------------|------|
| 1 | Creative Lab 토론을 LangGraph 서브그래프로 전환 | 기존 `creative_shorts.py` 대체 | [ ] |
| 2 | Production Pipeline을 LangGraph 서브그래프로 전환 | 기존 `creative_pipeline.py` 대체 | [ ] |
| 3 | Script Generation Graph와 Creative Graph 통합 | 단일 진입점, 모드 분기 | [ ] |
| 4 | 기존 커스텀 코드 제거 | creative_shorts.py, creative_pipeline.py deprecated | [ ] |

**논의 필요**:
- [ ] Creative Lab을 별도 유지할지, Script Generation에 흡수할지?
- [ ] 9-Agent 토론 구조를 LangGraph 서브그래프로 그대로 옮길지, 재설계할지?
- [ ] Phase 3는 Phase 1-2 안정화 후 진행? 동시 진행?

### Phase 4: 고도화 (장기)

| # | 작업 | 상태 |
|---|------|------|
| 1 | 멀티에이전트 병렬 실행 (LangGraph `Send` API) | [ ] |
| 2 | Streaming 출력 (LangGraph `astream_events`) | [ ] |
| 3 | 분산 실행 (Redis/Celery 큐 연동) | [ ] |
| 4 | A/B 테스트 (그래프 버전 분기) | [ ] |
| 5 | Self-improving 에이전트 (메모리 기반 프롬프트 자동 최적화) | [ ] |

---

## 5. 미결정 사항 (Open Questions)

### 아키텍처 레벨

| # | 질문 | 선택지 | 결정 |
|---|------|--------|------|
| Q1 | LangChain 의존성 범위 | A: LangGraph만 (최소) / B: LangChain Core 포함 / C: 풀 LangChain | 미정 |
| Q2 | Gemini 호출 방식 | A: 기존 `google-genai` 유지 / B: LangChain wrapper 전환 | 미정 |
| Q3 | 기존 Creative 테이블 처리 | A: 병행 운영 / B: LangGraph 체크포인트로 마이그레이션 / C: 점진적 deprecated | 미정 |
| Q4 | Frontend 연동 | A: SSE (기존 패턴) / B: WebSocket / C: Polling | 미정 |
| Q5 | 단일 대본 생성도 Graph 경유? | A: 항상 / B: "Quick" 모드는 기존 단일 호출 유지 | 미정 |

### 비용/성능 레벨

| # | 질문 | 논의 |
|---|------|------|
| Q6 | 반복 개선 시 Gemini 호출 증가 비용 | 현재 1회 → 최대 3-4회로 증가. 허용 범위? |
| Q7 | Checkpoint 저장 빈도 | 노드마다? 핵심 노드만? |
| Q8 | Memory Store 쿼리 지연 | 매 생성마다 메모리 조회 시 latency 증가 |

---

## 6. 영향 범위

### Backend 변경

| 파일/모듈 | 변경 내용 |
|-----------|----------|
| `requirements.txt` | `langgraph`, `langgraph-checkpoint-postgres` 추가 |
| `services/script/` | Graph 기반으로 재구성 |
| `services/creative_*.py` | Phase 3에서 Graph 서브그래프로 전환 |
| `routers/scripts.py` | Graph 실행 엔드포인트로 교체 |
| `models/` | Memory Store 테이블 (langgraph 자동 생성 또는 커스텀) |
| `config.py` | LangGraph 관련 상수 추가 |

### Frontend 변경

| 파일/모듈 | 변경 내용 |
|-----------|----------|
| Scripts 페이지 | Human-in-the-loop 리뷰 UI |
| SSE/WebSocket | Graph 실행 상태 스트리밍 |
| 피드백 UI | 생성 결과 평가 (Learn 노드 입력) |

### DB 변경

| 테이블 | 변경 |
|--------|------|
| `langgraph_checkpoints` (자동) | LangGraph PostgresSaver가 생성 |
| `langgraph_store` (자동) | LangGraph PostgresStore가 생성 |
| `creative_sessions` | Phase 3까지 병행, 이후 deprecated 검토 |

---

## 7. 참고 자료

- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [LangGraph Persistence](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [LangGraph Memory Store](https://langchain-ai.github.io/langgraph/concepts/memory/)
- [LangGraph Human-in-the-loop](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)
