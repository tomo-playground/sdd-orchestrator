---
id: SP-040
priority: P1
scope: infra
branch: feat/SP-040-ai-session-guardrails
created: 2026-03-21
status: pending
depends_on: SP-039
label: enhancement
assignee: stopper2008
---

## 무엇을
AI 세션 간 충돌 방지 체계 구축 — Invariants + ADR + CodeRabbit 충돌 검증

## 왜
- SP-039 근본 원인: 서로 다른 Claude 세션이 만든 코드가 충돌 (404 재생성 vs 삭제)
- 업계 데이터: AI는 사람보다 1.7배 더 많은 버그 생성, 특히 로직/제어 흐름 오류 75% 더 많음
- CLAUDE.md에 원칙은 있지만, 구체적 금지 행동(Invariant)이 없어 AI가 "합리적 이유"로 위반
- 결정의 이유(ADR)가 없어 다른 세션의 AI가 의도를 모른 채 반대 로직을 추가

## 구현 범위

### 1. CLAUDE.md Invariants 섹션 추가
- "절대 위반 금지" 규칙을 구체적 행동 + 이유로 명시
- 현행 "원칙"과 구분: Invariant = 예외 없는 금지 규칙

포함할 Invariants:
```
- 404 응답 시 자동 재생성 금지 (삭제된 엔티티 복원 금지)
- autoSave는 UPDATE만 수행, CREATE 금지
- soft delete된 엔티티에 대한 PUT/PATCH 시도 시 스토어 정리
- config.py 상수를 문자열 리터럴로 하드코딩 금지
```

### 2. ADR (Architecture Decision Records) 도입
- 위치: `.claude/adr/`
- 형식: `ADR-NNN-제목.md` (Status, Context, Decision, Consequences)
- 기존 주요 결정 3~5개를 소급 기록
  - ADR-001: persistStoryboard 404 처리 (Superseded)
  - ADR-002: Draft 선생성 패턴
  - ADR-003: autoSave debounce 설계

### 3. CodeRabbit 충돌 검증 규칙
- `.coderabbit.yaml` path_instructions 추가
- `storyboardActions.ts`: delete/persist/autoSave 3자 상호작용 검증 명시
- 404 처리 변경 시 삭제 시나리오 충돌 확인

### 4. SDD 태스크 템플릿에 "영향 분석" 항목 추가
- 태스크 파일에 `## 영향 분석` 섹션 추가 (선택)
- "이 변경이 영향을 줄 수 있는 기존 로직" 목록
- Claude가 구현 전 관련 코드를 먼저 읽도록 유도

## 완료 기준 (DoD)
- [ ] CLAUDE.md에 Invariants 섹션 추가 (4개 이상)
- [ ] `.claude/adr/` 디렉토리 + 소급 ADR 3개 작성
- [ ] `.coderabbit.yaml`에 storyboardActions 충돌 검증 규칙 추가
- [ ] `.claude/tasks/_template.md`에 "영향 분석" 섹션 추가
- [ ] 기존 CLAUDE.md 원칙과 중복 없이 보완 관계

## 제약
- CLAUDE.md 800줄 한도 준수 — Invariants는 간결하게, 상세 이유는 ADR에 위임
- ADR은 코드 파생 문서가 아닌 의사결정 문서 → main 직접 커밋 허용
- 건드리면 안 되는 것: 기존 CLAUDE.md 규칙 (추가만, 수정/삭제 안 함)

## 힌트
- 참고: https://github.com/anthropics/claude-code/issues/13853 (ADR feature request)
- 참고: https://stackoverflow.blog/2026/01/28/are-bugs-and-incidents-inevitable-with-ai-coding-agents/
- ADR 포맷: https://adr.github.io/
- 기존 결정 추적: `git log --oneline --grep="fix:" | head -20`
