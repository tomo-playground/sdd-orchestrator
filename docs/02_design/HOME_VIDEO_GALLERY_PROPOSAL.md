# Home Video Gallery UI/UX 제안서

**작성일**: 2026-02-15
**담당**: UI/UX Engineer
**목적**: Home 페이지를 단순 "최근 3개 영상" 쇼케이스에서 → **전체 프로젝트 영상 큐레이션 갤러리**로 확장

---

## 1. 현재 상태 분석

### 1.1 기존 Home 구조
```
ShowcaseSection       — 최신 3개 영상 (localStorage 기반)
QuickActionsWidget    — 빠른 액션 4개 버튼
QuickStatsWidget      — 라이브러리 통계 4개
Footer
```

### 1.2 문제점
| 문제 | 영향 |
|------|------|
| **데이터 손실** | localStorage 기반 → 스토리보드 전환 시 리셋 |
| **제한된 발견성** | 최대 3개만 표시 → 과거 영상 접근 불가 |
| **큐레이션 부재** | 프로젝트별/레이아웃별 필터링 불가 |
| **컨텍스트 부족** | 영상 메타데이터(프로젝트명, 업로드 상태 등) 최소화 |
| **Empty State 약함** | "Your Showcase Awaits" → 동기부여 약함 |

### 1.3 사용자 니즈
- **발견**: "지난달에 만든 Post 영상 어디갔지?"
- **비교**: "Full vs Post 레이아웃 중 어떤 게 더 나았지?"
- **재사용**: "이 프로젝트 영상들을 한 번에 보고 싶다"
- **관리**: "YouTube 업로드 완료된 영상만 보고 싶다"

---

## 2. 제안 개요

### 2.1 핵심 컨셉
**"영상 포트폴리오 대시보드"** — 모든 렌더링 영상을 한눈에, 다양한 관점으로 큐레이션

### 2.2 디자인 원칙
1. **Progressive Disclosure**: 정보 과부하 방지 (접기/펼치기, 페이지네이션)
2. **Consistency**: 기존 QuickActions/QuickStats 패턴 유지
3. **Accessibility**: 키보드 내비게이션 + 스크린 리더 지원
4. **Performance**: 무한 스크롤 (가상화) 또는 페이지네이션

---

## 3. UI 제안

### 3.1 레이아웃 구조 (수정안)
```
┌─────────────────────────────────────────────┐
│ Hero Video Gallery                           │ ← 새로운 섹션
│ ┌─────────────────────────────────────────┐ │
│ │ [필터 칩: Recent | By Project | ...]    │ │
│ │ [그리드: 영상 카드 × N]                 │ │
│ └─────────────────────────────────────────┘ │
├─────────────────────────────────────────────┤
│ Quick Actions Widget                         │ ← 유지 (약간 축소)
├─────────────────────────────────────────────┤
│ Quick Stats Widget                           │ ← 유지
└─────────────────────────────────────────────┘
```

**변경 사항**:
- **ShowcaseSection 대체** → Hero Video Gallery (전체 영상 큐레이션)
- **QuickActions/Stats 유지** → 사용자에게 익숙한 진입점 보존
- **순서**: Gallery → Actions → Stats (영상 먼저, 액션은 보조)

### 3.2 영상 카드 디자인

#### 3.2.1 기본 카드 (그리드 아이템)
```
┌───────────────────┐
│ [9:16 썸네일]      │ ← aspect-ratio: 9/16, max-height: 320px
│ ┌───────────────┐ │
│ │   Video       │ │
│ │   Preview     │ │ ← hover: 재생 아이콘 오버레이
│ └───────────────┘ │
│ ─────────────────  │
│ 프로젝트명         │ ← font-semibold, truncate
│ [Full] • 2h ago   │ ← 배지 + 상대 시간
│ [YT] [★]          │ ← 상태 배지 (업로드/즐겨찾기)
└───────────────────┘
```

#### 3.2.2 메타데이터 우선순위
| 필수 | 선택 |
|------|------|
| 썸네일 (video preload="metadata") | 해시태그 |
| 프로젝트명 (fallback: "2h ago 영상") | 씬 개수 |
| 레이아웃 배지 (Full/Post) | 조회수 (향후) |
| 생성 시간 (상대 시간) | 좋아요 (향후) |
| YouTube 업로드 상태 | |

