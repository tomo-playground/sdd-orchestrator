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

## 실패 테스트 (TDD)
AI가 구현할 때 이 테스트를 GREEN으로 만드는 것이 목표.
사람이 작성하거나, 테스트 파일 경로 + 케이스를 명시.

```python
# backend/tests/test_SP_NNN.py
def test_핵심_기능():
    """[기대 동작 설명]"""
    result = 대상_함수(입력값)
    assert result == 기대값
```

또는 기존 테스트 파일에 케이스 추가:
- `backend/tests/test_xxx.py::test_케이스명` — [기대 동작]

## 완료 기준 (DoD)
- [ ] 실패 테스트 → GREEN
- [ ] 기존 테스트 regression 없음
- [ ] 린트 통과

## 영향 분석 (선택)
- 이 변경이 영향을 줄 수 있는 기존 로직:
- 관련 Invariant:
- 관련 ADR:

## 제약
- 변경 파일 10개 이하 목표
- 건드리면 안 되는 것:
- 의존성 추가 금지:

## 힌트 (선택)
- 관련 파일:
- 참고:
