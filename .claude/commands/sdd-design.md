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

질문 대상:
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

### Phase 5: 설계 파일 생성 + 리뷰 요청

1. `.claude/tasks/current/SP-NNN_*/design.md` 파일에 설계 내용 작성 (spec.md와 동일 디렉토리)
2. 태스크 파일(spec.md)의 `## 상세 설계 (How)` 섹션에 `> [design.md](./design.md) 참조` 링크 추가
3. `status: pending` → `status: design` 변경
4. 사용자에게 설계 요약 테이블 + 승인 명령어 안내:

```
설계 작성 완료. 리뷰해 주세요.

[설계 요약 테이블]

승인: /sdd-design SP-NNN approved
수정 요청: /sdd-design SP-NNN reject [사유]
```

---

## Phase 6-A: 승인 처리

> `SP-NNN approved`가 전달된 경우 실행

1. 태스크 파일 로드 → `status: design` 확인 (아니면 에러)
2. `status: design` → `status: approved` + `approved_at: YYYY-MM-DD` 기록
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
