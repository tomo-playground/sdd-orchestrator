# Character Management Page

> 상태: 설계 완료 / 구현 미착수

## 배경

현재 캐릭터 관리가 Home 페이지(/) 중간에 `CharactersSection`으로 끼워져 있고, 편집은 대형 모달(`CharacterEditModal`, 564줄)로 처리. 캐릭터 10개 이상 시 Home 페이지 스크롤이 길어지며, 모달 내부 세로 스크롤도 작업 공간을 제약.

## 목표

- 캐릭터 전용 독립 페이지(`/characters`)로 분리하여 전용 진입점 확보
- 모달 기반 편집 → 페이지 기반 편집으로 전환 (넓은 작업 공간, URL 북마크)
- Home 페이지 경량화 (최근 캐릭터 3개 미리보기만 유지)

## 선행 조건

- Backend `services/characters/` 패키지 분리 (내부 리팩토링, API 인터페이스 변경 없음)
- 현재 캐릭터 API가 안정된 상태에서 프론트엔드 착수

## 범위

| 항목 | 설명 |
|------|------|
| 네비게이션 변경 | Home → **Characters** → Lab → Manage (4탭) |
| 목록 페이지 (`/characters`) | 3열 카드 그리드 + 검색/필터 + 빈 상태 |
| 상세/편집 페이지 (`/characters/[id]`) | 좌측 사이드패널(프리뷰+액션) + 우측 편집 섹션 |
| 신규 생성 (`/characters/new`) | 빈 폼 편집 페이지, 저장 후 상세 페이지로 리다이렉트 |
| Home 축소 | `CharactersSection` → 최근 3개 미니카드 + "View All" 링크 |
| 모달 정리 | `CharacterEditModal` → 섹션 추출 후 경량 버전 유지 (Quick Edit 용) |

## CHARACTER_BUILDER.md와의 관계

- `/characters/new` = 현재 수동 입력 방식의 페이지 버전
- `CHARACTER_BUILDER` 위저드 = 향후 `/characters/new`에 추가되는 대안 생성 경로
- 이 기능이 CHARACTER_BUILDER의 선행 조건 (페이지가 있어야 위저드를 내장 가능)

## 수락 기준

| # | 기준 |
|---|------|
| 1 | `/characters` 접근 시 전체 캐릭터 카드 표시, 새로고침 복구 |
| 2 | `/characters/[id]` 접근 시 모든 편집 섹션 렌더링 |
| 3 | Save 후 데이터 영속, 편집 중 이탈 시 경고 표시 |
| 4 | Home 페이지에서 최근 3개 미니카드 + "View All" 링크 동작 |
| 5 | 기존 CharacterSelector, CharacterPicker 등 참조 컴포넌트 정상 동작 |
| 6 | 반응형 레이아웃 (Desktop 3열 / Tablet 2열 / Mobile 1열) |

## 설계 문서

- 와이어프레임: `docs/02_design/wireframes/CHARACTER_PAGE_WIREFRAME.md`
