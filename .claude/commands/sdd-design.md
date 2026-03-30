# /sdd-design Command

SDD 태스크의 상세 설계를 작성하고 승인을 관리하는 명령입니다.
설계가 승인되어야 `/sdd-run`을 실행할 수 있습니다.

## 사용법

```
/sdd-design [SP-NNN]              # 설계 작성 (Phase 1-5)
/sdd-design [SP-NNN] approved     # 승인 → 자동 커밋 + /sdd-run 안내
/sdd-design [SP-NNN] reject [사유] # 수정 요청 → 설계 재작성
```

### 예시
```
/sdd-design SP-048                  # SP-048 설계 작성
/sdd-design SP-048 approved         # SP-048 설계 승인
/sdd-design SP-048 reject Q1 재검토  # SP-048 설계 수정 요청
```

## 인자 분기

ARGUMENTS를 파싱하여 동작 결정:

| 패턴 | 동작 |
|------|------|
| `SP-NNN` (액션 없음) | Phase 1-5: 설계 작성 |
| `SP-NNN approved` | Phase 6-A: 승인 처리 |
| `SP-NNN reject [사유]` | Phase 6-B: 수정 요청 처리 |

---

## Phase 1-5: 설계 작성

> `SP-NNN`만 전달된 경우 실행

### Phase 1: 태스크 로드

1. `.claude/tasks/current/SP-NNN_*/spec.md` 패턴으로 태스크 파일 매칭 (디렉토리 방식)
2. 디렉토리 미발견 시 fallback: `.claude/tasks/current/SP-NNN_*.md` (레거시 파일 방식)
3. 매칭 실패 시 안내 후 중단
4. `status`가 이미 `approved`/`running`/`done`이면 "이미 설계 승인됨" 안내 후 중단

### Phase 2: 코드 탐색

1. 태스크 파일의 **힌트**, **영향 분석**, **DoD** 섹션에서 관련 파일/함수 키워드 추출
2. 해당 파일들을 읽어서 현재 구현 상태 파악
3. 필요 시 Grep/Glob으로 연관 코드 추가 탐색

### Phase 3: 소크라테스식 질문 (Brainstorming)

코드를 읽은 후, 설계 전에 **모호하거나 판단이 필요한 부분**을 사용자에게 질문합니다.
질문은 **최대 3개**로 제한. 명확한 태스크는 질문 없이 바로 Phase 4로.

#### 결정 우선순위 (질문 전에 반드시 확인)

1. **FEATURES 명세 확인**: 태스크에 연결된 FEATURES 명세(`docs/01_product/FEATURES/*.md`)가 있으면, 해당 명세에서 결정 근거를 먼저 찾는다. 명세에 답이 있으면 **질문하지 않고 AI가 결정**한다.
2. **CLAUDE.md 규칙 확인**: 프로젝트 규칙에 답이 있으면 AI가 결정한다.
3. **코드 패턴 확인**: 기존 코드에서 동일한 패턴이 있으면 따른다.
4. **위 3가지에 답이 없는 경우만** 사용자에게 질문한다.

> 이 규칙으로 FEATURES 명세가 충분히 상세한 태스크는 질문 없이 설계가 완료된다. 태스크를 대량 생성해도 사용자 병목이 발생하지 않는다.

#### 질문 대상 (위 우선순위로 해결 불가한 경우만)
- UI/UX 동작에서 여러 선택지가 있는 경우 (토글 vs 토스트 vs 인라인 피드백)
- 엣지 케이스 처리 방향 (무시 vs 에러 vs fallback)
- 기존 코드와 충돌 가능성이 있는 설계 판단

질문 형식:
```
설계 전 확인이 필요합니다:

Q1. [구체적 상황] — A안 vs B안 중 어느 방향?
Q2. [엣지케이스] — 처리 방침은?
Q3. [영향 범위] — 기존 X 기능과의 관계는?
```

사용자 답변을 받은 후 Phase 4로 진행.

### Phase 4: 상세 설계 작성

각 DoD 항목에 대해 **6가지**를 작성:

1. **구현 방법**: 어떤 파일의 어떤 함수를 어떻게 수정 (시그니처 레벨)
2. **동작 정의**: before → after 상태 변화
3. **엣지 케이스**: 예외 상황 + 처리 방침
4. **영향 범위**: 사이드 이펙트 가능성
5. **테스트 전략**: RED 단계에서 작성할 테스트 (어떤 입력 → 어떤 출력 검증)
6. **Out of Scope**: 이번 항목에서 절대 건드리지 말 것

### 설계 깊이 기준