#### 3.2.3 상태 배지 디자인
| 상태 | 배지 | 색상 |
|------|------|------|
| Layout | `Full` / `Post` | `bg-zinc-100 text-zinc-600` |
| YouTube | `YT` | `bg-red-50 text-red-500` (기존과 동일) |
| Starred | `★` | `bg-amber-50 text-amber-500` |
| New (24h) | `New` | `bg-emerald-50 text-emerald-600` (기존과 동일) |

### 3.3 큐레이션 필터 UI

#### 3.3.1 필터 칩 (Horizontal Scroll)
**레이아웃**: 상단 고정, 수평 스크롤 (모바일 대응)

```
┌─────────────────────────────────────────────────────────┐
│ [Recent ✓] [By Project] [Published] [Full] [Post] [★]  │ ← 스크롤 가능
└─────────────────────────────────────────────────────────┘
```

**인터랙션**:
- 클릭 시 active 상태 토글 (`border-zinc-900 bg-zinc-900 text-white`)
- 멀티 선택 가능 (예: `Full` + `Published` = Full 레이아웃 + YouTube 업로드)
- 선택 해제: 다시 클릭 또는 전체 초기화 버튼

#### 3.3.2 필터 옵션 (Phase 1)
| 필터 | 설명 | 구현 |
|------|------|------|
| **Recent** | 전체 영상 시간순 (기본) | `sort: createdAt desc` |
| **By Project** | 프로젝트별 그룹핑 | `group by projectId` + 대표 1건 |
| **Published** | YouTube 업로드 완료 | `filter: yt_video_id IS NOT NULL` |
| **Full** | 9:16 레이아웃만 | `filter: layout = 'full'` |
| **Post** | Post 레이아웃만 | `filter: layout = 'post'` |
| **Starred** | 즐겨찾기 | `filter: is_starred = true` (신규 필드) |

#### 3.3.3 Phase 2 확장 (향후)
- **By Character**: 특정 캐릭터가 등장하는 영상
- **By Style**: 특정 스타일 프로필 사용 영상
- **Date Range**: 날짜 범위 필터 (드롭다운)
- **Duration**: 영상 길이 (짧은순/긴순)

### 3.4 그리드 vs 피드 vs 캐러셀 비교

| 레이아웃 | 장점 | 단점 | 추천 |
|---------|------|------|------|
| **그리드** | 한눈에 많은 영상 표시, YouTube/Instagram 익숙함 | 개별 영상 크기 작음 | ✅ **추천** |
| **피드** | 스토리텔링 강조, TikTok 스타일 | 한 번에 1개만 → 발견성 약함 | 향후 "몰입 모드"로 추가 |
| **캐러셀** | 디자인 깔끔 | 숨겨진 영상 많음 → UX 나쁨 | ❌ 비추천 |

**결론**: **그리드** 채택 (YouTube Shorts 그리드 패턴과 유사)

### 3.5 그리드 사양
```css
/* Desktop (1024px+) */
grid-template-columns: repeat(auto-fill, minmax(225px, 1fr));
gap: 1rem; /* 16px */

/* Tablet (768px-1023px) */
grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));

/* Mobile (320px-767px) */
grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
gap: 0.75rem; /* 12px */
```

**무한 스크롤 vs 페이지네이션**:
- **Phase 1**: 페이지네이션 (20개/페이지) → 구현 단순
- **Phase 2**: 무한 스크롤 (react-window 가상화) → 성능 최적화

---

## 4. 기존 위젯과의 조화

### 4.1 QuickActions — 공존 (약간 축소)

**변경 사항**:
- 그리드 `4칸` 유지 (Desktop)
- 아이콘 크기 축소: `h-6 w-6` → `h-5 w-5`
- 패딩 축소: `p-6` → `p-4`
- 제목 크기 축소: `text-xl` → `text-lg`

**이유**: Gallery가 Hero 영역을 차지하므로, Actions는 보조 역할로 축소

### 4.2 QuickStats — 유지

