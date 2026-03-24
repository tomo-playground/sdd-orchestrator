# /sdd-coach Command

SDD 코치가 워크플로우 상태를 점검하고 액션을 제안하는 커맨드입니다.

## 사용법

```
/sdd-coach [action]
```

### Actions

| Action | 설명 |
|--------|------|
| (없음) | 전체 점검 (프로세스 준수 + PR 리뷰 사이클 + 병목 + 메트릭) |
| `audit` | 프로세스 준수 감사 — 설계 리뷰/DBA 리뷰/TDD 준수 위반 감지 |
| `review-cycle` | 열린 PR의 리뷰 코멘트 분석 → 수정 디스패치 |
| `bottleneck` | 병목 식별 — stuck PR, 블록된 태스크, 좀비 워크트리 |
| `metrics` | 메트릭 대시보드 — 사이클 타임, 리뷰 라운드, self-heal |
| `retro` | 회고 — Keep/Problem/Try 분석 + 메모리 저장 |

## 실행 에이전트

이 커맨드는 `sdd-coach` 에이전트로 실행하세요.

ARGUMENTS: $ARGUMENTS

---

## Action: (없음) — 전체 점검

아래 모든 항목을 순서대로 실행하고 대시보드로 출력합니다.

---

## Action: audit — 프로세스 준수 감사

### Step 1: current/ 태스크 점검

`.claude/tasks/current/` 디렉토리의 모든 태스크를 스캔합니다:

1. `status: design`인 태스크의 `design.md`에 **설계 리뷰 결과** 섹션이 있는지 확인
   - 없으면: `BLOCKER — 설계 리뷰 미실행`
   - 난이도 판정 (변경 파일 수)과 실제 리뷰 라운드 수 비교

2. `status: approved`인 태스크가 설계 리뷰를 거쳤는지 확인
   - design.md 없거나 리뷰 결과 없음: `BLOCKER — 리뷰 없이 승인됨`

3. DB/API 변경이 포함된 태스크의 DBA 리뷰 여부 확인
   - design.md에서 `models/`, `alembic/`, `DB`, `마이그레이션` 키워드 검색
   - 해당하면 DBA 리뷰 결과 확인

### Step 2: 열린 PR 점검

`gh pr list --state open`으로 모든 열린 PR 확인:

1. PR에 테스트 파일 변경이 있는지 확인 (`gh pr diff N --stat | grep test`)
   - 테스트 없음: `WARNING — RED 단계 누락 (TDD 위반)`

2. PR의 리뷰 상태 확인
   - `CHANGES_REQUESTED` + 1시간 경과: `WARNING — 리뷰 대응 지연`

3. models/alembic 변경이 있는 PR의 DB_SCHEMA.md 동기화 확인

### Step 3: 결과 출력

```
SDD Coach Audit Report
──────────────────────
프로세스 준수: X/Y 항목 PASS
  BLOCKER: [있으면 목록]
  WARNING: [있으면 목록]

TDD 준수: X/Y PR에 테스트 포함
  [누락 목록]

설계 리뷰 준수: X/Y 태스크 리뷰 완료
  [누락 목록]
```

---

## Action: review-cycle — 리뷰 사이클 자동화

### Step 1: CHANGES_REQUESTED PR 수집

```bash
gh pr list --state open --json number,title,reviewDecision
```

`reviewDecision == "CHANGES_REQUESTED"`인 PR만 필터링합니다.

### Step 2: 각 PR의 리뷰 코멘트 분석

각 PR에 대해:

1. `gh api repos/{owner}/{repo}/pulls/{N}/reviews`로 리뷰 읽기
2. `gh api repos/{owner}/{repo}/pulls/{N}/comments`로 인라인 코멘트 읽기
3. 각 코멘트를 분류:
   - **BLOCKER**: 런타임 크래시, 데이터 손실, 보안 이슈
   - **WARNING**: 잠재적 버그, 성능 이슈, 패턴 위반
   - **Nit**: 스타일, 네이밍, 코멘트 추가

### Step 3: 유효성 판단

각 지적에 대해 실제 코드를 확인합니다:
- 참조된 파일/라인을 Read로 읽기
- 이미 수정되었을 수 있음 (이전 push 확인)
- CLAUDE.md 규칙과 충돌하는 제안은 기각

### Step 4: 수정 디스패치

유효한 지적을 파일별로 분류 → 담당 에이전트에 수정 위임:
- `backend/` → backend-dev
- `frontend/` → frontend-dev
- `models/`, `alembic/` → dba (검증만)

### Step 5: 결과 보고

```
Review Cycle Report — PR #NNN
─────────────────────────────
리뷰어: claude[bot], coderabbitai[bot]
코멘트: BLOCKER 1건, WARNING 3건, Nit 2건
유효: 3건 (BLOCKER 1 + WARNING 2)
기각: 1건 (이미 수정됨)
수정 디스패치: backend-dev에 위임
```

---

## Action: bottleneck — 병목 식별

### 점검 항목

1. **Stuck PR**: `CHANGES_REQUESTED` > 1시간
2. **Blocked 태스크**: `depends_on` 선행 태스크 미완료
3. **좀비 워크트리**: 프로세스 없는 워크트리 디렉토리
4. **sdd-fix skipped**: 최근 workflow 로그에서 skipped 확인
5. **오케스트레이터 상태**: PID 확인 + 최근 로그 에러
6. **중복 프로세스**: 동일 태스크 다중 Claude 프로세스

### 출력

```
Bottleneck Report
─────────────────
Stuck PR: #188 (2.5h in CHANGES_REQUESTED) → 수정 디스패치 권장
Blocked: SP-023 (depends: SP-022 미머지) → SP-022 우선 머지 권장
Zombies: 0
Orchestrator: OK (PID 299878, Cycle #15)
```

---

## Action: metrics — 메트릭 대시보드

### 데이터 수집

1. `done/` 디렉토리에서 완료 태스크의 `approved_at` → PR `merged_at` 계산
2. PR별 `CHANGES_REQUESTED` 횟수 카운트
3. `.claude/retrospectives/` 에서 self-heal 기록 수집

### 출력

```
SDD Metrics Dashboard
─────────────────────
기간: 최근 7일

사이클 타임: 평균 1.8h (목표 < 2h) ✅
리뷰 라운드: 평균 2.1회 (목표 < 3회) ✅
self-heal: 평균 0.8회 (목표 < 2회) ✅
설계 리뷰 준수: 80% (목표 100%) ⚠️
머지 후 Sentry: 0건 (목표 0건) ✅
TDD RED 선행: 90% (목표 100%) ⚠️
```

---

## Action: retro — 회고

### Step 1: 데이터 수집

- 이번 세션 완료 PR/태스크
- 발생한 블로커 + 해결 방법
- 프로세스 위반 사례
- 메트릭 변화

### Step 2: Keep / Problem / Try 분석

- **Keep**: 잘 동작한 패턴 (반복할 것)
- **Problem**: 문제 + 근본 원인 (예: 설계 리뷰 누락 → 설계 에이전트가 Phase 4.5 건너뜀)
- **Try**: 구체적 개선 액션 (예: 설계 에이전트 프롬프트에 Phase 4.5 필수 체크 추가)

### Step 3: 저장

- `memory/feedback_sdd_retrospective_*.md` — 핵심 교훈 (중복 시 기존 업데이트)
- `.claude/retrospectives/YYYY-MM-DD.md` — 전체 회고 기록
