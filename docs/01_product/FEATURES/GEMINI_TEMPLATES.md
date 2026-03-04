# Structure별 전용 Gemini 템플릿

> 상태: **대체 완료** (Phase 13-C, 2026-02-20) | 출처: 7-1 #7 (Tier 1)
>
> Phase 13-C에서 Structure별 전용 파일 대신 기존 템플릿 내 Structure별 가이드 통합 방식으로 해결.
> `writer_planning.j2`, `concept_architect.j2`, `scriptwriter.j2` 등에 Structure별 조건부 렌더링 적용.

## 배경

현재 모든 Structure(Monologue, Dialogue, Narrated Dialogue, Confession, Lesson 등)가 동일한 Gemini 템플릿(`create_storyboard.j2`)을 사용. Structure별 고유한 연출 패턴(독백 vs 대화 vs 교훈)을 반영하지 못해 품질 편차 발생.

## 목표

- Structure별 전용 Jinja2 템플릿 5종 제작
- 각 Structure의 특성에 맞는 씬 구성 가이드 제공
- Gemini가 Structure에 맞는 장면 전환/감정 표현/카메라 앵글을 자연스럽게 생성

## 범위

| 항목 | 설명 |
|------|------|
| Monologue 템플릿 | 1인 독백 중심, 감정 흐름 강조 |
| Dialogue 템플릿 | 2인 대화, 화자 전환 + 리액션 샷 |
| Narrated Dialogue 템플릿 | 나레이터 + 2인 대화, 시점 전환 |
| Confession 템플릿 | 고백/회상, 클로즈업 + 플래시백 |
| Lesson 템플릿 | 교훈/정보 전달, 시각적 예시 삽입 |

## 선행 조건

- Prompt Engine 완료 (6-2.5 완료)
- 기존 `create_storyboard.j2` 분석 완료

## 수락 기준

| # | 기준 |
|---|------|
| 1 | 5종 전용 J2 템플릿 파일 각각 존재 |
| 2 | 각 템플릿 10건 생성 시 WD14 Match Rate 80%+ |
| 3 | 기존 단일 템플릿 대비 품질 편차 감소 확인 |
| 4 | `services/presets.py`에서 Structure → 템플릿 자동 매핑 |

## 참고

- 기존 템플릿: `backend/templates/create_storyboard.j2`
- 프리셋 정의: `backend/services/presets.py`
