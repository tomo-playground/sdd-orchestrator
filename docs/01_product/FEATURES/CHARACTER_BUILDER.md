# Character Builder UI

> 상태: 미착수

## 배경

현재 캐릭터 생성은 Manage 페이지에서 필드를 수동 입력. 조합형 빌더로 직관적 캐릭터 구성을 지원.

## 목표

- Gender + Appearance + LoRA를 단계별로 조합하여 캐릭터 생성
- 실시간 프리뷰로 조합 결과 확인
- 기존 수동 입력 방식과 병행

## 범위

| 항목 | 설명 |
|------|------|
| Step-by-Step Wizard | Gender → Hair/Eye → Body → LoRA 단계별 선택 |
| Live Preview | 선택 변경 시 실시간 프리뷰 이미지 생성 |
| LoRA Suggestion | 선택한 특성에 맞는 LoRA 자동 추천 |
| Save & Apply | 완성된 캐릭터를 DB에 저장 |

## 수락 기준

| # | 기준 |
|---|------|
| 1 | 단계별 조합으로 캐릭터 생성 가능 |
| 2 | 프리뷰 이미지가 선택 사항 반영 |
| 3 | 기존 수동 생성 방식에 영향 없음 |
