# SDD + TDD 워크플로우 가이드

> **SDD (Spec-Driven Development) + TDD (Test-Driven Development)**
> 사람이 스펙과 실패 테스트를 쓰면, AI가 테스트를 GREEN으로 만들고 PR까지 자율 실행.
> **테스트가 곧 스펙이고, GREEN이 곧 완료.**
> 최종 업데이트: 2026-03-21

---

## 핵심 원칙

> "AI를 믿지 말고, 테스트를 믿어라."

- **사람**: 무엇을 만들지 정의 (스펙 + 실패 테스트)
- **AI**: 테스트가 통과하도록 구현 (추측 판단 불가 — GREEN/RED가 객관적)
- **Stop Hook**: 자동 검증 (모든 테스트 GREEN이면 통과, 아니면 self-heal)

### 왜 TDD + SDD인가?

| SDD만 | SDD + TDD |
|-------|-----------|
| DoD에 "테스트 통과" 작성 → 테스트 없으면 통과할 게 없음 | 실패 테스트가 곧 DoD — 객관적 완료 기준 |
| AI가 "구현 완료" 자기 판단 → 편향 | 테스트 GREEN = 완료, RED = 미완료 — 판단 불필요 |
| 리뷰에서 "이거 동작해?" 확인 필요 | 테스트가 동작을 증명 — 리뷰는 설계 품질에 집중 |
| 회귀 발견 어려움 | Stop Hook이 기존 테스트 자동 검증 — 회귀 즉시 감지 |

---

## 실행 흐름

```
[사람] backlog에 한 줄 등록
  ↓
[사람] 착수 결정 → 태스크 파일 + 실패 테스트 작성 (RED)
  ↓
[사람] 실패 테스트 확인 → main 커밋
  ↓
[사람] /sdd-run SP-NNN
  ↓
[Claude] 테스트를 GREEN으로 만드는 코드 작성 → Stop Hook 자동 검증
  ↓  RED → self-heal (최대 3회)
  ↓  ALL GREEN → 커밋 → push → PR 생성
  ↓
[병렬 리뷰]
  ├─ Claude 리뷰 (claude-review.yml) — 설계 품질 검증
  └─ CodeRabbit 리뷰 — 규칙 준수 검증
  ↓
[changes_requested 시]
  ↓
[Claude 자동 수정] (sdd-review.yml auto-fix) → push
  ↓
[재리뷰] Claude + CodeRabbit
  ↓
[사람] 머지 판단
  ↓
[GitHub Actions] sdd-sync → 태스크 done/ + 브랜치 삭제
```

---

## 역할 정의

### 사람 (SDD 오케스트레이터)

| 책임 | 산출물 |
|------|--------|
| 제품 방향 설정 | `ROADMAP.md` |
| 태스크 작성 | `.claude/tasks/current/SP-NNN_*/spec.md` (디렉토리 방식) |
| 기동 | `/sdd-run SP-NNN` |
| 머지 판단 | Claude + CodeRabbit 리뷰 결과 종합 |
| 규칙 유지보수 | `CLAUDE.md` |

### AI (Claude Code)

| 활동 | 자율 여부 | 워크플로우 |
|------|----------|----------|
| 코드 구현 | 풀 자율 | 로컬 (`/sdd-run`) |
| 테스트 작성 | 풀 자율 | 로컬 |
| 린트 + 포맷팅 | 자동 | Hook (`auto-lint.sh`) |
| 품질 게이트 | 자동 | Hook (`on-stop.sh`) |
| self-heal | 최대 3회 | Hook |
| 커밋 + push + PR | 풀 자율 | 로컬 |
| PR 리뷰 | 자동 | `claude-review.yml` |
| 리뷰 피드백 수정 | 자동 | `sdd-review.yml` auto-fix |
| @claude 수동 대응 | 자동 | `sdd-review.yml` manual |

### AI (CodeRabbit)

| 활동 | 동작 |
|------|------|
| PR 자동 리뷰 | PR 생성/push 시 자동, CLAUDE.md 기반 |
| changes_requested | 심각 이슈 시 → Claude 자동 수정 트리거 |
| incremental review | push 후 자동 재리뷰 |

---

## GitHub Actions 워크플로우

### 3-워크플로우 체계

| 워크플로우 | 트리거 | 역할 | Runner |
|----------|--------|------|--------|
| `claude-review.yml` | PR 생성/push | Claude 리뷰 (읽기 전용) | self-hosted |
| `sdd-review.yml` | 리뷰 코멘트 / `@claude` 멘션 | 코드 자동 수정 | self-hosted |
| `sdd-sync.yml` | PR 머지 | 태스크 정리 + 브랜치 삭제 | self-hosted |
| `sentry-patrol.yml` | 매일 09:00 KST / 수동 | Sentry 에러 → GitHub Issue 자동 생성 | self-hosted |

