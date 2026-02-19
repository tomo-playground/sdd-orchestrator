# Frontend

Next.js 16 + React 19 + Zustand 5 기반 워크스페이스 UI. Studio, Library, Settings 등 11개 페이지.

> 프로젝트 전체 개요: [README.md](../README.md) / 개발 가이드: [CONTRIBUTING.md](../docs/guides/CONTRIBUTING.md)

---

## 구조

```
frontend/app/
├── (app)/               # 페이지 (App Router)
│   ├── page.tsx         #   Home (대시보드)
│   ├── studio/          #   Studio (Script / Edit / Publish)
│   ├── scripts/         #   스크립트 관리
│   ├── storyboards/     #   스토리보드 관리
│   ├── characters/      #   캐릭터 (목록/상세/신규)
│   ├── library/         #   Library (7탭)
│   ├── settings/        #   Settings (5탭)
│   ├── voices/          #   음성 프리셋
│   ├── music/           #   음악 프리셋
│   ├── backgrounds/     #   배경 에셋
│   ├── lab/             #   Lab (실험)
│   └── pipeline-demo/   #   파이프라인 데모
├── store/               # Zustand 4-Store
│   ├── useUIStore.ts    #   Toast, Modal, Tab
│   ├── useContextStore.ts   # Project/Group, Config
│   ├── useStoryboardStore.ts # Scenes, Characters
│   ├── useRenderStore.ts    # Layout, Audio, Output
│   ├── actions/         #   비동기 액션 (14개 모듈)
│   └── selectors/       #   파생 상태
├── hooks/               # 커스텀 훅 (25개)
├── components/          # UI 컴포넌트 (19개 디렉토리)
├── types/               # TypeScript 타입 (73+ 타입)
└── utils/               # 유틸리티 함수
```

---

## 실행

```bash
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL 등
npm run dev                        # http://localhost:3000
```

---

## Scripts

```bash
npm run dev              # 개발 서버
npm run build            # 프로덕션 빌드
npm run start            # 프로덕션 서버
npm run lint             # ESLint
npm test                 # 단위 테스트 (vitest)
npm run test:vrt         # VRT (Playwright 스크린샷 비교)
npm run test:vrt:update  # VRT baseline 갱신
npm run test:vrt:ui      # VRT UI 모드
```

---

## 상태 관리

4-Store 구조 (Zustand 5):

| Store | 역할 | Persistence |
|-------|------|-------------|
| `useUIStore` | Toast, Modal, Tab | 없음 |
| `useContextStore` | Project/Group, Cascading Config | 부분 |
| `useStoryboardStore` | Scenes, Characters, Validation | 부분 |
| `useRenderStore` | Layout, Audio, Output | 부분 |

상세: [STATE_MANAGEMENT.md](../docs/03_engineering/frontend/STATE_MANAGEMENT.md)

---

## 테스트 현황

| 유형 | 테스트 수 | 도구 |
|------|----------|------|
| Unit | 352 | vitest |
| VRT | 24 screenshots (8 specs) | Playwright |
| E2E | 3 specs | Playwright |

상세: [TEST_STRATEGY.md](../docs/03_engineering/testing/TEST_STRATEGY.md) / [VRT_GUIDE.md](../docs/03_engineering/testing/VRT_GUIDE.md)