**변경 없음** — 통계는 정보 전달이 목적이므로 현재 크기 유지

### 4.3 순서 조정 (Before/After)

| Before | After |
|--------|-------|
| ShowcaseSection (3개) | **Hero Video Gallery** (필터 + 그리드) |
| QuickActions | QuickActions (약간 축소) |
| QuickStats | QuickStats |
| Footer | Footer |

---

## 5. Empty State 개선

### 5.1 현재 Empty State (문제점)
```
┌─────────────────────────────────────────┐
│ [✨ 아이콘]                              │
│ Your Showcase Awaits                    │
│ Create your first video...              │
│ [Start Creating 버튼]                   │
└─────────────────────────────────────────┘
```

**문제**: 동기부여 약함, 다음 액션 모호

### 5.2 개선안 (단계별 안내)
```
┌─────────────────────────────────────────┐
│ [🎬 Clapperboard 아이콘]                │
│ 첫 영상을 만들어보세요                   │
│                                         │
│ 1️⃣ 캐릭터 생성 → 2️⃣ 스토리보드 작성    │
│ → 3️⃣ 이미지 생성 → 4️⃣ 렌더링           │
│                                         │
│ [New Project] [튜토리얼 보기]            │
└─────────────────────────────────────────┘
```

**개선 사항**:
- **명확한 플로우**: 4단계 시각화
- **2개 CTA**: Primary (New Project) + Secondary (튜토리얼)
- **감성적 메시지**: "Your Showcase Awaits" → "첫 영상을 만들어보세요"

### 5.3 부분 Empty State (필터링 결과 0건)
```
┌─────────────────────────────────────────┐
│ [🔍 Search 아이콘]                       │
│ 해당 조건의 영상이 없습니다               │
│ 다른 필터를 시도해보세요                 │
│ [필터 초기화]                            │
└─────────────────────────────────────────┘
```

---

## 6. 반응형 고려사항

### 6.1 브레이크포인트
| 디바이스 | 뷰포트 | 그리드 열 | 카드 크기 |
|---------|--------|---------|---------|
| Desktop | 1024px+ | 4-5열 | 225px |
| Tablet | 768-1023px | 3열 | 180px |
| Mobile | 320-767px | 2열 | 150px |

### 6.2 모바일 최적화
- **필터 칩**: 수평 스크롤 (고정 상단)
- **카드 간격**: `gap-4` → `gap-3` (16px → 12px)
- **썸네일 높이**: `max-h-320px` → `max-h-240px`
- **메타데이터**: 프로젝트명만 표시 (시간 생략)

### 6.3 터치 인터랙션
- **카드 탭**: 모달 플레이어 오픈
- **롱 프레스**: 컨텍스트 메뉴 (삭제/즐겨찾기/공유)
- **스와이프**: (향후) 좌우 스와이프로 이전/다음 영상

---

## 7. 접근성 (A11y)

### 7.1 키보드 내비게이션
| 키 | 동작 |
|----|------|
| `Tab` | 다음 카드로 포커스 이동 |
| `Shift+Tab` | 이전 카드로 포커스 이동 |
| `Enter` / `Space` | 모달 플레이어 오픈 |
| `Escape` | 모달 닫기 |
| `Arrow Keys` | (향후) 그리드 내 방향 이동 |

### 7.2 ARIA 속성
```tsx
<article
  role="article"
  aria-label={`영상: ${projectName}, ${layout}, ${time}`}
>
  <button aria-label="영상 재생">
    <video aria-hidden="true" />
  </button>
</article>
```

### 7.3 색상 대비
- **배지 텍스트**: WCAG AA 기준 (4.5:1) 준수
- **호버 상태**: 명확한 시각적 피드백 (border + shadow)
- **포커스 링**: `focus-visible:ring-2 ring-zinc-900`

---

## 8. 성능 최적화

### 8.1 이미지 로딩
- **Lazy Loading**: `<video loading="lazy" preload="metadata">`
- **썸네일 추출**: (향후) 첫 프레임 이미지로 대체 → 네트워크 절약
- **CDN**: MinIO URL → CloudFront CDN (향후)