### claude-review.yml — PR 병렬 리뷰

```
PR push → Claude가 CLAUDE.md 기준으로 리뷰
        → 인라인 코멘트 + 전체 요약 (코드 수정 안 함)
        → CodeRabbit과 병렬 동작
```

### sdd-review.yml — 리뷰 자동 수정

**Job 1: auto-fix** (멘션 불필요)
```
CodeRabbit/Claude 리뷰 → changes_requested 감지
  → Claude가 코멘트 읽기 → 코드 수정 → 커밋 → push
  → CodeRabbit + Claude 재리뷰 (자동 핑퐁)
```

**Job 2: manual** (@claude 멘션)
```
사람이 @claude 멘션 → Claude가 요청 대응
  → 리뷰 수정, 질문 답변, 코드 변경 등
```

### sentry-patrol.yml — 에러 자동 수집

```
매일 09:00 KST (cron) 또는 /sentry-patrol (수동)
  → Sentry API (3개 프로젝트: backend/frontend/audio)
  → 최근 24시간 새 이슈 필터링
  → GitHub Issues (label:sentry) 중복 체크
  → 새 이슈만 gh issue create (label: sentry, bug)
```

**봇 필터**:
- `[bot]` suffix 코멘트 → 워크플로우 스킵 (무한 루프 방지)
- `cancel-in-progress: false` 필수 (봇 코멘트가 원본 run 취소 방지)

### sdd-sync.yml — 머지 후 정리

```
PR 머지 → 태스크 current/ → done/ 이동
        → 로컬/원격 브랜치 삭제
        → 워크트리 정리
        → 자동 커밋 + push
```

### 핑퐁 자동화

```
PR push
  ├─ Claude 리뷰
  └─ CodeRabbit 리뷰
        ↓ changes_requested
Claude 자동 수정 → push
        ↓ push 트리거
Claude + CodeRabbit 재리뷰
        ↓ 이슈 남으면
Claude 재수정 → push → 재리뷰 (반복)
        ↓ approved
사람이 머지
```

---

## 운영 명령어

| 주체 | 명령어 | 언제 | 동작 |
|------|--------|------|------|
| 사람 | `/sdd-run SP-NNN` | 태스크 시작 | 워크트리 → 구현 → PR |
| 사람 | `@claude [요청]` | PR에서 수동 요청 | Claude가 요청 대응 |
| 사람 | `/sdd-sync` | 비상용 수동 | 머지 태스크 정리 |
| 자동 | `claude-review.yml` | PR 생성/push | 병렬 리뷰 |
| 자동 | `sdd-review.yml` | 리뷰 코멘트 | 자동 수정 |
| 자동 | `sdd-sync.yml` | PR 머지 | 태스크 정리 |
| 자동 | CodeRabbit | PR 생성/push | 병렬 리뷰 |

---

## 태스크 관리

### 원칙

- **태스크 파일은 착수 직전에 생성** — 미리 만들면 코드 변경으로 낡음
- **backlog 한 줄이 SSOT** — 태스크 파일은 실행 계약서
- **current/는 8개 이하** — 대형 피처는 backlog에만 기록
- **진행 이력 있는 태스크는 유지** — 워크트리/설계 진행된 것은 삭제 안 함

### 좋은 Task vs 나쁜 Task

```markdown
# 나쁜 Task — 테스트 없음, 완료 기준 모호
## 무엇을
렌더링 품질 개선
## 완료 기준
- [ ] 품질이 좋아짐
```

```markdown
# 좋은 Task — 실패 테스트가 곧 스펙
## 무엇을
Post Type 렌더링에서 긴 텍스트(60자+) 잘림 방지

## 왜
현재 고정 폰트 48px → 3줄 넘으면 영역 밖으로 벗어남

## 실패 테스트 (TDD)
# backend/tests/test_rendering_font.py
def test_long_text_font_shrink():
    result = calculate_optimal_font_size("가" * 65)
    assert result <= 32

def test_short_text_font_default():
    result = calculate_optimal_font_size("가" * 15)
    assert result >= 48

def test_medium_text_font_interpolation():
    result = calculate_optimal_font_size("가" * 40)
    assert 32 <= result <= 48

## 완료 기준 (DoD)
- [ ] 위 3개 테스트 GREEN
- [ ] 기존 테스트 regression 없음

## 제약
- services/rendering.py만 수정
```

**핵심**: 실패 테스트가 스펙이고, GREEN이 완료. AI의 자기 판단이 아닌 **객관적 검증**.

---

## 품질 게이트 (Stop Hook)

### 5단계 파이프라인

```
Step 1. Lint     → ruff (Python) + prettier (TypeScript)
Step 2. pytest   → Backend 단위 테스트
Step 3. vitest   → Frontend 단위 테스트
Step 4. VRT      → Visual Regression Test
Step 5. E2E      → Playwright (서버 실행 중일 때만)
```

