# Cross-Agent Audit Report (2026-02-26)

> **상태: 완료 (P0~P3 106건 수정, 02-26)**
> 7개 에이전트 통합 점검 결과 | 총 123건 (BUG 63, IMPROVEMENT 60)
> PM 보고서: 우선순위별 통합, 영향도/수정 난이도/담당 에이전트 포함

## 요약 대시보드

| 우선순위 | 건수 | 정의 | 목표 Sprint |
|----------|------|------|-------------|
| **P0 (즉시)** | 14건 | 데이터 손실, 크래시, 파이프라인 중단 | Sprint 1 (1주) |
| **P1 (긴급)** | 32건 | 기능 오작동, 세션 누수, 접근성 핵심 | Sprint 2 (2주) |
| **P2 (중요)** | 45건 | 품질 저하, UX 미흡, 보안 강화 | Sprint 3-4 (3~4주) |
| **P3 (백로그)** | 32건 | 최적화, 코드 정리, 장기 개선 | Phase 18+ |

**영향도**: USR=사용자 영향, DAT=데이터 무결성, SEC=보안, PER=성능
**수정 난이도**: S=1~2시간, M=반나절, L=1일+

---

## P0: 즉시 수정 (Sprint 1 / 14건)

### G1. 파이프라인 크래시 방지 (3건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 1 | `cost_usd.toFixed()` null 크래시 | Frontend | USR | S |
| 2 | `TagFilterCache` 클래스 중복 정의 (core.py vs db_cache.py) | Prompt | DAT | S |
| 3 | `_apply_layer_boosts` LoRA 트리거 의도치 않은 가중치 | Prompt | DAT | M |

### G2. xfade 오프셋 계산 오류 (1건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 4 | xfade offset 누적 계산 오류 -- 3개+ 씬 전환 타이밍 틀어짐 | FFmpeg | USR | M |

### G3. response_model 누락 -- API Contract 위반 (3건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 5 | `/storyboards/create` response_model 누락 | Backend | DAT | S |
| 6 | `/scene/validate-and-auto-edit` response_model 누락 | Backend | DAT | S |
| 7 | `/scene/cancel/{task_id}` response_model 누락 | Backend | DAT | S |

### G4. Soft Delete 필터 누락 -- 삭제 데이터 노출 (3건 그룹)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 8 | `prompt_histories` PUT/toggle/apply/score 4개 EP | Backend | DAT | M |
| 9 | Soft Delete 필터 누락 6건 (update_character 등) | DBA | DAT | M |
| 10 | `controlnet.py` Character 쿼리 soft delete 미적용 | Backend | DAT | S |

> G4는 일괄 처리 권장. `deleted_at.is_(None)` 누락 지점 전수 검사.

### G5. DB 인덱스/제약조건 (2건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 11 | `ix_scenes_client_id` partial unique index 미적용 | DBA | DAT | M |
| 12 | FK 컬럼 인덱스 26개 누락 | DBA | PER | L |

### G6. 접근성 법적 요건 (2건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 13 | `label htmlFor` 누락 136/158개 | UI/UX | USR | L |
| 14 | Studio 3컬럼 레이아웃 모바일 미대응 | UI/UX | USR | L |

---

## P1: 긴급 수정 (Sprint 2 / 32건)

### G7. 세션/리소스 누수 (4건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 15 | `get_db()` next() -- 세션 cleanup 미실행 | FFmpeg | DAT | S |
| 16 | `quality.py` SessionLocal 수동 관리 5개 EP | Backend+DBA | DAT | M |
| 17 | `scene.py` edit_scene_image db.close() 후 ORM 참조 | Backend | DAT | S |
| 18 | `_prepare_preset_bgm` 세션 rollback 누락 | FFmpeg | DAT | S |

