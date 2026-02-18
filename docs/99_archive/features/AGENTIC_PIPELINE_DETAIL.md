# Agentic AI Pipeline — 상세 설계 원본 (아카이브)

> 요약: [FEATURES/AGENTIC_PIPELINE.md](../../01_product/FEATURES/AGENTIC_PIPELINE.md)
> 아카이브 일자: 2026-02-19
> 원본: Phase 9 마이그레이션 계획 상세 (State 설계, Phase 0~5 작업 목록, 영향 범위 등)

이 문서는 Phase 9 LangGraph 마이그레이션의 상세 설계 및 단계별 작업 계획 원본입니다.
Phase 9~10 전체 완료 후, 핵심 내용은 통합 명세로 이동하고 상세는 여기에 보존합니다.

---

## State 설계

```python
class PipelineControl(TypedDict):
    concept: Literal["manual", "assisted", "delegated"]
    script: Literal["manual", "assisted", "delegated"]
    prompts: Literal["manual", "assisted", "delegated"]
    images: Literal["manual", "assisted", "delegated"]
    render: Literal["manual", "assisted", "delegated"]

class ScriptState(TypedDict):
    topic: str
    duration: int
    structure: str
    language: str
    character_ids: list[int]
    control: PipelineControl
    current_phase: str
    auto_review_threshold: float
    research_brief: str | None
    draft_scenes: list[dict] | None
    review_feedback: str | None
    revision_count: int
    memory_context: list[dict]
    final_scenes: list[dict] | None
    quality_score: float | None
```

## 단계별 제어 매핑

| 단계 | Manual | Assisted | Delegated |
|------|--------|----------|-----------|
| **컨셉/주제** | 사람이 직접 입력 | AI가 3안 제시 → 사람 선택 | AI가 자동 선택 |
| **대본 작성** | 사람이 씬별 직접 작성 | AI 초안 → 사람 씬별 수정 | AI 작성 + 자체 리뷰 |
| **이미지 프롬프트** | 사람이 태그 직접 편집 | AI 제안 → 사람 미세 조정 | AI 생성 + 품질 자동 검증 |
| **이미지 생성** | 사람이 씬별 수동 생성 | 일괄 생성 → 사람이 골라냄 | AI 생성 + match_rate 자동 재생성 |
| **렌더링** | 설정 직접 조정 | AI 추천 설정 → 사람 확인 | 원클릭 렌더 |

## Phase별 영향 범위

### Phase 0-1 (동등 전환)

| 파일/모듈 | 변경 내용 |
|-----------|----------|
| `pyproject.toml` | `langgraph`, `langgraph-checkpoint-postgres`, `psycopg[binary]` 추가 |
| `services/agent/` (신규) | `graph_manager.py`, `script_graph.py`, `nodes/draft.py`, `nodes/review.py`, `nodes/finalize.py` |
| `services/script/gemini_generator.py` | Draft 노드에서 래핑 |
| `routers/scripts.py` | 내부를 Graph 실행으로 교체 |
| `config.py` | LangGraph 관련 상수 |
| Alembic `env.py` | LangGraph 자동 생성 테이블 exclude |
| Frontend Script 탭 | Manual → Quick 단일 모드 |

### Phase 1.5 (기능 확장)

| 파일/모듈 | 변경 내용 |
|-----------|----------|
| `services/agent/nodes/revise.py` | Revise 노드 + Review→Revise→Draft 루프 |
| `services/agent/nodes/human_gate.py` | `interrupt()` 기반 Human-in-the-loop |
| `services/agent/nodes/debate.py` | Creative Lab Debate 로직 Graph 노드화 |
| Jinja2 템플릿 | `reasoning` 필드 출력 지시 추가 |
| Frontend Script 탭 | Quick/Full 모드 토글 + 승인/수정 UI |

### Phase 2 (Memory + Observability)

| 파일/모듈 | 변경 내용 |
|-----------|----------|
| `pyproject.toml` | `langgraph-store-postgres`, `langfuse` 추가 |
| `docker-compose.langfuse.yml` | LangFuse + 전용 PostgreSQL |
| `services/agent/nodes/research.py` | Memory Store 조회 |
| `services/agent/nodes/learn.py` | Memory Store 저장 |
| Frontend | 피드백 수집 UI |

## DB 변경

| 테이블 | Phase | 비고 |
|--------|-------|------|
| `langgraph_checkpoints` (자동) | Phase 0 | AsyncPostgresSaver `setup()` 시 생성 |
| `langgraph_store` (자동) | Phase 2 | AsyncPostgresStore `setup()` 시 생성 |
| `creative_sessions` | Phase 3 | 폐기 결정 |

## Phase 5 설계 결정 사항

| # | 질문 | 결정 | 근거 |
|---|------|------|------|
| D11 | Multi-draft vs Concept Gate | **Concept Gate** | 같은 템플릿에서 3개 뽑아도 다양성 부족 |
| D12 | 서사 평가 위치 | **Review 노드 확장** | 기존 규칙 검증 후 서사 평가 순차 실행 |
| D13 | 서사 평가 대상 모드 | **Full 모드만** | Quick 모드는 비용 절감 목적 |
| D14 | 피드백 방식 | **프리셋 우선 + 자유 입력 보조** | 원클릭으로 structured feedback 주입 |
| D15 | Concept Gate 적용 범위 | **Creator만 interrupt** | Full Auto의 "완전 자동" 약속 유지 |
