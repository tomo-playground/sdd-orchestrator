---
id: SP-061
priority: P1
scope: backend
branch: feat/SP-061-review-dialogue-quality
created: 2026-03-23
status: done
depends_on:
label: feat
---

## 무엇을 (What)
Review 노드에 대사 품질 코드 레벨(L2) 검증을 추가하여, Gemini aggregate 점수에 의존하지 않고 즉시 판정 가능한 대사 품질 이슈를 잡는다.

## 왜 (Why)
현재 대사 품질 검증은 Review Unified의 Narrative 8차원 aggregate 점수(L3)에만 의존한다. 개별 씬의 감정 중복, Speaker 교번 단절, 클리셰 등은 전체 점수에 묻혀 통과된다. storyboard 1175에서 씬4~5 감정 중복, 씬11 클리셰("심쿵이야"), 씬3~5~7 A 연속 독백이 모두 통과한 사례가 있다.

## 완료 기준 (DoD)

### Layer A: 구조 검증 (순수 함수, Gemini 호출 없음)

- [x] **A-1 감정 중복 연속 (Finalize 배치)**: Finalize 노드에서 동일 speaker의 연속 2씬 이상에서 context_tags.emotion이 동일하면 WARNING 로그, 3씬 이상이면 ERROR 로그를 출력한다 (Review 시점에는 context_tags 미존재이므로 Cinematographer 이후인 Finalize에서 실행)
- [x] **A-2 Speaker 교번 단절**: dialogue 구조에서 동일 speaker가 3씬 이상 연속이면 WARNING을 추가한다 (monologue/narrated_dialogue 구조는 제외)
- [x] **A-3 인접 씬 스크립트 유사도**: 인접 2씬의 script 토큰 Jaccard 유사도가 0.7 이상이면 WARNING을 추가한다

### Layer B: 패턴 검증 (정규식/키워드)

- [x] **B-1 클리셰 감지**: config.py에 `DIALOGUE_CLICHE_PATTERNS` 리스트를 정의하고, 씬 script에 2개 이상 매칭되면 WARNING을 추가한다
- [x] **B-2 문체 일관성**: dialogue 구조에서 동일 speaker의 씬들이 반말/존댓말을 혼용(각 3씬 이상)하면 WARNING을 추가한다

### 통합

- [x] `_review_validators.py`의 기존 `validate_scenes()` 플로우에 Layer A+B 검증을 추가한다 (별도 함수 `validate_dialogue_quality()` 추출)
- [x] 검증 결과가 `ReviewResult.warnings/errors`에 포함되어 Revise 노드의 `revision_feedback`에 자동 전달된다
- [x] 기존 테스트 regression 없음
- [x] 린트 통과

## 영향 분석
- 관련 파일: `backend/services/agent/nodes/_review_validators.py`, `backend/services/agent/nodes/review.py`, `backend/config.py`
- 상호작용: Revise 노드가 review_result.errors/warnings를 읽어 피드백 구성 — 추가된 warnings도 자동으로 포함됨
- Gemini 호출 없음 — 비용 증가 없음, 실행 시간 무시 가능

## 제약
- 변경 파일 5개 이하
- Layer C (Gemini per-scene 평가)는 SP-064에서 별도 처리
- emotion 허용값 검증은 SP-062 scope

## 힌트
- `_validate_single_scene()`은 씬 단독 검증, 새 함수는 **씬 간 관계** 검증
- 한국어 반말 지표: 어절 끝 {"야","어","지","네","게","냐","을게"}
- 한국어 존댓말 지표: 어절 끝 {"요","세요","ㅂ니다","ㅂ니까"}
- storyboard 1175를 테스트 fixture로 활용 가능