- 함수의 **시그니처**(이름, 입력, 출력)와 **상호작용**(호출 관계)까지만 설계
- 함수 내부 구현 로직(if문, 루프 등)은 AI TDD에 위임
- UI 변경 시: Loading/Empty/Error 등 모든 상태를 명시 (Happy Path만 쓰지 않는다)
- 기존 컴포넌트/유틸리티 재사용 지시를 명시 (새로 만들기 금지인 경우)

### Phase 4.5: 에이전트 설계 리뷰

설계 작성 후, **변경 영향 범위에 따라 관련 에이전트가 자동으로 설계를 리뷰**합니다.
리뷰 결과(이견/승인)를 반영한 뒤 사용자에게 제출합니다.

#### 리뷰어 자동 판단 기준

| 변경 감지 | 리뷰어 에이전트 | 검증 항목 |
|-----------|----------------|-----------|
| `models/*.py`, `alembic/`, DB 스키마 | **DBA** | 네이밍, FK/CASCADE, JSONB vs 정규화, DB_SCHEMA.md 반영 |
| `routing.py`, `state.py`, 노드 추가/삭제, 그래프 구조 | **Tech Lead** | 아키텍처 일관성, 기존 패턴 준수, 사이드 이펙트 |
| 외부 API 호출, timeout/retry/rate limit | **Performance Engineer** | 통신 안정성, 풀 설정, 에러 핸들링 |
| UI 컴포넌트, UX 흐름 | **UI/UX Engineer** | 사용성, 상태 누락 (Loading/Empty/Error), 접근성 |
| 프롬프트 변경, LangFuse 템플릿 | **Prompt Reviewer** | 태그 문법, Danbooru 준수, 프롬프트 품질 |

#### 반복 분석 횟수 (난이도 기반)

태스크 난이도에 따라 설계 리뷰를 반복합니다. 각 라운드에서 피드백을 반영한 뒤 다음 라운드를 실행합니다.

| 난이도 | 기준 | 리뷰 라운드 |
|--------|------|------------|
| 하 | 변경 파일 ≤3, 신규 함수 없음 | 생략 (기존과 동일) |
| 중 | 변경 파일 4~7, DB/API 변경 없음 | 2회 (리뷰 → 반영 → 재검증) |
| 상 | 변경 파일 8+ 또는 DB/API 변경 | 3회 (리뷰 → 반영 → 재검증 → 반영 → 최종 검증) |

각 라운드의 역할:
- **1차**: 구조적 결함, 누락 파일, 아키텍처 위반 탐지
- **2차**: 1차 반영 후 부작용 검증, 엣지 케이스 보완
- **3차** (상만): 최종 정합성 확인, 테스트 전략 완전성 점검

#### Gemini 자문 (난이도 중/상)

난이도 중 이상의 태스크는 에이전트 리뷰 전에 **Gemini MCP를 통해 설계 자문**을 받습니다.

**사용 도구**: `gemini-brainstorm` (Claude 분석 + Gemini 교차 검증)

```
gemini-brainstorm(
  prompt: "SP-NNN 설계 리뷰: [태스크 요약]. 아키텍처 결함, 누락된 엣지 케이스, 더 나은 대안이 있는지 검토해줘.\n\n[design.md 내용]",
  claudeThoughts: "Claude가 작성한 설계의 핵심 판단 근거와 우려 사항",
  maxRounds: 난이도 중=2 / 상=3
)
```

| 난이도 | Gemini 자문 | maxRounds | 활용 |
|--------|------------|-----------|------|
| 하 | 생략 | — | — |
| 중 | 실행 | 2 | 설계 보완 후 에이전트 리뷰 투입 |
| 상 | 실행 | 3 | 아키텍처 대안 탐색 + 설계 보완 후 에이전트 리뷰 투입 |

Gemini 피드백 중 유효한 지적은 design.md에 반영한 뒤 에이전트 리뷰로 넘깁니다.

#### 실행 방법

1. design.md의 **변경 파일 요약**에서 영향 범위를 파싱 → 난이도 판정
2. 난이도 중/상: **Gemini 자문** 실행 → 피드백 반영
3. 해당하는 리뷰어 에이전트를 **병렬 호출** (Agent 도구 사용)
4. 각 에이전트가 design.md를 읽고 이견/승인 판정
5. **WARNING/BLOCKER 피드백을 design.md에 자동 반영** (파일 수정 누락 추가, 엣지 케이스 보정, 문구 수정 등)
6. 난이도에 따라 **2~3 단계 반복** (반영 → 재검증 → 반영 → 최종 검증)
7. 반영 완료 후 리뷰 결과 요약을 Phase 5 출력에 포함 (라운드별 결과 + Gemini 자문 결과 포함)
8. 사용자에게는 **이미 피드백이 반영된 최종 설계**를 제출 — 별도 수동 반영 불필요

