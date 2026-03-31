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

### 1. 에이전트 정리: 17개 → 7개

**삭제 (8개)** — 사용 이력 0, 38줄 래퍼, 또는 역할 중복:

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

**흡수 (2개)** — 에이전트가 아닌 자동화로 전환:

| 대상 | 방향 |
|------|------|
| `sdd-coach` | Phase 0에서는 유지. Phase 1 이후 프로세스 감시(용어 검증, 파일 역할 체크)를 on-stop.sh/CI로 이전 후 제거 검토 |
| `shorts-pm` | Planner/Initializer에 역할 흡수 |

**유지 (7개)** — Harness Triad 매핑:

| 에이전트 | 하네스 역할 |
|---------|-----------|
| `backend-dev` | Generator |
| `frontend-dev` | Generator (+ UI/UX 흡수) |
| `dba` | Generator |
| `ffmpeg-expert` | Generator |
| `prompt-engineer` | Generator (+ prompt-reviewer 흡수) |
| `tech-lead` | Evaluator (+ 보안/성능 루브릭) |
| `qa-validator` | Evaluator (+ 미디어 체크리스트) |

### 2. 하네스 강화 Phase 정의

#### Phase 0. 컨텍스트 격리

- 에이전트 파일 삭제/흡수 (위 표)
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
- on-stop.sh에 `passes` 전체 true 검증 추가
- Sprint Contract: 하나라도 false → 전체 실패

**1b. Initializer/Coding Agent 2단계 분리:**

features.json 생성 흐름: **사람이 spec.md에 DoD 작성 → Initializer가 DoD를 JSON Feature List로 변환 + 검증 steps 세분화**

기존 sdd-run 흐름:
```
sdd-run → worktree 생성 → Claude Code 실행 → on-stop.sh → PR
```

변경 후:
```
sdd-run → worktree 생성
  → [Initializer] spec.md DoD → features.json 변환 + claude-progress.txt + init.sh 생성 → 커밋
  → [Coding Agent] progress.txt 읽기 → 다음 feature 1개 선택 → init.sh → smoke test → 구현 → 커밋 → on-stop.sh
  → PR
```

Initializer와 Coding Agent는 같은 worktree에서 순차 실행되나, **별도 컨텍스트**(별도 프로세스 또는 context reset)로 동작.

#### Phase 2. Evaluator 물리 분리

3-에이전트 Triad:

```
[Initializer]          [Generator]              [Evaluator]
 spec → features.json   worktree 구현             별도 프로세스 (read-only)
 1회                    on-stop.sh 기계적 검증     Playwright MCP 앱 테스트
                        feature별 커밋             API 직접 호출 + DB 검증
                                                  few-shot 캘리브레이션 기준
                                                  → eval-report.json 출력
```

Evaluator = 코드 리뷰가 아님. **실행 중인 앱을 사용자처럼 테스트**.

#### Phase 3. 병렬 에이전트 실행

- 매 세션 시작 전 `git commit -m "checkpoint"` 자동화 (안전망)
- 독립 태스크 → 별도 worktree + 별도 프로세스
- git lock 기반 태스크 클레임
- `--fast` 테스트 샘플링 (시간 인지 불능 대응)
- 1인 개발 환경이므로 네트워크 격리/컨테이너화는 Phase 2 효과 검증 후 필요 시 도입

### 3. 하네스 진화 원칙

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
- 에이전트 17 → 7: 관리 부채 제거, 역할 명확화
- Evaluator 분리: 자기 평가 편향 해소, 품질 천장 돌파
- 세션 Init: 컨텍스트 낭비 제거, 세션 간 연속성
- JSON Feature List: DoD 임의 축소 방지

### Negative
- Phase 2(Evaluator)은 Playwright MCP 설정 + few-shot 튜닝 필요
- Phase 3(병렬)은 충돌 해결 전략 복잡
- 에이전트 삭제 시 CLAUDE.md 워크플로우 룰 동기화 필요

### Cost
- Evaluator 분리 = 태스크당 Claude 프로세스 추가 호출 → 비용 증가
- Anthropic 사례: Solo $9/20분 vs Full harness $200/6시간 (20x)
- 트레이드오프: 전체 태스크에 적용하지 않고, 복잡도 높은 태스크(멀티 파일, 크로스 레이어)에만 Evaluator 적용으로 비용 제어

### Risk
- Evaluator 품질: "Out of the box, Claude is a poor QA agent" — 캘리브레이션 없이 도입하면 효과 미미
- 과도한 하네스: 모델 개선으로 불필요해질 컴포넌트에 과투자 가능 → 진화 원칙으로 대응
