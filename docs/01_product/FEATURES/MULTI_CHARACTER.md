# Multi-Character 지원

> 상태: 미착수 (DB 스키마 완료, UI 대기)

## 배경

현재 씬당 캐릭터 1명만 지정 가능. 대화 장면, 그룹 씬 등 다중 캐릭터가 필요한 콘텐츠 제작 불가.

## 목표

- 씬당 A, B, C... 다중 캐릭터 배치 지원
- 캐릭터별 독립적 포즈/표정/의상 지정
- 프롬프트 엔진에서 다중 캐릭터 태그 합성

## 현재 상태

- DB: `scene_character_actions` 연관 테이블 이미 존재 (V3 아키텍처)
- Backend: CharacterAction 모델 정의 완료
- Frontend: UI 미구현

## 범위

| 항목 | 설명 |
|------|------|
| Scene Character Selector | 씬별 캐릭터 복수 선택 UI |
| Character Position | 캐릭터 배치 순서 (좌/우/중앙) |
| Per-Character Tags | 캐릭터별 독립 포즈/표정 태그 |
| Prompt Composition | 12-Layer Builder 다중 캐릭터 합성 |

## 수락 기준

| # | 기준 |
|---|------|
| 1 | 씬당 2명 이상 캐릭터 지정 가능 |
| 2 | 캐릭터별 독립적 포즈/표정 설정 |
| 3 | 생성된 이미지에 다중 캐릭터 반영 |
| 4 | 기존 단일 캐릭터 워크플로우 영향 없음 |