#### 자동 반영 규칙

- **BLOCKER**: 반드시 반영. 반영 불가 시 사용자에게 판단 위임 (설계 요약에 명시)
- **WARNING**: design.md에 자동 반영 (파일 목록 추가, 문구 수정, 엣지 케이스 보정 등)
- **PASS**: 반영 불필요. 결과 테이블에만 기록

#### 리뷰 결과 형식

```
## 설계 리뷰 결과 (난이도: 상 — Gemini 3라운드 + 에이전트 3라운드)

### Gemini 자문 (3라운드)
- R1: state 필드 추가 시 기존 체크포인트 호환성 확인 필요 → 반영
- R2: 라우팅 분기 단순화 제안 (enum 기반) → 채택
- R3: 테스트 픽스처 공유 전략 확인 → PASS

## 에이전트 설계 리뷰 결과 (난이도: 상 — 3라운드)

### Round 1
| 리뷰어 | 판정 | 주요 피드백 |
|--------|------|------------|
| DBA    | WARNING | tone 컬럼 nullable 누락 |
| Tech Lead | BLOCKER | 기존 라우팅 테스트 미반영 |

### Round 2 (1차 반영 후)
| 리뷰어 | 판정 | 주요 피드백 |
|--------|------|------------|
| DBA    | PASS | nullable 반영 확인 |
| Tech Lead | WARNING | 엣지 케이스 1건 추가 필요 |

### Round 3 (최종 검증)
| 리뷰어 | 판정 | 주요 피드백 |
|--------|------|------------|
| DBA    | PASS | — |
| Tech Lead | PASS | — |
```

#### 스킵 조건

- 난이도 하 (변경 파일 ≤3, 신규 함수 없음): 리뷰 생략
- 버그 수정(Hotfix)은 생략

### Phase 5: 설계 파일 생성 + 리뷰 요청

1. `.claude/tasks/current/SP-NNN_*/design.md` 파일에 설계 내용 작성 (spec.md와 동일 디렉토리)
2. 태스크 파일(spec.md)의 `## 상세 설계 (How)` 섹션에 `> [design.md](./design.md) 참조` 링크 추가
3. `status: pending` → `status: design` 변경 (spec.md + state.db 동기화: `sqlite3 "$(git worktree list | head -1 | awk '{print $1}')/.sdd/state.db" "INSERT INTO task_status (task_id, status, updated_at) VALUES ('SP-NNN', 'design', datetime('now')) ON CONFLICT(task_id) DO UPDATE SET status='design', updated_at=datetime('now');"` 실행)
4. 사용자에게 **설계 요약 + 에이전트 리뷰 결과** + 승인 명령어 안내:

```
설계 작성 완료. 리뷰해 주세요.

[설계 요약 테이블]

## 에이전트 설계 리뷰 결과
[리뷰 결과 테이블]

승인: /sdd-design SP-NNN approved
수정 요청: /sdd-design SP-NNN reject [사유]
```

---

## Phase 6-A: 승인 처리

> `SP-NNN approved`가 전달된 경우 실행

1. 태스크 파일 로드 → `status: design` 확인 (아니면 에러)
2. `status: design` → `status: approved` + `approved_at: YYYY-MM-DD` 기록 (spec.md + state.db 동기화: `sqlite3 "$(git worktree list | head -1 | awk '{print $1}')/.sdd/state.db" "INSERT INTO task_status (task_id, status, updated_at) VALUES ('SP-NNN', 'approved', datetime('now')) ON CONFLICT(task_id) DO UPDATE SET status='approved', updated_at=datetime('now');"` 실행)
3. 태스크 파일 + 설계 파일 main 커밋 (`chore: SP-NNN 설계 승인`)
4. `/sdd-run SP-NNN` 워크트리 실행 명령어 출력:

```
SP-NNN 설계 승인 완료.

워크트리에서 구현을 시작하려면:
! claude --worktree SP-NNN --dangerously-skip-permissions -p "/sdd-run SP-NNN"
```

## Phase 6-B: 수정 요청 처리

> `SP-NNN reject [사유]`가 전달된 경우 실행

1. 태스크 파일 로드 → `status: design` 확인
2. reject 사유를 기반으로 설계 파일의 해당 부분 수정
3. 수정된 설계 요약 출력 + 재승인 요청

---

## 주의사항

- 설계 단계에서는 코드를 수정하지 않는다 (읽기만)
- 질문은 최대 3개. 과도한 질문으로 사용자를 방해하지 않는다
- 설계 적정 깊이: Interface/Contract 레벨. 과잉 설계 금지
- 버그 수정(Hotfix/Sentry)은 이 명령 없이 바로 `/sdd-run` 가능
