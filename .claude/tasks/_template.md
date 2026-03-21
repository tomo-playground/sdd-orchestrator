---
id: SP-NNN                   # SP-순번 (프로젝트 고유 ID)
priority:                    # P0 / P1 / P2 / P3
scope:                       # backend / frontend / fullstack / infra / docs
branch: feat/SP-NNN-설명     # feat/{id}-{kebab-case 설명}
created:                     # YYYY-MM-DD
status: pending              # pending → running → done / failed
depends_on:                  # 선행 태스크 id (없으면 비움)
label:                       # PR 라벨 (feat / bug / chore)
---

## 무엇을 (What)
[한 줄: 사용자 관점에서 뭐가 바뀌는지]

## 왜 (Why)
[이유/배경 — 이게 없으면 왜 문제인지]

## 완료 기준 (DoD)
> AI가 이 목록으로 실패 테스트를 작성(RED)하고, 구현(GREEN)한다.
> "must"는 필수, "should"는 권장. 모호한 표현 금지.

- [ ] [동사로 시작하는 검증 가능한 기준]
- [ ] [동사로 시작하는 검증 가능한 기준]
- [ ] 기존 테스트 regression 없음
- [ ] 린트 통과

### DoD 작성 가이드
```
--- 좋은 DoD ---
- [ ] POST /api/v1/express에 mood 없이 요청하면 400 반환
- [ ] 30초 이상 영상은 자동으로 잘라서 30초로 제한
- [ ] 삭제된 storyboard에 PUT 요청하면 스토어 전체 리셋

--- 나쁜 DoD ---
- [ ] API가 잘 동작해야 한다        ← 모호함
- [ ] 에러 처리를 개선한다           ← 뭘 어떻게?
- [ ] 사용자 경험이 좋아야 한다      ← 측정 불가
```

## 영향 분석 (선택)
> 이 변경이 영향을 줄 수 있는 기존 로직을 나열한다.
> Claude가 구현 전 관련 코드를 먼저 읽도록 유도하는 목적.

- 관련 함수/파일:
- 상호작용 가능성:
- 관련 Invariant:
- 관련 ADR:

## 제약 (Boundaries)
- 변경 파일 10개 이하 목표
- 건드리면 안 되는 것:
- 의존성 추가 금지:

## 힌트 (선택)
- 관련 파일:
- 참고 문서:
