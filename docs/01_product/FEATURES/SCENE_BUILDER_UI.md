# Scene Builder UI

> 상태: 미착수 (DB 스키마 완료, UI 대기)

## 배경

현재 장면 컨텍스트(배경, 시간, 날씨)는 Gemini가 자동 생성. 사용자가 직접 세밀하게 제어할 수 없음.

## 목표

- 장면별 배경/시간/날씨 컨텍스트 태그를 사용자가 직접 선택
- DB의 `scene_tags` 테이블 활용
- Gemini 자동 생성과 수동 설정의 하이브리드 운영

## 현재 상태

- DB: `scene_tags` 연관 테이블 존재
- Backend: SceneTag 모델, context_tags 필드 정의 완료
- Frontend: UI 미구현

## 범위

| 항목 | 설명 |
|------|------|
| Environment Picker | 실내/실외, 구체적 장소 선택 |
| Time/Weather | 시간대, 날씨 컨텍스트 태그 |
| Manual Override | Gemini 자동 태그 위에 수동 덮어쓰기 |
| Tag Autocomplete 연동 | 기존 6-3.12 Tag Autocomplete 재사용 |

## 수락 기준

| # | 기준 |
|---|------|
| 1 | 장면별 배경/시간/날씨 태그 수동 선택 가능 |
| 2 | Gemini 자동 생성 태그와 공존 (수동 우선) |
| 3 | 선택된 태그가 프롬프트에 정확히 반영 |
