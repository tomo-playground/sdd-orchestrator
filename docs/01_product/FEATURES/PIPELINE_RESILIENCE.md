# Pipeline Resilience — Agentic AI 기반 파이프라인 견고성 개선

**상태**: Phase 28 — 진행 중 (Phase A 착수)
**선행**: Phase 27 (Chat System UX), [AGENTIC_PIPELINE.md](AGENTIC_PIPELINE.md)
**근거**: 파이프라인 플로우 검수 (2026-03-04) — 24개 이슈 발견, 실사용 캐릭터 배정 장애 재현

---

## 1. 배경

### 1-1. 현황 진단

19-노드 파이프라인은 **Happy Path에서는 안정적**이나,
빈 그룹·빈 씬·LLM 실패 등 **Edge Case에서 Silent Failure**가 발생한다.

```
Agentic AI 5대 요건 대비 현재 갭 (정성 평가):

 자율적 의사결정  ████████░░  빈 씬 생성 시 자체적으로 에러 판단 못함
 Tool Use         █████████░  안정
 Planning         █████████░  안정
 Self-Reflection  ██████░░░░  실패 시 원인 분석/복구 부재
 에이전트 소통     ███████░░░  프론트엔드에 실패 맥락 전달 부재
```

### 1-2. 핵심 문제: "Silent Failure Chain"

Writer가 0개 씬을 생성해도 error를 설정하지 않아,
Review → Director → Human Gate까지 빈 데이터가 전파되고,
사용자는 **"검토 대기 중 — AI가 0개 씬을 생성했습니다"** 를 보게 된다.

```
Writer(0개 씬) → Review(빈 입력 통과) → Checkpoint(빈 평가)
  → Cinematographer(빈 프롬프트) → Director(빈 승인) → Human Gate(0개 씬 검토)
```

Agentic 시스템이라면 Writer가 0개 씬을 인지하고 **자체적으로 재시도하거나 에러를 선언**해야 한다.

---

## 2. 개선 영역 (Agentic AI 5대 요건 기준)

### 2-1. 자율적 의사결정 강화 — Empty State Guard

**현상**: 빈 `draft_scenes`, 빈 캐릭터, None 입력이 다음 노드로 무조건 전달됨.
**원칙**: Agent는 자신의 출력이 유효한지 자체적으로 판단하고, 무효하면 재시도 또는 에러를 선언해야 한다.

| # | 위치 | 현재 | 개선 |
|---|------|------|------|
| 1 | `writer` → `draft_scenes: []` | error 미설정, review로 진행 | **자체 검증**: `len(scenes) == 0` → 1회 재시도 → 실패 시 `{"error": "빈 스크립트"}` |
| 2 | `route_after_writer` | error만 검사 | **빈 씬 검사** 추가: `not state.get("draft_scenes")` → finalize |
| 3 | `finalize` → `_resolve_characters_from_group` | 빈 그룹 → `(None, None)` 무조건 반환 | `(None, None)` 유지 + 경고 로깅 (다른 그룹 캐릭터 혼입 방지) |
| 4 | `cinematographer` → `_load_characters_tags` | None → 템플릿에 그대로 전달 | None → 빈 dict 폴백 + 로깅 |

**구현 난이도**: 낮음 (방어 코드 추가)
**영향 범위**: writer, routing, finalize, cinematographer

---

### 2-2. Self-Reflection 강화 — 실패 원인 분석 + 자동 복구

**현상**: 노드 실패 시 단순 fallback만 반환. 왜 실패했는지 맥락 없음.
**원칙**: Agent는 실패를 감지하면 원인을 분석하고, 가능하면 전략을 바꿔 재시도해야 한다.

