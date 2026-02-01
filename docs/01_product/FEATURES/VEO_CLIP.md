# VEO Clip (Video Generation)

> 상태: 미착수

## 배경

현재 정지 이미지 + Ken Burns 효과로 영상을 구성. AI Video Generation을 통합하면 더 역동적인 씬 제작 가능.

## 목표

- Google VEO 또는 유사 Video Generation API 통합
- 씬 단위 비디오 클립 생성 옵션 제공
- 기존 이미지 기반 워크플로우와 병행

## 범위

| 항목 | 설명 |
|------|------|
| API 연동 | VEO API 호출 파이프라인 |
| Scene Option | 씬별 이미지/비디오 선택 토글 |
| Render Pipeline | 비디오 클립을 FFmpeg 파이프라인에 통합 |
| Fallback | 생성 실패 시 기존 이미지 + Ken Burns로 대체 |

## 수락 기준

| # | 기준 |
|---|------|
| 1 | 씬 단위로 비디오 클립 생성 가능 |
| 2 | 기존 이미지 기반 워크플로우에 영향 없음 |
| 3 | 렌더링 파이프라인에서 비디오 클립 정상 합성 |