### G8. 프롬프트/태그 정합성 (6건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 19 | `medium_shot`, `bust_shot` FORBIDDEN인데 CATEGORY_PATTERNS 등록 | Prompt | DAT | S |
| 20 | `POSE_MAPPING` 키 공백 형식 (Danbooru 언더바 불일치) | Prompt | DAT | S |
| 21 | ~~`compose_for_reference` alias 해소 후 필터링 결함~~ (해결 — `_resolve_aliases_positional` 도입) | Prompt | DAT | M |
| 22 | `custom_base_prompt` 태그 `is_permanent` 미설정 | Prompt | DAT | S |
| 23 | `MultiCharacterComposer` TagRuleCache 충돌 검사 누락 | Prompt | DAT | M |
| 24 | 템플릿 "open mouth" 공백 형식 | Prompt | DAT | S |

### G9. Falsy 값 소실 / 타입 불일치 (5건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 25 | `\|\|` 연산자로 falsy 값(0, false) 소실 3건 | Frontend | USR | S |
| 26 | `sceneIds` fallback `\|\|` vs `??` 불일치 | Frontend | USR | S |
| 27 | `description` 필드 타입 불일치 | Frontend | USR | S |
| 28 | `buildScenesPayload` client_id 누락 | Frontend | DAT | S |
| 29 | `scene.py` validate-and-auto-edit dict.get() 타입 불일치 | Backend | DAT | S |

### G10. response_model 누락 -- 나머지 (2건 그룹)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 30 | DELETE 엔드포인트 15개 response_model 누락 | Backend | DAT | M |
| 31 | 기타 엔드포인트 30개+ response_model 누락 | Backend | DAT | L |

### G11. N+1 쿼리 / 성능 (2건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 32 | N+1 쿼리 (admin, voice/music presets, style_profiles 등) | Backend | PER | M |
| 33 | 이미지 이중 로딩 (filters.py) | FFmpeg | PER | S |

### G12. 이미지/렌더링 품질 (3건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 34 | 마지막 씬 불필요한 transition delay | FFmpeg | USR | S |
| 35 | `-s` 플래그 이중 스케일링 화질 열화 | FFmpeg | USR | M |
| 36 | `colorchannelmixer aa=1.6` 알파 클리핑 | FFmpeg | USR | S |

### G13. ARIA / 접근성 (6건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 37 | Popover ARIA 속성 누락 | UI/UX | USR | S |
| 38 | Tooltip 키보드/스크린리더 미지원 | UI/UX | USR | M |
| 39 | CollapsibleSection aria-expanded 없음 | UI/UX | USR | S |
| 40 | AppThreeColumnLayout 우측 패널 반응형 미대응 | UI/UX | USR | M |
| 41 | Studio Sub-Nav 모바일 미대응 | UI/UX | USR | M |
| 42 | clipboard API reject 미처리 3건 | Frontend | USR | S |

### G14. Stale State / 동기화 (4건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 43 | `handleImageUpload` stale scenes 참조 | Frontend | USR | M |
| 44 | `handleGenerateImage` stale scenes 참조 | Frontend | USR | M |
| 45 | `styleProfileActions` version 미전송 (optimistic lock 우회) | Frontend | DAT | S |
| 46 | Storyboard 삭제 기능 부재 | Frontend | USR | M |

---

## P2: 중요 개선 (Sprint 3-4 / 45건)

### G15. 보안 강화 (7건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 47 | S3Storage Path Traversal 검증 부재 | Security | SEC | M |
| 48 | 에러 응답 내부 예외 메시지 노출 | Security | SEC | M |
| 49 | 다수 라우터 `str(exc)` 직접 반환 | Security | SEC | M |
| 50 | CORS `allow_origins=["*"]` + credentials | Security | SEC | S |
| 51 | base64 이미지 크기 미제한 | Security | SEC | S |
| 52 | SSRF (`load_image_bytes` HTTP 요청) | Security | SEC | M |
| 53 | OAuth state CSRF 방어 미흡 | Security | SEC | M |

