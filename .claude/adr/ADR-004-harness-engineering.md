# ADR-004: Harness Engineering 도입

- **Status**: Proposed
- **Date**: 2026-03-31
- **References**: Anthropic Engineering Blog (3편), Gemini Deep Research 교차 검증

## Context

현재 SDD 자동화 시스템이 Anthropic이 정의한 "하네스 엔지니어링" 패턴을 부분적으로 실천하고 있으나, 핵심 갭이 존재.

### 현재 강점 (유지)
- `on-stop.sh`: 외부 검증(pytest/vitest) + 3회 self-heal — Anthropic "외부 검증" 패턴 정확 실천
- `auto-lint.sh`: PostToolUse 훅 자동 포맷 — context noise 감소
- worktree 격리 실행 — 메인 코드 오염 방지
- Task 라이프사이클 (`current/` → `done/`) — progress file 패턴 유사

### 핵심 갭
1. **사용 이력 0 에이전트 10개**: 관리 부채 + 평가 역할 8개로 분산 (Anthropic: Evaluator는 1개 + 멀티 루브릭)
2. **Generator/Evaluator 미분리**: 자기 결과물 자기 평가 → 품질 천장
3. **Evaluator가 코드 리뷰**: Anthropic 원문은 Playwright로 실제 앱 테스트
4. **세션 Init 루틴 부재**: 매 세션 "어디까지 했지?" 파악에 컨텍스트 낭비
5. **Feature List가 Markdown**: JSON이 에이전트 임의 변경 방지에 효과적
6. **Planner 에이전트 부재**: spec → 세부 feature 분해 담당자 없음

## Decision

### 1. 에이전트 정리: 17개 → 5개

**삭제 (10개)** — 사용 이력 0, 38줄 래퍼, 역할 중복, 또는 자동화로 대체:

| 삭제 대상 | 사유 |
|----------|------|
| `sound-reviewer` | 38줄 래퍼, 사용 이력 0 |
| `voice-reviewer` | 38줄 래퍼, 사용 이력 0 |
| `video-reviewer` | 38줄 래퍼, 사용 이력 0 |
| `prompt-reviewer` | 38줄 래퍼, prompt-engineer와 중복 |
| `security-engineer` | 사용 이력 0, tech-lead에 보안 루브릭 흡수 |
| `performance-engineer` | 사용 이력 0, tech-lead에 성능 루브릭 흡수 |
| `uiux-engineer` | 사용 이력 0, frontend-dev에 흡수 |
| `storyboard-writer` | 실제 호출 0, 콘텐츠 생성은 Gemini 파이프라인 담당 |
| `tech-lead` | on-stop.sh 기계적 게이트 + Evaluator(별도 claude 프로세스)로 대체 |
| `qa-validator` | 동일. 평가는 에이전트가 아닌 on-stop.sh 파이프라인이 담당 |

**흡수 (2개)** — 에이전트가 아닌 자동화로 전환:

| 대상 | 방향 |
|------|------|
| `sdd-coach` | Phase 0에서는 유지. Phase 1 이후 프로세스 감시(용어 검증, 파일 역할 체크)를 on-stop.sh/CI로 이전 후 제거 검토 |
| `shorts-pm` | Planner/Initializer에 역할 흡수 |

**유지 (5개)** — Generator 역할:

| 에이전트 | 비고 |
|---------|------|
| `backend-dev` | |
| `frontend-dev` | + UI/UX 흡수 |
| `dba` | |
| `ffmpeg-expert` | |
| `prompt-engineer` | + prompt-reviewer 흡수 |

**Initializer**: 별도 에이전트 불필요 — sdd-run 프롬프트 Step 1이 담당.
**Evaluator**: 별도 에이전트 불필요 — on-stop.sh에서 `claude -p`로 별도 프로세스 호출. 루브릭(코드 품질/보안/성능/미디어)은 프롬프트에 주입.

기존 `tech-lead`와 `qa-validator`는 삭제. 평가는 on-stop.sh(기계적 게이트) + Evaluator(별도 claude 프로세스)로 대체.

### 2. 하네스 강화 Phase 정의

#### Phase 0. 컨텍스트 격리

