# Phase 17: Service/Admin 분리 — Archive

**완료일**: 02-28
**목표**: 유저(콘텐츠 생산)와 백오피스 관리자(시스템 세팅)의 API/UI를 분리하여 역할별 최적화된 경험 제공.
**명세**: [SERVICE_ADMIN_SEPARATION.md](../../01_product/FEATURES/SERVICE_ADMIN_SEPARATION.md)

---

## Phase 17-0: API 정리 (선행, 완료 02-25)

| # | 항목 | 상태 |
|---|------|------|
| 1 | `keywords.py` 라우터 삭제 (Frontend 미사용, tags.py와 중복) | ✅ (02-25) |
| 2 | `avatar.py` 라우터 삭제 (Frontend 미사용) | ✅ (02-25) |
| 3 | `analytics.py` → `settings.py` 통합 (2개 EP, 동일 관심사) | ✅ (02-25) |
| 4 | `cleanup.py` → `admin.py` 통합 (3개 EP, 동일 관심사) | ✅ (02-25) |
| 5 | `sd.py` → `sd_models.py` 통합 (SD 인프라 단일화) | ✅ (02-25) |
| 6 | One-time 마이그레이션 EP 삭제 3건 (migrate-tag-rules, migrate-patterns) | ✅ (02-25) |
| 7 | Frontend 미사용 prompt EP 삭제 2건 (rewrite, check-conflicts) | ✅ (02-25) |

**결과**: 34개 → 29개 라우터

## Phase 17-0.5: 캐릭터 프리뷰 품질 개선 (완료 02-25)

| # | 항목 | 상태 |
|---|------|------|
| 1 | ControlNet Pose 적용 (standing 기본) — multiple_views 방지 | ✅ (02-25) |
| 2 | 다중 후보 생성 (3장) + 선택 UI | ✅ (02-25) |
| 3 | 네거티브 프롬프트 강화 (배경/멀티뷰/캐릭터시트 가중치 억제) | ✅ (02-25) |
| 4 | Style LoRA 레퍼런스 스케일링 (REFERENCE_STYLE_LORA_SCALE=0.3) | ✅ (02-25) |
| 5 | ControlNet control_mode 설정화 (SD_REFERENCE_CONTROLNET_MODE) | ✅ (02-25) |

## Phase 17-1: Backend 논리적 분리 (완료 02-28)

| # | 항목 | 상태 |
|---|------|------|
| 1 | Service 라우터 `/api/v1/` prefix 그룹핑 (12개 라우터) | ✅ (02-28) |
| 2 | Admin 라우터 `/api/admin/` prefix 그룹핑 (17개 라우터) | ✅ (02-28) |
| 3 | 분할 대상 라우터 10개 엔드포인트 분리 (GET→Service, CUD→Admin) | ✅ (02-28) |
| 4 | OpenAPI docs 분리 (`/docs` Service, `/admin/docs` Admin) | ✅ (02-28) |
| 5 | Frontend URL 마이그레이션 (~50개 파일, `ADMIN_API_BASE` 전환) | ✅ (02-28) |
| 6 | Backend 테스트 URL prefix 갱신 (65개 테스트 파일) | ✅ (02-28) |

## Phase 17-2: Frontend Route Group 분리 (완료 02-28)

| # | 항목 | 상태 |
|---|------|------|
| 1 | `(service)/` route group — Home, Studio, Storyboards | ✅ (02-28) |
| 2 | `admin/` route group — Characters, Styles, Tags, Lab, System | ✅ (02-28) |
| 3 | Library 페이지 해체 → Admin 하위 재배치 | ✅ (02-28) |
| 4 | Settings 해체 → Admin > System + Service > 유저 설정 | ✅ (02-28) |
| 5 | `/` vs `/admin` 경로 기반 역할 식별 + 네비게이션 분리 | ✅ (02-28) |

## Phase 17-3: 유저 UI 간소화 (완료 02-28)

| # | 항목 | 상태 |
|---|------|------|
| 1 | Edit Tab: Advanced 토글로 관리자 기능 격리 (ControlNet, IP-Adapter, Prompt 편집) | ✅ (02-28) |
| 2 | Publish Tab: Quick Render (기본값 렌더) 추가 | ✅ (02-28) |
| 3 | 전문 용어 Tooltip 시스템 추가 (10개 용어) | ✅ (02-28) |

---

**총 18항목 완료** (17-0: 7 + 17-0.5: 5 + 17-1: 6 + 17-2: 5 + 17-3: 3 = 26항목, 단 현재 상태 섹션에서는 17-0~17-3 18건으로 카운트)