### G16. DB 정합성 / 스키마 (5건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 54 | `media_assets` CHECK 제약조건 ORM 불일치 | DBA | DAT | S |
| 55 | `ip_adapter_reference` String (Known Issue) | DBA | DAT | L |
| 56 | `storyboard_characters` FK 인덱스 누락 | DBA | PER | S |
| 57 | `list_storyboards` soft-deleted 씬 포함 카운트 | DBA | DAT | S |
| 58 | `default_` prefix (StyleProfile) | DBA | DAT | M |

### G17. 프롬프트 엔진 개선 (6건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 59 | `CATEGORY_PATTERNS` cross-category 중복 | Prompt | DAT | M |
| 60 | `INDOOR_LOCATION_TAGS` "room" 불일치 | Prompt | DAT | S |
| 61 | 레퍼런스 생성 StyleProfile 파라미터 미적용 | Prompt | USR | M |
| 62 | `POSE_MAPPING` 커버리지 부족 (21/40) | Prompt | USR | M |
| 63 | `_apply_clothing_override` 12-Layer 무시 | Prompt | DAT | M |
| 64 | controlnet sampler 하드코딩 | Prompt | DAT | S |

### G18. Backend 코드 품질 (8건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 65 | SQL 와일드카드 이스케이프 미적용 (ilike) | Backend | SEC | S |
| 66 | admin refresh-caches 실패 시 200 반환 | Backend | DAT | S |
| 67 | `datetime.now()` 타임존 미지정 | Backend | DAT | S |
| 68 | 인라인 스키마 정의 → schemas.py 분리 필요 | Backend | DAT | L |
| 69 | settings.py 런타임 모듈 변수 직접 수정 | Backend | DAT | M |
| 70 | scene.py base64 인코딩 5중 반복 | Backend | PER | M |
| 71 | video.py delete_video filename 기반 조회 | Backend | DAT | S |
| 72 | 함수 내부 import 반복 | Backend | PER | M |

### G19. FFmpeg 파이프라인 안정화 (5건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 73 | `_probe_duration` 실패 시 로그 없음 | FFmpeg | DAT | S |
| 74 | 필터체인 문자열 결합 디버깅 어려움 | FFmpeg | PER | M |
| 75 | `anullsrc` 무한 스트림 | FFmpeg | PER | S |
| 76 | `Image.open()` close 미호출 | FFmpeg | PER | S |
| 77 | `compose_post_frame` RGB->PNG 비효율 | FFmpeg | PER | S |

### G20. UI/UX 개선 (10건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 78 | ConfirmDialog `aria-describedby` 누락 | UI/UX | USR | S |
| 79 | CommandPalette combobox 역할 누락 | UI/UX | USR | S |
| 80 | ConnectionGuard 로딩 알림 누락 | UI/UX | USR | S |
| 81 | `text-[10px]` 타이포그래피 규칙 위반 | UI/UX+FE | USR | S |
| 82 | 에러 페이지 구체적 안내 부족 | UI/UX | USR | M |
| 83 | 삭제 확인 대상 정보 미강조 | UI/UX | USR | S |
| 84 | Studio 로딩 시 Skeleton UI 없음 | UI/UX | USR | M |
| 85 | EmptyState 액션 버튼 미제공 | UI/UX | USR | S |
| 86 | `html lang="en"` -> `"ko"` 변경 | UI/UX | USR | S |
| 87 | 모달 구현 불일치 (7개 자체 구현) | UI/UX | USR | L |

### G21. Frontend 개선 (4건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 88 | scenes payload 3중 중복 로직 | Frontend | DAT | M |
| 89 | 프로젝트/그룹 전환 시 불완전 리셋 | Frontend | USR | M |
| 90 | best candidate 중복 검증 API 호출 | Frontend | PER | S |
| 91 | Speaker 변경 시 커스텀 negative 손실 | Frontend | USR | S |

---

## P3: 백로그 (Phase 18+ / 32건)