| # | 위치 | 현재 | 개선 |
|---|------|------|------|
| ~~5~~ | ~~`director` 노드~~ | ~~LLM 실패 시 예외 미포착~~ | **이미 구현됨** — 2단계 try/except + 재시도 + `decision="error"` fallback 존재 (`director.py:83-216`) |
| 6 | `copyright_reviewer` fallback | 실패 시 `"PASS"` 반환 | `"WARN"` + `"fallback_reason": "api_error"` (거짓 안전 방지). **#14와 동시 구현 필수** |
| 7 | `finalize` 내 validator | `validate_controlnet_poses()` 등 try/except 없음 | 논리 그룹별 try/except 래핑 (non-fatal, `exc_info=True` 필수) |
| 8 | Production 3노드 fallback | `_FALLBACK_TTS/SOUND/PASS` 반환, 사유 미기록 | `fallback_reason` 필드 추가 (디버깅 + 관측성) |

**구현 난이도**: 중간 (각 노드별 에러 핸들링 추가)
**영향 범위**: copyright_reviewer, finalize, tts/sound_designer
**참고**: #5(Director)는 이미 구현 완료. #6은 #14(DECISION_MAP 보완)와 반드시 동시 구현해야 한다.

---

### 2-3. 에이전트 소통 강화 — SSE 관측성 + Frontend 방어

**현상**: 프론트엔드가 파이프라인 내부 상태를 충분히 못 받음. 빈 씬이어도 검토 UI 표시.
**원칙**: Agent는 사용자에게 진행 상황과 실패 맥락을 투명하게 전달해야 한다.

| # | 위치 | 현재 | 개선 |
|---|------|------|------|
| 9 | `_read_interrupt_state` | `if vals.get("draft_scenes"):` — 빈 리스트 falsy → SSE 누락 | `if vals.get("draft_scenes") is not None:` (None과 [] 구분) |
| 10 | `_NODE_RESULT_KEYS` | research, revise, human_gate 결과 SSE 미전달 | 누락 노드의 `node_result` 키 추가 |
| 11 | `ReviewApprovalPanel` | 0개 씬에서도 검토 UI 표시 | `scenes.length === 0` → 에러 메시지 표시 ("씬 생성에 실패했습니다") |
| 12 | Production fallback | 프론트엔드에서 fallback vs 정상 구분 불가 | `fallback_reason` 필드 UI 경고 배지 표시 |

**구현 난이도**: 낮음~중간
**영향 범위**: routers/scripts.py, ReviewApprovalPanel.tsx, PipelineStepCard.tsx

---

### 2-4. Guardrail 정합성 — 리비전 제한 + 라우팅 안전성

**현상**: 3종 리비전 카운터가 독립적이라 총 리비전 횟수가 통제되지 않음.
**원칙**: Agent의 자율 반복은 반드시 글로벌 상한이 있어야 하며, 예상치 못한 입력에 안전하게 반응해야 한다.

| # | 위치 | 현재 | 개선 |
|---|------|------|------|
| 13 | revision 카운터 3종 분리 | review(3) + checkpoint(3) + director(3) = 최대 9회 | **파생 계산 함수** `_total_revisions(state)` 도입 (state 필드 추가 없이 라우팅에서 합산). 상한 10회 |
| 14 | `_DIRECTOR_DECISION_MAP` | 미등록 decision → `finalize` 직행 (로깅 없음) | unknown decision 경고 로깅 추가. **#6과 동시 구현** (WARN→revise_copyright 경로 보장) |
| 15 | `director_checkpoint_score` | 음수(LLM 오류) → writer 강한 피드백으로 오분류 | `score < 0` → error 취급 → cinematographer 진행 |
| 16 | `director_plan_gate` | `vals.get("director_plan")` None 가능 → 프론트 빈 플랜 | `or {}` 폴백 적용 |

**구현 난이도**: 낮음 (파생 계산 함수는 state 스키마 변경 불필요)
**영향 범위**: routing.py, director_plan_gate
**설계 결정**: `total_revision_count` state 필드 추가 대신, 라우팅 함수 내 파생 계산 방식 채택 (DBA 리뷰 권고 — 카운터 동기화 실수 원천 방지)

---

### 2-5. 데이터 무결성 — State 필드 일관성 + 데이터 보존

**현상**: `character_id` vs `draft_character_id` 우선순위 불명확, reasoning 데이터 손실.
**원칙**: Agent 상태는 명확한 소유권 규칙이 있어야 하며, 중간 결과가 손실되면 안 된다.

