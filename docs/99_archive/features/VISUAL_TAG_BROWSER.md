# Phase 15-B: Visual Tag Browser

> 텍스트 전용 태그에 예시 이미지를 추가하여 선택 정확도 향상

## Status: Completed (02-24)

## 목표
- 태그 선택 시 예시 이미지 표시로 **직관적 탐색** 지원
- 이미지 로딩 실패 시 텍스트 fallback (무장애 경험)
- 카테고리별 시각적 태그 탐색 가능

## 이미지 소스 전략
| 우선순위 | 소스 | 조건 |
|----------|------|------|
| 1 | Danbooru Posts API | `rating:g + score:>10` 필터, preview_file_url |
| 2 | 수동 Override | Admin이 직접 업로드한 이미지 |

## 대상 태그 그룹 (6그룹, ~340태그)
| group_name | 예시 태그 | 예상 수 |
|------------|----------|---------|
| expression | smile, crying, blush | ~40 |
| pose | standing, sitting, lying | ~30 |
| camera | close-up, cowboy_shot, from_above | ~20 |
| clothing | school_uniform, dress, jacket | ~80 |
| hair_color | brown_hair, blonde_hair, blue_hair | ~30 |
| hair_style | twintails, ponytail, bob_cut | ~40 |

## 저장소
- Tag 모델에 `thumbnail_asset_id` FK → `media_assets.id` (ondelete=SET NULL)
- `@property thumbnail_url` — MediaAsset 관계에서 런타임 URL 파생
- Storage key: `tags/{tag_id}/thumbnail/{file_name}.webp`

## UI 위치
- **드롭다운 미니 썸네일**: TagSuggestionDropdown 왼쪽 32px 이미지
- **태그 탐색 패널**: Lab 탭 (`/lab?tab=tag-browser`)
  - 좌측: 그룹 사이드바 (6개 그룹)
  - 우측: 태그 카드 그리드 (128x128 썸네일 + 태그명 + wd14_count)

## Sub-tasks (B-1 → B-3)
| # | 항목 | 범위 |
|---|------|------|
| B-1 | Image Provider + DB 스키마 + Danbooru 수집 | Backend 인프라 |
| B-2 | 드롭다운 미니 썸네일 | Frontend 8곳 적용 |
| B-3 | 태그 탐색 패널 — Lab 탭 | 카테고리 그리드 + 독립 패널 통합 |

## 수락 기준
1. `POST /admin/tag-thumbnails/generate` 로 배치 수집 가능
2. TagSuggestionDropdown에 32px 미니 썸네일 표시
3. Lab 탭에서 그룹별 태그 그리드 탐색 가능
4. 이미지 없는 태그는 텍스트/컬러블록 fallback
5. Backend 단위 테스트 + Frontend 컴포넌트 테스트 통과
