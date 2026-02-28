# Phase 15: Prompt Input UX 고도화 — Archive

**완료일**: 02-24
**목표**: 19개 프롬프트 입력 포인트에 "미리보기 → 확인 → 실행" 원칙 적용. TagAutocomplete 품질 개선 및 확산, 태그 검증 시스템 확산.
**명세**: [PROMPT_INPUT_UX.md](../../01_product/FEATURES/PROMPT_INPUT_UX.md)

---

## Phase A-0: 조합 프롬프트 미리보기 (완료 02-23)

| # | 항목 | 상태 |
|---|------|------|
| 1 | `/compose` API 확장 — 레이어별 분해 정보(`layers`) 응답 필드 추가 | ✅ (02-23) |
| 2 | `ComposedPromptPreview.tsx` — 12-Layer 분해 + 조합 결과 + 네거티브 표시 | ✅ (02-23) |
| 3 | 장면 묘사 → 이미지 프롬프트 변환 diff UI (승인 전 미적용) | ✅ (02-23) |
| 4 | 편집 지시문 Before/After diff UI (승인 전 미적용) | ✅ (02-23) |

## Phase A-1: TagAutocomplete 품질 개선 (완료 02-24)

| # | 항목 | 상태 |
|---|------|------|
| 1 | API 디바운스 300ms 적용 | ✅ (02-24) |
| 2 | 한글(유니코드) 입력 지원 | ✅ (02-24) |
| 3 | 인기도(`wd14_count`) 드롭다운 표시 | ✅ (02-24) |
| 4 | 태그 선택 후 `, ` 자동 삽입 | ✅ (02-24) |
| 5 | 폐기 태그 `deprecated_reason` + 대체 태그 표시 | ✅ (02-24) |
| 6 | Frontend-Backend 검증 스키마 동기화 (`validate-tags` 응답 통일) | ✅ (02-24) |

## Phase A-2: TagAutocomplete 확산 (완료 02-24)

| # | 항목 | 상태 |
|---|------|------|
| 1 | Tier 1 — NegativePrompt, CharacterActions, ClothingModal, PromptsStep Base/Negative (5곳) | ✅ (02-24) |
| 2 | Tier 2 — PromptsStep Ref Base/Negative, StyleProfileEditor Positive/Negative (4곳) | ✅ (02-24) |

## Phase A-3: 태그 검증 확산 (완료 02-24)

| # | 항목 | 상태 |
|---|------|------|
| 1 | 캐릭터 Base/Negative, Reference Base/Negative 검증 적용 | ✅ (02-24) |
| 2 | StyleProfile Positive/Negative 검증 적용 | ✅ (02-24) |
| 3 | Scene Negative, ClothingModal 검증 적용 | ✅ (02-24) |

## Phase B: Visual Tag Browser (완료 02-24)

| # | 항목 | 상태 |
|---|------|------|
| 1 | Image Provider + DB 스키마 + Danbooru 수집 (Backend 인프라) | ✅ (02-24) |
| 2 | 드롭다운 미니 썸네일 (8곳 적용) | ✅ (02-24) |
| 3 | 태그 탐색 패널 — Lab 탭 (카테고리 그리드 + 독립 패널 통합) | ✅ (02-24) |

---

**총 18항목 완료** (A-0: 4 + A-1: 6 + A-2: 2 + A-3: 3 + B: 3)
