# LangFuse Scoring 시스템 도입

**상태**: 계획
**목표**: 파이프라인 품질 점수를 LangFuse에 기록하여 추적/비교/회귀감지

---

## 배경

### 기존 계획
- `SYSTEM_OVERVIEW.md`: 아키텍처 다이어그램에 "LangFuse v3 (Trace/Span/Score)" 명시
- `LANGFUSE_PROMPT_OPS.md`: "LangFuse Score 연동 — 별도 명세로 분리"로 보류
- NarrativeScore, Research Score 등이 내부 로직에서만 사용, LangFuse 기록 0건

### LangFuse 공식 가이드 — 4가지 Evaluation Method

| 방법 | 설명 | 적합도 |
|------|------|--------|
| **SDK/API Score** | 코드에서 프로그래밍 방식으로 기록 | ✅ **1순위** — 파이프라인 내부 지표 자동 기록 |
| **LLM-as-Judge** | LLM이 출력물을 평가 | △ 참고용 — NarrativeScore가 이미 이 역할 |
| **Annotation (UI)** | 팀원이 UI에서 수동 평가 | △ 향후 — 아직 1인 개발 |
| **Annotation Queue** | 구조화된 리뷰 워크플로우 | ✗ 향후 — 팀 확장 시 |

---

## Score 설계 원칙

### 신뢰도 기반 Tier 분류

**Tier 1: 객관적 지표 (NUMERIC/BOOLEAN)**
- 코드에서 결정론적으로 측정 가능
- 절대값에 의미 있음 (revision_count=0 → 1차 통과)
- 프롬프트/코드 변경의 효과를 정량적으로 입증

**Tier 2: LLM 자기평가 (NUMERIC, comment로 세부 기록)**
- Gemini가 자신의 결과물을 평가 → 절대값 신뢰 낮음
- **추이 비교에만 사용** (v3 평균 0.72 → v4 평균 0.81)
- comment 필드에 세부 차원 JSON 기록

**Tier 3: 사용자 피드백 (향후)**
- 영상 시청 후 별점/thumbs up/down
- Ground truth로서 가장 신뢰도 높음
- 개발 안정화 후 도입

---

## Score 목록

### Tier 1: 객관적 지표 (Sprint B)

| Score Name | 타입 | 범위 | 소스 | 기록 시점 | 활용 |
|-----------|------|------|------|----------|------|
| `first_pass` | BOOLEAN | true/false | Review 1차 통과 여부 | Review | 프롬프트 품질 지표 |
| `revision_count` | NUMERIC | 0~N | state.revision_count | Finalize | 재생성 비용 지표 |
| `scene_count` | NUMERIC | 1~N | len(scenes) | Finalize | 생성 규모 |
| `visual_qc_issues` | NUMERIC | 0~N | len(visual_qc.issues) | Cinematographer | 시각 품질 |
| `research_quality` | NUMERIC | 0.0~1.0 | research_score.overall | Research | 자료 수집 품질 |
| `director_revisions` | NUMERIC | 0~3 | len(reasoning_steps) | Director | Production 수정 횟수 |
| `pipeline_mode` | CATEGORICAL | quick/full/fasttrack | interaction_mode + skip_stages | Finalize | 모드별 품질 분석 |

### Tier 2: LLM 자기평가 (Sprint C)

| Score Name | 타입 | 소스 | comment 내용 |
|-----------|------|------|-------------|
| `narrative_overall` | NUMERIC | NarrativeScore.overall | 8차원 세부 JSON |

comment 예시:
```json
{"hook":0.8,"emotional_arc":0.7,"twist_payoff":0.6,"speaker_tone":0.9,
 "script_image_sync":0.7,"spoken_naturalness":0.8,"retention_flow":0.7,"pacing_rhythm":0.75}
```

### Tier 3: 사용자 피드백 (향후)

| Score Name | 타입 | UI | 기록 방법 |
|-----------|------|-----|----------|
| `user_rating` | NUMERIC (1~5) | Publish 탭 별점 | Frontend → Backend → LangFuse SDK |
| `user_thumbs` | BOOLEAN | 영상 재생 후 좋아요 | Frontend → Backend → LangFuse SDK |

---

## Score Config (LangFuse UI 설정)

LangFuse에서 Score Config를 사전 등록하면 값 범위 검증 + 대시보드 자동 구성이 됨.

