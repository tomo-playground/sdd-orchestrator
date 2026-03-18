# LangFuse Scoring 시스템 도입

**상태**: 계획
**목표**: 파이프라인 품질 점수를 LangFuse에 기록하여 추적/비교/회귀감지
**리뷰**: Tech Lead PASS(조건부) / PM 승인 / QA 보완 요청 → 반영 완료

---

## 배경

### 기존 계획
- `SYSTEM_OVERVIEW.md`: 아키텍처에 "LangFuse v3 (Trace/Span/Score)" 명시
- `LANGFUSE_PROMPT_OPS.md`: "LangFuse Score 연동 — 별도 명세로 분리"로 보류
- NarrativeScore, Research Score 등이 내부 로직에서만 사용, LangFuse 기록 0건

### LangFuse 공식 Evaluation Method

| 방법 | 설명 | 적합도 |
|------|------|--------|
| **SDK/API Score** | 코드에서 프로그래밍 방식으로 기록 | ✅ **1순위** |
| **LLM-as-Judge** | LLM이 출력물을 평가 | △ 참고용 (NarrativeScore) |
| **Annotation Queue** | 구조화된 리뷰 워크플로우 | ✗ 향후 (팀 확장 시) |

---

## Score 설계 원칙

### 신뢰도 기반 Tier 분류

| Tier | 소스 | 신뢰도 | 활용 |
|------|------|--------|------|
| **Tier 1** | 코드 결정론적 측정 | 높음 | 절대값 비교, 회귀 감지 |
| **Tier 2** | LLM 자기평가 | 낮음 | 추이 비교만 (절대값 무의미) |
| **Tier 3** | 실제 시청자 데이터 | 최고 | Ground truth (향후) |

> **`research_quality` 주의**: Tier 1이지만 키워드 매칭 기반 휴리스틱이므로, 대시보드 해석 시 다른 Tier 1 지표보다 신뢰도 낮음.

---

## Score 목록

### Tier 1: 객관적 지표

| Score Name | 타입 | 범위 | 소스 | 기록 시점 |
|-----------|------|------|------|----------|
| `first_pass` | BOOLEAN | true/false | Review 1차 통과 여부 | Review |
| `revision_count` | NUMERIC | 0~6 | `state["revision_count"]` (Writer→Review 루프 횟수 단독) | Finalize |
| `scene_count` | NUMERIC | 1~30 | `len(final_scenes)` (후처리 완료 후) | Finalize |
| `visual_qc_issues` | NUMERIC | 0~20 | `len(qc.get("issues", []))` | Cinematographer |
| `script_qc_issues` | NUMERIC | 0~20 | `len(script_qc.get("issues", []))` | Review |
| `research_quality` | NUMERIC | 0.0~1.0 | `state["research_score"]["overall"]` | Research |
| `director_revision_count` | NUMERIC | 0~3 | `state["director_revision_count"]` (Director가 revise 판정한 횟수) | Director |
| `pipeline_duration_sec` | NUMERIC | 0~600 | `time.time() - start_time` | Finalize |

> **`pipeline_mode`**: Score가 아닌 trace metadata로 기록 (CATEGORICAL은 LangFuse 대시보드 활용도 낮음)

### Tier 2: LLM 자기평가

| Score Name | 타입 | 소스 | comment |
|-----------|------|------|---------|
| `narrative_overall` | NUMERIC (0~1) | NarrativeScore.overall | 8차원 세부 JSON |

comment 예시:
```json
{"hook":0.8,"emotional_arc":0.7,"twist_payoff":0.6,"speaker_tone":0.9,
 "script_image_sync":0.7,"spoken_naturalness":0.8,"retention_flow":0.7,"pacing_rhythm":0.75}
```

### Tier 3: 실제 시청자 데이터 (향후)

| Score Name | 타입 | 소스 |
|-----------|------|------|
| `youtube_retention_rate` | NUMERIC | YouTube Analytics API (게시 후 7일) |
| `youtube_like_ratio` | NUMERIC | 좋아요/조회수 비율 |

> PM 리뷰: 1인 개발 환경에서 자기 평가 별점은 Tier 2와 동급. YouTube 실제 데이터가 진정한 Ground truth.

---

## Score Config (코드 SSOT + LangFuse UI 등록)

```python
# config_pipelines.py — SSOT
LANGFUSE_SCORE_CONFIGS = {
    "first_pass": {"data_type": "BOOLEAN"},
    "revision_count": {"data_type": "NUMERIC", "min": 0, "max": 6},
    "scene_count": {"data_type": "NUMERIC", "min": 1, "max": 30},
    "visual_qc_issues": {"data_type": "NUMERIC", "min": 0, "max": 20},
    "script_qc_issues": {"data_type": "NUMERIC", "min": 0, "max": 20},
    "research_quality": {"data_type": "NUMERIC", "min": 0, "max": 1},
    "director_revision_count": {"data_type": "NUMERIC", "min": 0, "max": 3},
    "pipeline_duration_sec": {"data_type": "NUMERIC", "min": 0, "max": 600},
    "narrative_overall": {"data_type": "NUMERIC", "min": 0, "max": 1},
}
```

코드가 SSOT. LangFuse UI에도 동일하게 등록. 향후 스타트업 시 API 자동 동기화 검토.

---

## Sprint 구성

### Sprint A: 인프라 + 테스트
| # | 항목 | 파일 |
|---|------|------|
| A-1 | `record_score(name, value, data_type, comment)` 헬퍼 | `observability.py` |
| A-2 | `_current_trace_id` contextvar 자동 참조 (LangGraph 파이프라인 경로만) | `observability.py` |
| A-3 | 예외 처리 정책: try/except 전체 감싸기, 실패 시 warning 로그 + 파이프라인 미중단 | `observability.py` |
| A-4 | trace_id=None, 네트워크 장애, 범위 초과 시 graceful skip | `observability.py` |
| A-5 | `LANGFUSE_SCORE_CONFIGS` 상수 정의 | `config_pipelines.py` |
| A-6 | `create_langfuse_handler()`에서 trace metadata에 `pipeline_mode` 기록 | `observability.py` |
| A-7 | LangFuse UI에 Score Config 9개 등록 | LangFuse UI |
| A-8 | `record_score` 단위 테스트 (연결/미연결/trace_id 없음/범위 초과) | `tests/` |

### Sprint B: Tier 1 + Tier 2 Score 기록 + 테스트
| # | 항목 | 파일 | 테스트 |
|---|------|------|--------|
| B-1 | Review → `first_pass` + `script_qc_issues` | `nodes/review.py` | mock 호출 검증 |
| B-2 | Review → `narrative_overall` (comment에 8차원 JSON) | `nodes/review.py` | JSON 직렬화 검증 |
| B-3 | Finalize → `revision_count` + `scene_count` + `pipeline_duration_sec` | `nodes/finalize.py` | mock 호출 검증 |
| B-4 | Cinematographer → `visual_qc_issues` | `nodes/cinematographer.py` | mock 호출 검증 |
| B-5 | Research → `research_quality` | `nodes/research.py` | mock 호출 검증 |
| B-6 | Director → `director_revision_count` | `nodes/director.py` | mock 호출 검증 |
| B-7 | 기존 테스트 호환: `conftest.py`에 `record_score` autouse mock fixture | `tests/conftest.py` | 기존 ~120개 테스트 PASS 확인 |
| B-8 | 통합 테스트: 파이프라인 1회 실행 후 Score 9개 기록 확인 | `tests/` | |

---

## 예외 처리 정책 (Sprint A-3, A-4)

```python
def record_score(name: str, value: float | str | bool, *,
                 data_type: str = "NUMERIC", comment: str = "") -> None:
    """현재 trace에 score를 기록한다. 실패 시 파이프라인 미중단."""
    if not _ensure_initialized() or _langfuse_client is None:
        return  # LangFuse 비활성
    trace_id = _current_trace_id.get()
    if not trace_id:
        return  # trace context 밖에서 호출
    try:
        _langfuse_client.create_score(
            trace_id=trace_id,
            name=name,
            value=value,
            data_type=data_type,
            comment=comment or None,
        )
        logger.debug("[LangFuse] Score 기록: %s=%s (trace=%s)", name, value, trace_id[:16])
    except Exception as e:
        logger.warning("[LangFuse] Score 기록 실패 (non-fatal): %s=%s, %r", name, value, e)
```

| 시나리오 | 동작 |
|----------|------|
| LangFuse 비활성 | `_ensure_initialized()` False → 즉시 return |
| trace_id=None | contextvar None → 즉시 return |
| 네트워크 장애 | try/except → warning 로그 + 계속 |
| 범위 초과 | LangFuse 서버측 처리 (거부 시 warning) |
| SDK rate limit | 동일 — warning + 계속 |