| # | 위치 | 현재 | 개선 |
|---|------|------|------|
| 17 | `finalize` character_id 우선순위 | `character_id > draft_character_id` — 사용자 원본 우선 | `inventory_resolve`가 확정한 값이 SSOT. 주석으로 우선순위 명시 |
| 18 | `writer._extract_reasoning` | `scene.pop("reasoning")` — 원본 씬 mutate | 복사본에서 pop하여 원본 보존 (downstream 템플릿 혼입 방지) |
| 19 | `revision_history` | 무제한 누적 → 체크포인트 비대화 | 최근 N개(예: 5개)만 유지, 이전은 요약 |

**구현 난이도**: 낮음
**영향 범위**: finalize.py, writer.py, revise.py

---

## 3. 우선순위 매트릭스

사용자 체감 영향 × Agentic 원칙 부합도 기준:

| 우선순위 | 영역 | 개선 항목 | 사용자 체감 |
|----------|------|----------|------------|
| **P0** | 2-1 | Empty State Guard (#1~4) | 0개 씬 검토 게이트 해소 |
| **P0** | 2-3 | SSE + Frontend 방어 (#9, 11) | 빈 검토 화면 제거 |
| **P1** | 2-2 | Finalize validator 래핑 (#7) | 파이프라인 중단 방지 |
| **P1** | 2-2+2-4 | copyright WARN + DECISION_MAP (#6, #14) | 거짓 안전 방지 + 라우팅 정합성 (동시 구현 필수) |
| **P1** | 2-4 | 글로벌 리비전 파생 계산 (#13) | 무한 수정 루프 방지 |
| **P2** | 2-2 | Fallback reason 필드 (#8, 12) | 디버깅·관측성 향상 |
| **P2** | 2-3 | SSE 누락 노드 (#10) | 파이프라인 진행 가시성 |
| **P2** | 2-5 | State 필드 정합성 (#17~19) | 캐릭터 불일치 방지 |
| **P3** | 2-4 | 라우팅 엣지케이스 (#15~16) | 드문 케이스 안정성 |

> **참고**: #5(Director 에러 핸들링)는 이미 구현 완료 — 2단계 try/except + 재시도 + error fallback 존재

---

## 4. 구현 전략

### Phase A: Critical Guard (P0) — 예상 반나절

1. `writer`: 빈 씬 자체 검증 + 힌트 추가 1회 재시도 + error 설정
2. `route_after_writer`: `not state.get("draft_scenes")` 검사 추가
3. `_read_interrupt_state`: `is not None` 체크로 변경
4. `ReviewApprovalPanel`: 0개 씬 → 에러 메시지 + 승인 버튼 제거 (수정 요청만 유지)
5. `finalize._resolve_characters_from_group`: 빈 그룹 경고 로깅 강화
6. `cinematographer._load_characters_tags`: `None` → `{}` 폴백 (1줄)

### Phase B: Error Recovery (P1) — 예상 반나절

7. `finalize` validator 논리 그룹별 try/except 래핑 (`exc_info=True`)
8. `copyright_reviewer` fallback `"PASS"` → `"WARN"` + `fallback_reason`
9. `_DIRECTOR_DECISION_MAP` unknown decision 경고 로깅 (**#8과 동시 구현**)
10. 글로벌 리비전 파생 계산 `_total_revisions(state)` + 라우팅 상한 체크 (state 필드 추가 없음)

### Phase C: Observability (P2) — 예상 0.5일 (Phase B 이후)

11. `fallback_reason` 필드 표준화 (tts/sound)
12. `_NODE_RESULT_KEYS`에 research, revise 추가
13. Frontend fallback 경고 배지 + Production NODE_LABELS 추가

### Phase D: Data Integrity (P2~P3) — 예상 0.5일

14. `_extract_reasoning` 복사본에서 pop (원본 보존)
15. `director_checkpoint_score` 음수 → error 취급
16. `director_plan_gate` None → `{}` 폴백
17. `revision_history` 상한 (글로벌 카운터 도입 후 자동 제한되므로 우선순위 낮음)

> **Phase 의존성**: Phase B (#8 fallback_reason 정의) → Phase C (#11, #13 Frontend 소비). Phase C는 B 완료 후 진행.

---

## 5. 성공 기준 (DoD)

| 기준 | 측정 |
|------|------|
| Writer 빈 씬 → 에러 처리 | 0개 씬에서 "검토 대기 중" 표시 불가 |
| 전체 노드 에러 핸들링 | 어떤 노드가 실패해도 그래프 중단 없이 finalize 도달 |
| 글로벌 리비전 상한 | 총 리비전 10회 초과 불가 (3+3+3=9 기본 경로 + 여유 1회) |
| SSE 빈 씬 전달 | `draft_scenes: []` → 프론트엔드에 scenes 필드 포함 |
| Fallback 투명성 | fallback 발생 시 사유가 SSE + 프론트엔드에 표시 |

---

## 6. 테스트 시나리오

| 시나리오 | 검증 |
|----------|------|
| Writer가 0개 씬 반환 | 힌트 추가 1회 재시도 → 실패 시 에러 반환, human_gate 미도달 |
| group_id 있으나 캐릭터 0개 | topic_analysis 폴백 로드, finalize 경고 로깅 |
| Director LLM 2회 실패 | fallback error → finalize 정상 진행 (이미 구현 검증) |
| 3개 Production 노드 중 1개 실패 | 나머지 2개 정상 + 실패 노드 fallback + fallback_reason |
| 리비전 10회 도달 | 파생 계산 카운터 차단 → 강제 finalize |
| copyright_reviewer 실패 | "WARN" 반환 (거짓 "PASS" 방지) |
| Safety 재시도 후 빈 씬 | Safety 재시도 성공 후에도 빈 씬 검증 동작 확인 |
| Checkpoint 루프 내 빈 씬 | Checkpoint → Writer 재실행 → 0개 씬 → 가드 정상 동작 |
| Production 2개 이상 동시 실패 | Director가 복수 fallback 인지, 최종 판단 품질 확인 |

---

## 부록 A: 크로스 리뷰 반영 이력

| 리뷰어 | 주요 피드백 | 반영 |
|--------|-----------|------|
| **Tech Lead** | #5 Director 이미 구현됨 (오진단) | P1에서 제거, 이미 구현 표시 |
| **Tech Lead** | #6과 #14 의존성 — 동시 구현 필수 | #14를 P3→P1 승격, Phase B에서 #8+#9 묶음 |
| **Tech Lead** | 리비전 최대 15회 → 실제 9회 | `3+3+3=9`로 수정, 상한 8→10 |
| **DBA** | `total_revision_count` state 필드 대신 파생 계산 | `_total_revisions(state)` 함수 방식 채택 |
| **DBA** | DB 마이그레이션 불필요 확인 | 19개 항목 모두 Alembic 변경 없음 |
| **Backend** | #3 "전체 캐릭터 폴백"은 다른 그룹 혼입 위험 | `(None, None)` 유지 + 경고 로깅으로 변경 |
| **Backend** | #18 `get`으로 변경 시 downstream 혼입 | 복사본에서 pop 방식으로 변경 |
| **Frontend** | #11 승인 버튼 제거 + 수정 요청만 유지 | Phase A 구현 방향에 반영 |
| **Tech Lead** | 테스트 시나리오 3건 추가 | Safety+빈씬, Checkpoint 빈씬, 복수 실패 추가 |
| **Tech Lead** | Phase B→C 의존성 | Phase 의존성 화살표 추가 |

---

## 부록 B: 관련 버그 수정 이력

| 날짜 | 수정 | 커밋 |
|------|------|------|
| 2026-03-04 | `topic_analysis`: 빈 그룹 캐릭터 폴백 | `d1d64b82` |
| 2026-03-04 | `writer/revise`: `state["topic"]` KeyError 방어 | `d00ac5ae` |
| 2026-03-04 | `main.py`: Gemini Event loop 재초기화 | `d00ac5ae` |
| 2026-03-04 | `_validate_character`: int 변환 + 0 가드 | `d00ac5ae` |