### G22. 보안 장기 과제 (5건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 92 | 전 엔드포인트 인증 없음 (내부 도구 허용) | Security | SEC | L |
| 93 | 런타임 설정 변경 API 무방비 | Security | SEC | M |
| 94 | Static Files 직접 서빙 | Security | SEC | S |
| 95 | 의존성 버전 핀 범위 | Security | SEC | M |
| 96 | Pydantic 필드 길이 미제한 | Security | SEC | M |

### G23. DB 장기 과제 (3건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 97 | `PromptHistory.seed` Integer vs BigInteger | DBA | DAT | S |
| 98 | 마이그레이션 파일명 비표준 | DBA | DAT | S |
| 99 | 캐릭터 상세 페이지 고정 그리드 | UI/UX | USR | S |

### G24. 코드 최적화 (8건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 100 | `_expand_korean_numbers` 정규식 재컴파일 | FFmpeg | PER | S |
| 101 | `_VOICE_PROMPT_CACHE` 무제한 성장 | FFmpeg | PER | S |
| 102 | `raise exc` -> bare `raise` | FFmpeg | PER | S |
| 103 | `IGNORE_TOKENS`/`SKIP_TAGS` 빈 frozenset | Prompt | PER | S |
| 104 | `_extract_loras_from_prompt` source 부정확 | Prompt | DAT | S |
| 105 | ControlNet 통합 TODO 미구현 | Prompt | DAT | M |
| 106 | SSE 엔드포인트 OpenAPI 문서화 | Backend | DAT | S |
| 107 | `timerMap()` SSR 매번 새 Map | Frontend | PER | S |

### G25. UX 미세 개선 (10건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 108 | 인라인 제목 편집 UX 개선 | UI/UX | USR | M |
| 109 | Tooltip 포지셔닝 깜빡임 | UI/UX | USR | S |
| 110 | SceneListPanel 레이아웃 시프트 | UI/UX | USR | S |
| 111 | ErrorMessage isRetryable prop | UI/UX | USR | S |
| 112 | 버튼 border-radius 불일치 | UI/UX | USR | S |
| 113 | 언어 혼용 (한국어/영어) | UI/UX | USR | M |
| 114 | `autoSave` HMR 싱글톤 문제 | Frontend | USR | S |
| 115 | `subtitleFont` 구 네이밍 잔존 | Frontend | DAT | S |
| 116 | `loadCharacterForRole` 필드명 불일치 가능성 | Frontend | USR | S |
| 117 | `uvicorn 0.0.0.0` 바인딩 | Security | SEC | S |

### G26. 비프로덕션 / 낮은 위험 (6건)

| # | 이슈 | 에이전트 | 영향도 | 난이도 |
|---|------|---------|--------|--------|
| 118 | f-string SQL (비프로덕션 스크립트) | Security | SEC | S |
| 119 | `loadCharacterForRole` 필드명 가능성 | Frontend | USR | S |
| 120 | `text-[10px]` CLAUDE.md 위반 (FE) | Frontend | USR | S |
| 121 | `list_storyboards` deleted 씬 카운트 | DBA | DAT | S |
| 122 | `default_` prefix (StyleProfile) | DBA | DAT | M |
| 123 | `ip_adapter_reference` String Known Issue | DBA | DAT | L |

---

## Sprint 계획

### Sprint 1: P0 즉시 수정 (1주, 14건)

**목표**: 파이프라인 크래시 및 데이터 무결성 즉시 복구

| 담당 | 작업 | 건수 | 예상 공수 |
|------|------|------|----------|
| Frontend Dev | G1 null 크래시 수정 | 1건 | 1h |
| Prompt Engineer | G1 TagFilterCache 중복 + LoRA 가중치 | 2건 | 3h |
| FFmpeg Expert | G2 xfade offset 계산 수정 | 1건 | 3h |
| Backend Dev | G3 response_model 3건 + G4 soft delete | 6건 | 4h |
| DBA | G4 soft delete 전수 검사 + G5 인덱스 | 4건 | 6h |
| UI/UX Engineer | G6 htmlFor 일괄 패치 시작 | 시작 | 4h |

**검증**: 전체 테스트 3,014개 PASS + DoD 4항목 재확인

