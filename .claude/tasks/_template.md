---
id: SP-NNN                   # SP-순번 (프로젝트 고유 ID)
priority:                    # P0 / P1 / P2 / P3
scope:                       # backend / frontend / fullstack / infra / docs
branch: feat/SP-NNN-설명     # feat/{id}-{kebab-case 설명}
created:                     # YYYY-MM-DD
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

## 상세 설계 (How)
> `/sdd-design SP-NNN`이 자동 작성 → **사람이 승인한 후에만** 구현 착수.
> state.db에서 design → 사람 승인 → approved → /sdd-run 실행. (spec.md에 status 필드 없음)

### 설계 작성 가이드
각 DoD 항목에 대해 아래 6가지를 명시:
1. **구현 방법**: 어떤 파일의 어떤 함수를 어떻게 수정하는지 (1-3줄)
2. **동작 정의**: 사용자 관점에서 before → after 상태 변화
3. **엣지 케이스**: 예외 상황과 처리 방침
4. **영향 범위**: 이 변경이 건드릴 수 있는 다른 기능
5. **테스트 전략**: 어떤 테스트를 먼저 작성할 것인가 (RED 단계 가이드)
6. **Out of Scope**: 이번 항목에서 건드리지 말아야 할 것

**적정 깊이**: 함수의 시그니처(이름, 입력, 출력)와 상호작용(호출 관계)까지만 설계.
내부 구현 로직(if문, 루프 등)은 AI에게 위임.

```
--- 좋은 설계 ---
### DoD-1: 음성 톤 토스트
- 구현: handleEmotionClick에서 이전 값 비교, 변경 시에만 showToast("음성 톤: {label}", "success")
- 동작: 밝게(미선택) 클릭 → 활성화 + 토스트. 밝게(선택됨) 재클릭 → 무시
- 엣지: 캐릭터 미선택 상태에서도 프리셋 저장 허용 (기존 동작 유지)
- 영향: autoSave 트리거 시점 변경 없음, 토스트만 추가
- 테스트: DirectorControlPanel 렌더 → emotion 버튼 클릭 → showToast 호출 검증
- OoS: setGlobalEmotion 내부 로직 변경 금지

--- 나쁜 설계 ---
### DoD-1: 음성 톤 토스트
- showToast 추가                    ← 어디에? 조건은?
- 적절하게 처리                      ← 뭘 어떻게?
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