- 에이전트 파일 삭제/흡수 (위 표)
- **동기화 필수**: `.claude/agents/` 삭제 시 `sdd-orchestrator/templates/agents/`도 동기 삭제. 미삭제 시 `sdd-orchestrator init`가 재생성
- 한 세션에 **1개 역할만** 로드
- CLAUDE.md 워크플로우 룰 업데이트

#### Phase 1. JSON Feature List + 세션 Init + Progress 로그

**1a. Feature List 포맷 정의** (Coding Agent의 전제조건):

```json
{
  "features": [
    {
      "id": "F1",
      "category": "functional",
      "description": "씬 이미지 생성 API",
      "steps": [
        "POST /api/v1/scenes/{id}/generate → 200 + task_id",
        "폴링 후 이미지 URL 확인",
        "DB media_asset 레코드 확인"
      ],
      "passes": false
    }
  ]
}
```

- 에이전트는 `passes`만 수정 가능 (프롬프트 제어)
- on-stop.sh에서 `jq`로 원본 features.json의 `id`/`description`/`steps` 해시와 대조 → 임의 변경 감지
- on-stop.sh에 `passes` 전체 true 검증 추가
- Sprint Contract: 하나라도 false → 전체 실패
- Initializer가 `"complexity": "high" | "low"` 판별하여 주입 → Phase 2 Evaluator 적용 분기 기준
- **하위 호환**: features.json이 없는 태스크(기존 running, Hotfix/Sentry)는 검증 스킵. 기존 흐름 유지

**1b. Initializer → sdd-run 프롬프트 내 Step 1:**

features.json 생성 흐름: **사람이 spec.md에 DoD 작성 → sdd-run Step 1에서 DoD를 JSON Feature List로 변환 + 검증 steps 세분화**

오케스트레이터 `do_launch_sdd_run`은 **변경 없음**. 기존 CLI subprocess 그대로.

```
do_launch_sdd_run(task_id) → claude --worktree (변경 없음)
  CLI 내부 (/sdd-run 프롬프트):
    Step 1: spec.md DoD → features.json 변환 + progress.txt 초기화 → 커밋
    Step 2: progress.txt 읽기 → 다음 feature 1개 선택 → 구현 → feature별 커밋
    Step 3: on-stop.sh (기계적 게이트 + features.json 검증 + Evaluator)
  → PR
```

**핵심 설계**: 모든 단계가 **CLI subprocess 내부**에서 실행. 오케스트레이터 코드 변경 불필요.

#### Phase 2. Evaluator 물리 분리

**on-stop.sh 내부**에서 별도 Claude CLI 프로세스로 Evaluator 호출 (`complexity: high` 태스크만):

```
on-stop.sh 실행 흐름:
  Step 1: ruff/prettier (기존 lint)
  Step 2: pytest/vitest (기존 기계적 게이트)
  Step 3: features.json passes 전체 true 검증 (Phase 1)
  Step 4: complexity == "high" → Evaluator 호출 (Phase 2)
    └── claude -p "Playwright로 실행 중인 앱 테스트..." (별도 프로세스)
        → eval-report.json 출력
        → FAIL → exit 2 (기존 self-heal 3회 재시도)
```

Evaluator = 코드 리뷰가 아님. **실행 중인 앱을 사용자처럼 테스트**.

**왜 on-stop.sh 안인가** — 5가지 문제를 동시 해결:
1. worktree 수동 생성 불필요 — 기존 `claude --worktree` 그대로
2. 서버가 떠있음 — Generator 프로세스가 아직 살아있는 상태
3. cleanup 전 실행 — on-stop.sh가 exit 전에 실행되므로 worktree 존재
4. 재시도 자연스러움 — exit 2 → 기존 self-heal 로직 그대로 작동
5. 오케스트레이터 코드 변경 0 — `do_launch_sdd_run` 수정 불필요

**물리 분리 보장**: Evaluator는 `claude -p` 로 **별도 Claude 프로세스** 호출. Generator와 다른 컨텍스트 윈도우에서 실행되므로 자기 평가 편향 해소.

**테스트 환경**: Generator가 띄운 서버/DB가 그대로 사용 가능. 별도 seed/teardown 불필요.

#### Phase 3. 병렬 에이전트 실행 (보류 — Phase 2 효과 검증 후 결정)

> 1인 개발 환경에서 워크트리 병렬 코딩은 결합도 높은 프로젝트에서 merge 충돌 비용이 클 수 있음.
> 적용 범위를 "병렬 코딩"이 아닌 "병렬 검증/테스트"로 축소 검토.

- 매 세션 시작 전 `git commit -m "checkpoint"` 자동화 (안전망)
- 독립 태스크 → 별도 worktree + 별도 프로세스
- git lock 기반 태스크 클레임
- `--fast` 테스트 샘플링 (시간 인지 불능 대응)
- 네트워크 격리/컨테이너화는 필요 시 도입

### 3. state.db 상태 전이

기존 상태를 유지. 全단계가 CLI subprocess 내부에서 실행되므로 DB 상태 추가 불필요.

```
pending → design → approved → running → done/failed
                                 │
                                 └── CLI 내부: sdd-run Step 1(Init) → Step 2(구현) → on-stop.sh(검증+Evaluator)
                                     (로그로 추적, DB 상태 변경 없음)
```

### 4. 구현 수단

**오케스트레이터 변경 없음**. 모든 하네스 강화는 sdd-run 프롬프트와 on-stop.sh 확장으로 구현.

| Phase | 구현체 | 위치 | 오케스트레이터 영향 |
|-------|--------|------|------------------|
| Phase 0 | 파일 삭제 + CLAUDE.md 수정 | `.claude/agents/` + `sdd-orchestrator/templates/agents/` | 템플릿 동기 삭제 |
| Phase 1 Init | sdd-run 프롬프트 Step 1 추가 | `.claude/commands/sdd-run.md` (프로젝트측 수정. 범용 템플릿 `sdd-orchestrator/templates/commands/sdd-run.md`는 별도 판단) | 없음 |
| Phase 1 품질 게이트 | on-stop.sh 확장 (features.json 해시 + passes 검증) | `.claude/hooks/on-stop.sh` | 없음 |
| Phase 2 Evaluator | on-stop.sh에서 별도 `claude -p` 호출 | `.claude/hooks/on-stop.sh` | 없음 |

### 5. 하네스 진화 원칙

- 모델 메이저 릴리스마다 컴포넌트 1개씩 제거 실험
- "이 컴포넌트 없이도 품질 유지?" → Yes → 제거
- 하네스 = 모델 결함 보상 장치. 모델이 좋아지면 줄어야 함.

## Implementation Priority

| Phase | 난이도 | 효과 | 선행 조건 |
|-------|--------|------|----------|
| **0** | 낮음 | 높음 | 없음 (즉시) |
| **1** | 중간 | 높음 | Phase 0 |
| **2** | 중간 | **최고** | Phase 1 |
| **3** | 높음 | 중간 | Phase 2 효과 검증 후 |

## Consequences

### Positive
- 에이전트 17 → 5: 관리 부채 제거, Generator만 에이전트로 유지
- Evaluator = on-stop.sh 내 별도 claude 프로세스: 자기 평가 편향 해소, 품질 천장 돌파
- 오케스트레이터 변경 0: 모든 강화가 sdd-run 프롬프트 + on-stop.sh 확장
- 세션 Init: 컨텍스트 낭비 제거, 세션 간 연속성
- JSON Feature List: DoD 임의 축소 방지

### Negative
- Phase 2(Evaluator)은 Playwright MCP 설정 + few-shot 튜닝 필요
- Phase 2 Evaluator 추가로 on-stop.sh 실행 시간 수십 분 증가 가능 (complexity: high만)
- Phase 3(병렬)은 충돌 해결 전략 복잡
- 에이전트 삭제 시 CLAUDE.md 워크플로우 룰(Sub Agents, Workflow Rules, 설계 리뷰 참여 등 15건) 동기화 필요

### Cost
- Evaluator 분리 = 태스크당 Claude 프로세스 추가 호출 → 비용 증가
- Anthropic 사례: Solo $9/20분 vs Full harness $200/6시간 (20x)
- 트레이드오프: features.json의 `complexity: high` 태스크에만 Evaluator 적용으로 비용 제어. 판별은 Initializer가 수행

### Risk
- Evaluator 품질: "Out of the box, Claude is a poor QA agent" — 캘리브레이션 없이 도입하면 효과 미미
- 과도한 하네스: 모델 개선으로 불필요해질 컴포넌트에 과투자 가능 → 진화 원칙으로 대응
