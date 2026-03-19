# Scene 단위 자연어 이미지 편집

> 상태: **완료** (Phase 13-B, 2026-02-20) | 선행: 6-4.22 Gemini Image Editing (완료)

## 배경

Character Preview에서는 자연어 이미지 편집이 이미 동작 중 (`edit-preview` API).
Scene 이미지에도 동일 기능을 확장하여 개별 씬 이미지를 자연어로 수정 가능하게 함.

## 목표

- SceneCard에서 개별 씬 이미지를 자연어 명령으로 편집
- 기존 `edit-preview` API 패턴 재사용
- 편집 후 이미지 교체 및 Asset 업데이트

## 범위

| 항목 | 설명 |
|------|------|
| SceneCard Edit Button | 자연어 편집 입력 UI |
| Backend API | Scene 이미지 편집 엔드포인트 (`/scenes/{id}/edit-image`) |
| Asset Update | 편집 결과를 기존 이미지 Asset과 교체 |
| History | 편집 전/후 비교 (선택적) |

## 수락 기준

| # | 기준 |
|---|------|
| 1 | SceneCard에서 자연어 입력으로 이미지 편집 가능 |
| 2 | 편집 결과가 Asset 스토리지에 저장 |
| 3 | 기존 이미지 재생성 워크플로우에 영향 없음 |