---

## 활용 시나리오

### 1. 프롬프트 변경 효과 측정
```
Phase 37 적용 전: first_pass rate=60%, revision_count 평균=2.1
Phase 37 적용 후: first_pass rate=80%, revision_count 평균=1.3
→ 한국어 구어체 강화 효과 정량 입증
```

### 2. 회귀 감지
```
프롬프트 v5 배포 → visual_qc_issues 급증 (0.5 → 2.3)
→ 대시보드에서 즉시 감지 → 롤백 판단
```

### 3. 모드별 품질 비교
```
pipeline_mode=full: first_pass 85%, narrative_overall 0.81
pipeline_mode=fasttrack: first_pass 65%, narrative_overall 0.72
→ FastTrack 품질 트레이드오프 정량화
```

### 4. ComfyUI 전환 검증 (향후)
```
Forge 베이스라인: visual_qc_issues 평균 1.2
ComfyUI Phase A 후: visual_qc_issues 평균 0.8
→ 이미지 품질 개선 정량 입증
```
> PM 리뷰: 지금 도입하면 ComfyUI 전환 전 베이스라인이 자동 축적됨

---

## 완료 기준 (DoD)
- [ ] `record_score` 헬퍼 구현 + graceful skip 패턴
- [ ] Tier 1 Score 8개 + Tier 2 Score 1개 = 9개 기록
- [ ] 파이프라인 1회 실행 후 LangFuse Score 탭에 최소 9개 Score 표시
- [ ] FastTrack 모드에서도 `scene_count` + `revision_count` + `pipeline_duration_sec` 최소 3개 기록
- [ ] Score Config 9개 LangFuse UI에 등록
- [ ] 기존 Backend 테스트 전체 PASS (Score 기록 실패가 파이프라인 미중단)
- [ ] 신규 테스트 전체 PASS

## 모니터링
- 성공: `logger.debug("[LangFuse] Score 기록: %s=%s")`
- 실패: `logger.warning("[LangFuse] Score 기록 실패 (non-fatal): ...")`
- 점검: LangFuse UI Score 탭 → 최근 trace에 Score 존재 여부

## 의존성
- LangFuse v3 SDK `create_score` API — 설치됨
- `observability.py`의 `_current_trace_id` contextvar — 구현됨
- Phase 37 NarrativeScore 8차원 — 완료
- `LANGGRAPH_MAX_REVISIONS` 상수 — Score Config max와 동기화 필요

## 리뷰 반영 이력
| 리뷰어 | 핵심 피드백 | 반영 |
|--------|-----------|------|
| Tech Lead | `director_revisions` 정의 모호 (BLOCKER) | → `director_revision_count` (실제 수정 횟수)로 명확화 |
| Tech Lead | `pipeline_mode`는 trace metadata로 | → Score 목록에서 제거, A-6에서 metadata 기록 |
| Tech Lead | `pipeline_duration_sec`, `script_qc_issues` 추가 | → Tier 1에 추가 |
| Tech Lead | Sprint D를 B에 통합 | → 2-Sprint 구조로 변경 |
| PM | DoD 정량적 검증 기준 부재 | → "최소 9개 Score" + "FastTrack 최소 3개" 추가 |
| PM | `revision_count` 정의 명확화 | → "state.revision_count 단독 (Writer→Review 루프)" 명시 |
| PM | Tier 3 대안: YouTube Analytics | → Tier 3을 YouTube 데이터로 변경 |
| PM | 시나리오 4 축소 | → ComfyUI 전환 검증으로 변경 (현실적) |
| QA | Sprint D 테스트 3개→11개 | → Sprint B에 통합, 노드별 mock 검증 + 통합 테스트 |
| QA | 엣지 케이스 8개 미정의 | → 예외 처리 정책 섹션 신설 |
| QA | `scene_count` Config 누락 | → Config 목록에 추가 |
| QA | 기존 테스트 영향 (~120개) | → B-7에 conftest.py autouse fixture 명시 |
| QA | Config를 코드 SSOT로 | → `LANGFUSE_SCORE_CONFIGS` 상수 정의 (A-5) |
| QA | 모니터링 방법 부재 | → 모니터링 섹션 신설 |
