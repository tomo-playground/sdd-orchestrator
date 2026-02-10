# 이미지 생성 Progress (SSE)

> 상태: 미착수 | 출처: 7-1 #4 (Tier 1)

## 배경

렌더링 SSE 진행률은 완료(7-1 #19: `/video/progress/{task_id}`). 그러나 이미지 생성(SD WebUI)은 진행률 없이 블로킹 대기 상태. 다수 씬 생성 시 사용자가 진행 상황을 알 수 없음.

## 목표

- SD WebUI `/sdapi/v1/progress` API 폴링 → SSE 스트리밍
- 생성 중 실시간 % 표시
- (옵셔널) 중간 프리뷰 이미지 전송

## 범위

| 항목 | 설명 |
|------|------|
| Backend SSE 엔드포인트 | `GET /scene/generate-progress/{task_id}` |
| SD WebUI Progress 폴링 | `/sdapi/v1/progress` 주기적 호출 (1-2초) |
| Frontend Progress UI | 생성 중 % 바 + 예상 시간 |
| 프리뷰 이미지 (옵셔널) | SD WebUI `current_image` 필드 활용 |
| Batch 생성 연동 | `generate-batch` 시 씬별 개별 progress |

## 선행 조건

- 렌더링 SSE 인프라 완료 (7-1 #19 완료)
- SD WebUI progress API 접근 가능

## 수락 기준

| # | 기준 |
|---|------|
| 1 | 이미지 생성 중 실시간 % 표시 |
| 2 | 생성 완료 시 즉시 이미지 표시 |
| 3 | 네트워크 끊김 시 자동 재연결 |
| 4 | 기존 동기 생성 API 호환성 유지 |

## 참고

- 렌더링 SSE 구현: `backend/routers/video_routes.py` (`/video/progress/`)
- SD WebUI Progress API: `http://localhost:7860/sdapi/v1/progress`