### Sprint 2: P1 긴급 수정 (2주, 32건)

**목표**: 세션 누수 해소, 프롬프트 정합성, 접근성 핵심

| 주차 | 담당 | 작업 그룹 |
|------|------|----------|
| Week 1 | Backend+DBA | G7 세션 누수 4건, G10 response_model 나머지, G11 N+1 |
| Week 1 | Prompt Eng | G8 태그 정합성 6건 |
| Week 1 | Frontend | G9 falsy 값 5건, G14 stale state 4건 |
| Week 2 | FFmpeg | G12 렌더링 품질 3건 |
| Week 2 | UI/UX | G13 ARIA 6건, G6 모바일 대응 |

### Sprint 3-4: P2 중요 개선 (3~4주, 45건)

**우선순위 순서**:
1. **보안 강화** (G15, 7건) -- SEC 영향도 최우선
2. **DB/프롬프트** (G16+G17, 11건) -- DAT 무결성
3. **Backend 코드 품질** (G18, 8건) -- 유지보수성
4. **FFmpeg 안정화** (G19, 5건)
5. **UI/UX + Frontend** (G20+G21, 14건)

### Phase 18+ 백로그 (P3, 32건)

Phase 17 완료 후 또는 이슈 심각도 변경 시 재평가.
인증 시스템(#92)은 외부 배포 결정 시 P0으로 격상.

---

## 에이전트별 부하 분포

| 에이전트 | P0 | P1 | P2 | P3 | 합계 |
|---------|----|----|----|----|------|
| Backend Dev | 4 | 5 | 8 | 1 | 18 |
| Frontend Dev | 1 | 9 | 4 | 5 | 19 |
| DBA | 3 | 1 | 5 | 3 | 12 |
| Prompt Engineer | 2 | 6 | 6 | 3 | 17 |
| FFmpeg Expert | 1 | 3 | 5 | 3 | 12 |
| UI/UX Engineer | 2 | 6 | 10 | 6 | 24 |
| Security | 0 | 0 | 7 | 6 | 13 |
| **합계** | **13** | **30** | **45** | **27** | **115** |

> 참고: 일부 이슈는 복수 에이전트 공동 담당(G7 #16 Backend+DBA 등).
> G6 #13 htmlFor은 P0(시작)+P1(완료) 분할.
> P3 중복 항목 8건은 상위 그룹에 이미 포함되어 합계 115건(실질 고유 이슈).

---

## Phase 17과의 관계

현재 Phase 17-1 (Backend 논리적 분리)이 미착수 상태.

**권장**: Sprint 1-2의 P0/P1 수정을 Phase 17-1 착수 **전에** 완료.
- 이유: response_model 누락(#5~7, #30~31)은 API 분리 리팩토링과 동시에 처리하면
  이중 작업 위험. 먼저 현재 라우터에서 수정 후 분리하는 것이 안전.
- Soft delete 전수 검사(G4)도 라우터 분리 전 완료 필요.

**Phase 17-1 착수 전 게이트**:
- [ ] P0 14건 전체 완료
- [ ] P1 중 G7(세션 누수), G10(response_model) 완료
- [ ] 전체 테스트 3,014개 PASS 유지

---

## 다음 권장 액션

1. **즉시**: G1 Frontend null 크래시 -- 사용자 직접 영향, 1시간 수정
2. **즉시**: G4 Soft Delete 전수 검사 스크립트 작성 -- 누락 지점 일괄 식별
3. **이번 주**: G2 xfade + G3 response_model -- 파이프라인 안정성 확보
4. **다음 주**: G8 프롬프트 태그 정합성 -- Zero Variance 원칙 직결
5. **Sprint 2**: G15 보안 강화 착수 -- 외부 배포 대비

> 이 보고서는 `docs/01_product/FEATURES/CROSS_AGENT_AUDIT_2026_02_26.md`에 저장.
> 진행 상황은 ROADMAP.md "잔여 작업 우선순위" 섹션에 반영 예정.