| Config Name | Data Type | Min | Max | 설명 |
|-------------|-----------|-----|-----|------|
| `first_pass` | BOOLEAN | - | - | Review 1차 통과 |
| `revision_count` | NUMERIC | 0 | 10 | 재생성 횟수 |
| `visual_qc_issues` | NUMERIC | 0 | 20 | QC 경고 수 |
| `research_quality` | NUMERIC | 0 | 1 | 리서치 품질 |
| `director_revisions` | NUMERIC | 0 | 3 | Director 수정 |
| `narrative_overall` | NUMERIC | 0 | 1 | 서사 종합 (LLM 평가) |
| `pipeline_mode` | CATEGORICAL | - | - | quick/full/fasttrack |

---

## Sprint 구성

### Sprint A: 인프라 — Score 헬퍼 + Config 등록
| # | 항목 | 파일/위치 |
|---|------|----------|
| A-1 | `record_score(name, value, data_type, comment)` 헬퍼 | `observability.py` |
| A-2 | `_current_trace_id` contextvar에서 자동 trace_id 참조 | `observability.py` |
| A-3 | LangFuse 미연결 시 graceful skip (try/except) | `observability.py` |
| A-4 | LangFuse UI에서 Score Config 7개 등록 | LangFuse UI |

### Sprint B: Tier 1 객관적 지표
| # | 항목 | 파일 |
|---|------|------|
| B-1 | Review → `first_pass` (1차 통과 여부) | `nodes/review.py` |
| B-2 | Finalize → `revision_count` + `scene_count` + `pipeline_mode` | `nodes/finalize.py` |
| B-3 | Cinematographer → `visual_qc_issues` | `nodes/cinematographer.py` |
| B-4 | Research → `research_quality` | `nodes/research.py` |
| B-5 | Director → `director_revisions` | `nodes/director.py` |

### Sprint C: Tier 2 LLM 자기평가
| # | 항목 | 파일 |
|---|------|------|
| C-1 | Review → `narrative_overall` (comment에 8차원 JSON) | `nodes/review.py` |

### Sprint D: 테스트
| # | 항목 |
|---|------|
| D-1 | `record_score` 헬퍼 단위 테스트 (LangFuse 있을 때 / 없을 때) |
| D-2 | Review 노드에서 `first_pass` + `narrative_overall` 기록 호출 검증 |
| D-3 | Finalize 노드에서 `revision_count` 기록 호출 검증 |

---

## 활용 시나리오

### 1. 프롬프트 변경 효과 측정
```
Phase 37 적용 전: first_pass rate = 60%, revision_count 평균 = 2.1
Phase 37 적용 후: first_pass rate = 80%, revision_count 평균 = 1.3
→ 한국어 구어체 강화의 효과 정량 입증
```

### 2. 회귀 감지
```
프롬프트 v5 배포 → visual_qc_issues 급증 (평균 0.5 → 2.3)
→ 대시보드에서 즉시 감지 → 롤백 판단
```

### 3. 모드별 품질 비교
```
pipeline_mode=full: first_pass 85%, narrative_overall 0.81
pipeline_mode=fasttrack: first_pass 65%, narrative_overall 0.72
→ FastTrack의 품질 트레이드오프 정량화
```

### 4. 외부 평가 파이프라인 (향후)
```python
# LangFuse 공식 패턴: 배치로 trace를 가져와 외부 평가 실행
traces = langfuse.api.trace.list(tags="production", limit=100)
for trace in traces:
    eval = custom_evaluation(trace.output)
    langfuse.create_score(trace_id=trace.id, name="custom_eval", value=eval)
```

---

## 완료 기준 (DoD)
- [ ] LangFuse Score 탭에 파이프라인 실행별 점수 표시
- [ ] Tier 1: first_pass, revision_count, scene_count, visual_qc_issues, research_quality, director_revisions, pipeline_mode
- [ ] Tier 2: narrative_overall (comment에 8차원 JSON)
- [ ] Score Config 7개 LangFuse UI에 등록
- [ ] LangFuse 미연결 시 에러 없이 스킵
- [ ] 테스트 전체 PASS

## 의존성
- LangFuse v3 SDK `create_score` API — 설치됨
- `observability.py`의 `_current_trace_id` contextvar — 구현됨
- Phase 37 NarrativeScore 8차원 — 완료

## 참고
- LangFuse 공식 가이드: SDK/API Score가 자동화 파이프라인에 최적
- LLM-as-Judge는 "추이 비교"에만 유효, 절대값 신뢰 낮음
- `LANGFUSE_PROMPT_OPS.md` §비-목표에서 이 문서로 분리됨