### 8.2 무한 스크롤 최적화 (Phase 2)
- **가상화**: `react-window` 또는 `@tanstack/react-virtual`
- **페치 전략**: Intersection Observer로 하단 도달 시 추가 로드
- **캐싱**: React Query로 API 응답 캐싱

### 8.3 Lighthouse 목표
| 항목 | 목표 |
|------|------|
| Performance | 90+ |
| Accessibility | 95+ |
| Best Practices | 90+ |
| SEO | 90+ |

---

## 9. 구현 로드맵

### Phase 1 — MVP (1주)
- [x] Backend: `/api/render-history` 엔드포인트 (필터링 지원)
- [ ] Frontend: Hero Video Gallery 컴포넌트
- [ ] 필터 칩 (Recent, By Project, Published, Full, Post)
- [ ] 그리드 레이아웃 (페이지네이션)
- [ ] 모달 플레이어 (기존 재사용)
- [ ] Empty State 개선

### Phase 2 — 큐레이션 강화 (2주)
- [ ] 즐겨찾기 기능 (`is_starred` 필드 추가)
- [ ] By Character / By Style 필터
- [ ] 무한 스크롤 (가상화)
- [ ] 검색 기능 (프로젝트명/해시태그)
- [ ] 정렬 옵션 (최신순/오래된순/인기순)

### Phase 3 — 고급 기능 (3주)
- [ ] 일괄 작업 (다중 선택 + 삭제/다운로드)
- [ ] 공유 기능 (링크 복사/SNS 공유)
- [ ] 통계 대시보드 (조회수/좋아요 연동)
- [ ] AI 추천 ("이 영상을 좋아한다면...")

---

## 10. 디자인 핸드오프 체크리스트

### 10.1 Frontend Dev에 전달할 산출물
- [x] 이 제안서 (`HOME_VIDEO_GALLERY_PROPOSAL.md`)
- [ ] 와이어프레임 (Figma 또는 Excalidraw)
- [ ] 컴포넌트 계층 구조 다이어그램
- [ ] Tailwind CSS 스타일 가이드 (색상/간격/폰트)
- [ ] 상태 관리 요구사항 (Zustand 슬라이스 설계)

### 10.2 컴포넌트 계층 구조 (예상)
```
HomeVideoGallery/
├── FilterChips.tsx        — 필터 칩 (수평 스크롤)
├── VideoGrid.tsx          — 그리드 컨테이너
│   └── VideoCard.tsx      — 개별 영상 카드
├── VideoPlayerModal.tsx   — 모달 플레이어 (기존 재사용)
├── EmptyState.tsx         — Empty State
└── Pagination.tsx         — 페이지네이션
```

### 10.3 상태 관리 요구사항
```typescript
// useRenderStore.ts에 추가할 슬라이스
type VideoGallerySlice = {
  // 필터 상태
  activeFilters: Set<'recent' | 'by_project' | 'published' | 'full' | 'post' | 'starred'>;
  setActiveFilters: (filters: Set<...>) => void;

  // 페이지네이션
  currentPage: number;
  totalPages: number;
  setCurrentPage: (page: number) => void;

  // 영상 목록 (API에서 fetch)
  videos: RecentVideo[];
  fetchVideos: () => Promise<void>;

  // 즐겨찾기
  toggleStar: (videoUrl: string) => Promise<void>;
};
```

### 10.4 API 요구사항 (Backend Dev 협업)
```typescript
// GET /api/render-history
type RenderHistoryQuery = {
  page?: number;
  limit?: number;
  layout?: 'full' | 'post';
  project_id?: number;
  is_published?: boolean; // yt_video_id IS NOT NULL
  is_starred?: boolean;
  sort?: 'created_at_desc' | 'created_at_asc';
};

type RenderHistoryResponse = {
  items: RecentVideo[];
  total: number;
  page: number;
  pages: number;
};
```

---

## 11. 디자인 결정 기록 (ADR)

### ADR-001: 그리드 레이아웃 채택
**결정**: 그리드 레이아웃 사용 (피드/캐러셀 대신)
**이유**:
- YouTube Shorts/Instagram Reels 사용자에게 익숙한 패턴
- 한눈에 많은 영상 표시 → 발견성 향상
- 반응형 대응 용이 (auto-fill)

