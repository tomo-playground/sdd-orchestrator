# Shorts Factory - Lean Guide (MVP)

이 문서는 정책 변화에 유연하게 대응하면서 개발 속도를 유지하기 위한 최소한의 가이드입니다.

## 🛡️ 핵심 원칙 (Core Rules)

### 1. `main` 브랜치는 항상 동작해야 한다
*   실험적인 코드나 새로운 기능은 반드시 별도 브랜치(`feature/*`)에서 작업합니다.
*   `main`에 합칠 때는 **"지금 당장 데모가 가능한가?"**를 스스로 체크합니다.

### 2. "작동하는 코드"가 최우선이다
*   완벽한 코드 구조(리팩토링)에 집착하기보다, 의도한 기능이 사용자에게 전달되는 것에 집중합니다.
*   리팩토링은 로드맵의 특정 주기(Phase 1 등)에만 집중해서 수행합니다.

### 3. 문서는 "나침반" 역할만 한다
*   `PRD.md`에는 세부 스펙 대신 **핵심 목표**만 기록합니다.
*   `ROADMAP.md`를 통해 **다음 갈 길**만 명확히 유지합니다.
*   세세한 로직 설명은 문서 대신 **명확한 변수명과 함수명(코드)**으로 대신합니다.

### 4. `API_SPEC.md`는 API 변경 시 즉시 업데이트한다
*   새 엔드포인트 추가, Request/Response 스키마 변경, 엔드포인트 삭제 시 **해당 PR에 포함**합니다.
*   프론트엔드-백엔드 계약이므로, 코드와 문서의 불일치는 버그로 취급합니다.

### 5. `PRD.md`는 마일스톤 단위로 업데이트한다
*   Phase 완료 시 **Definition of Done** 체크리스트를 갱신합니다.
*   프로젝트 범위(Scope) 변경 시 v1.0 Core / v1.x Backlog 섹션을 조정합니다.

### 6. `TROUBLESHOOTING.md`는 이슈 해결 시 업데이트한다
*   문제 해결 후 **QA Validator**가 검증하고 문서에 기록합니다.
*   반복되는 이슈는 즉시 추가하여 같은 문제 재발을 방지합니다.

### 7. `CLAUDE.md`는 경량화 상태를 유지한다
*   **제한**: 50줄 / 2KB 이하 (모든 대화 컨텍스트에 포함되므로)
*   **필수 정보만**: 아키텍처 요약, 문서 참조, 코드 가이드라인, Agents/Commands 테이블
*   **상세 정보는 분리**: 진행 상황 → `ROADMAP.md`, 관리 규칙 → `CONTRIBUTING.md`

---

## 🤖 Agents/Commands 관리

### 구조
```
.claude/
├── agents/      # Sub Agents (판단/분석 담당)
└── commands/    # Commands (원자적 작업)
```

### 레이어 분리
```
Commands (원자적 작업) ← Agents (판단/분석) ← MCP Servers (외부 데이터)
```

### 추가/수정 시 체크리스트
- [ ] Agent/Command 추가 시: `CLAUDE.md` 테이블 업데이트
- [ ] Agent가 Command 활용 시: Agent 파일의 "활용 Commands" 섹션 업데이트
- [ ] MCP 추가 시: `.mcp.json` 및 관련 Agent 파일 업데이트

### 네이밍: `kebab-case.md` (예: `prompt-engineer.md`)

---
**Core Mindset**: "Move Fast, Stay Solid"