### Self-Heal

```
실패 → exit 2 → Claude에게 에러 전달 → 수정 시도
→ 재검증 → 실패 시 재시도 (최대 3회)
→ 3회 초과 → 종료 + 실패 보고
```

---

## 브랜치 전략

### 매칭 규칙

```
브랜치에서 SP-NNN을 추출하여 디렉토리 매칭 (fallback: 레거시 파일)
- feat/SP-002-xxx  → SP-002 → .claude/tasks/current/SP-002_*/spec.md
- fallback: .claude/tasks/current/SP-002_*.md (레거시)
- 설계 파일: .claude/tasks/current/SP-002_*/design.md (있으면 함께 로드)
```

지원 접두사: `feat/`, `fix/`, `chore/`, `hotfix/`, `worktree-`

### 커밋 경로 규칙

- **main 직접 허용**: `.claude/`, `CLAUDE.md`, `.github/workflows/`, `docs/`
- **feat/fix 브랜치 + PR 필수**: `backend/`, `frontend/`, `audio/`, 그 외 코드

---

## 용어 사전 (혼용 금지)

| 용어 | 역할 | 위치 |
|------|------|------|
| **Roadmap** | 제품 방향, Phase | `docs/01_product/ROADMAP.md` |
| **Backlog** | 태스크 큐 (우선순위) | `.claude/tasks/backlog.md` |
| **Task** | 실행 계약서 (착수 직전 생성) | `.claude/tasks/current/SP-NNN_*/spec.md` |
| **Done** | 완료 이력 | `.claude/tasks/done/SP-NNN_*/` |

---

## PR 코멘트 대응 원칙

맹목 수용이 아닌 **시니어 엔지니어 판단**:
- **버그 지적** → 즉시 수정
- **설계 개선 제안** → CLAUDE.md 대조 후 판단
- **스타일/Nit** → 합리적이면 수정, 아니면 스킵

---

## TDD 실전 가이드

### Red-Green-Refactor 사이클

```
[사람] RED: 실패 테스트 작성 → pytest 실행 → FAIL 확인 → main 커밋
  ↓
[AI]   GREEN: 테스트를 통과하는 최소 코드 작성
  ↓
[AI]   REFACTOR: 테스트 GREEN 유지하면서 코드 정리
```

### 사람이 쓰는 테스트 원칙

- **한 번에 하나씩**: 테스트 1개 → 구현 → 다음 테스트
- **단일 assertion**: 하나의 테스트가 하나의 동작만 검증
- **의도를 테스트**: 구현 방법이 아닌 기대 동작을 검증
- **경계값 포함**: 정상, 엣지, 에러 케이스 모두

### AI에게 주의할 점 (외부 연구 기반)

| 연구 | 발견 | 대응 |
|------|------|------|
| TDAD (arXiv 2603.17973) | TDD 지시만으로는 regression 9.94% 증가 — "어떻게 TDD할지"보다 "어떤 테스트를 확인할지"가 중요 | 태스크에 **영향 받는 기존 테스트 목록** 명시 |
| Simon Willison | AI는 테스트 없이 불필요한 코드 작성 위험. 테스트가 있으면 필요한 코드만 작성 | 실패 테스트 선작성 필수 |
| alexop.dev | 하나의 컨텍스트에서 테스트+구현 동시하면 TDD가 깨짐 — 테스트 작성자 지식이 구현에 오염 | 사람이 테스트, AI가 구현 — 역할 분리 |

---

## 교훈 (Lessons Learned)

| 변경 | 생긴 구멍 | 교훈 |
|------|----------|------|
| worktree 도입 | 의존성 없어서 테스트 불가 | 새 실행 환경 도입 시 테스트 경로 검증 |
| SP-NNN 도입 | sdd-sync 매칭 불일치 | 네이밍 변경 시 스크립트 전체 업데이트 |
| Next.js rewrite 프록시 | SSE 30초 timeout → critic 100% 실패 | 인프라 변경 시 SSE/long-poll 검증 필수 |
| sdd-review 모든 코멘트 반응 | 봇 핑퐁 + timeout 폭발 | `@claude` 멘션 또는 특정 봇만 반응 |
| cancel-in-progress: true | 봇 코멘트가 원본 run 취소 | `false`로 설정, 봇은 if에서 skip |
| 태스크 15개 미리 생성 | 관리 부채, 뭐가 진행 중인지 혼란 | 착수 직전 생성, current/ 8개 이하 |
| sdd-sync `fix/` 브랜치 | sed가 feat/만 처리 → 크래시 | 모든 접두사 패턴 + grep 방어 |
| 회고 교훈 memory에만 기록 | 같은 실수 반복 | Hook/CLAUDE.md에 하드코딩 |