**대안**:
- 피드: 몰입감 강하나 발견성 약함 → Phase 2 "몰입 모드"로 추가 검토
- 캐러셀: 숨겨진 영상 많음 → UX 나쁨

### ADR-002: 필터 칩 (탭 대신)
**결정**: 필터 칩 (멀티 선택 가능)
**이유**:
- 멀티 필터 조합 가능 (예: `Full + Published`)
- 모바일 수평 스크롤로 공간 절약
- 시각적으로 active 상태 명확

**대안**:
- 탭: 단일 선택만 가능 → 제한적
- 드롭다운: 숨겨진 옵션 → 발견성 약함

### ADR-003: QuickActions/Stats 유지
**결정**: 기존 위젯 유지 (약간 축소)
**이유**:
- 사용자에게 익숙한 진입점 보존
- Gallery와 역할 구분 (영상 큐레이션 vs 빠른 액션)
- 점진적 개선 (Breaking Change 최소화)

**대안**:
- 완전 대체: 사용자 혼란 우려
- 통합: 역할 모호해짐

---

## 12. 참조

### 12.1 유사 서비스 벤치마킹
| 서비스 | 레이아웃 | 필터 | 배운 점 |
|--------|---------|------|---------|
| YouTube Shorts | 그리드 | 없음 | 9:16 썸네일 그리드 효과적 |
| Instagram Reels | 그리드 | 없음 | 배지 활용 (음원, 조회수) |
| TikTok Studio | 피드 + 그리드 | 태그 | 필터 칩 수평 스크롤 패턴 |
| Canva Projects | 그리드 | 폴더/태그 | 프로젝트별 그룹핑 |

### 12.2 디자인 시스템 참조
- **색상**: Tailwind Zinc 팔레트 (기존 유지)
- **간격**: 4px 그리드 시스템 (`gap-3`, `gap-4`)
- **폰트**: 최소 `text-xs` (13px) 이상 (CLAUDE.md Typography Rules 준수)
- **아이콘**: Lucide React (기존 QuickActions와 일관성)

### 12.3 관련 문서
- `docs/01_product/PRD.md` — DoD 참조
- `docs/03_engineering/frontend/STATE_MANAGEMENT.md` — Zustand 패턴
- `CLAUDE.md` — UI Typography Rules

---

## 부록: 와이어프레임 (텍스트 스케치)

```
┌─────────────────────────────────────────────────────────────────┐
│ Home / Video Gallery                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 🎬 Your Video Gallery                                          │
│ 모든 렌더링 영상을 한눈에                                        │
│                                                                 │
│ [Recent ✓] [By Project] [Published] [Full] [Post] [★]  ←→     │ ← 스크롤
│                                                                 │
│ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                              │
│ │9:16 │ │9:16 │ │9:16 │ │9:16 │                              │
│ │Thumb│ │Thumb│ │Thumb│ │Thumb│                              │
│ └─────┘ └─────┘ └─────┘ └─────┘                              │
│ Project1 Project2 Project3 Project4                           │
│ [Full]   [Post]   [Full]   [Post]                            │
│ 2h ago   1d ago   3d ago   1w ago                             │
│ [YT]     [★]      [New]    [YT][★]                           │
│                                                                 │
│ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                              │
│ │     │ │     │ │     │ │     │                              │
│ └─────┘ └─────┘ └─────┘ └─────┘                              │
│                                                                 │
│                    ← 1 2 3 4 5 →                              │ ← 페이지네이션
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ ⚡ Quick Actions                                                │
│ [New Project] [Create Character] [Browse Styles] [Browse Voices]│
├─────────────────────────────────────────────────────────────────┤
│ 📚 Your Library                                                 │
│ [12 Characters] [8 Styles] [5 Voices] [3 Music]                │
└─────────────────────────────────────────────────────────────────┘
```

---

**다음 단계**:
1. Frontend Dev와 핸드오프 미팅 (컴포넌트 계층 구조 리뷰)
2. Backend Dev와 API 스펙 협의 (`/api/render-history` 필터링)
3. Figma 와이어프레임 작성 (선택적)
4. Phase 1 MVP 구현 시작
