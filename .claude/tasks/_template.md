---
id: SP-NNN                   # SP-순번 (프로젝트 고유 ID)
priority:                    # P0 / P1 / P2 / P3
scope:                       # backend / frontend / fullstack / infra / docs
branch: feat/SP-NNN-설명     # feat/{id}-{kebab-case 설명}
created:                     # YYYY-MM-DD
status: pending              # pending → running → done / failed
depends_on:                  # 선행 태스크 id (없으면 비움)
---

## 무엇을
[구현할 기능 한 줄 설명]

## 왜
[이유/배경]

## 완료 기준 (DoD)
- [ ] 핵심 기능 동작
- [ ] 테스트 통과
- [ ] 기존 기능 regression 없음

## 제약
- 변경 파일 10개 이하 목표
- 건드리면 안 되는 것:
- 의존성 추가 금지:

## 힌트 (선택)
- 관련 파일:
- 참고:
