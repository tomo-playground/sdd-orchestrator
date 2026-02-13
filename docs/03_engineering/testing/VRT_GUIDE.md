# VRT (Visual Regression Testing) Guide

## 1. 개요

VRT는 **스크린샷 비교** 기반으로 UI 변경 시 시각적 회귀를 감지하는 테스트입니다.

| 항목 | 값 |
|------|-----|
| 도구 | Playwright `toHaveScreenshot()` |
| 범위 | 8개 페이지, 24개 스크린샷 |
| 환경 | macOS 로컬 전용 (CI 없음) |
| 저장 | Git 직접 커밋 (~528KB) |

---

## 2. 실행 방법

```bash
cd frontend

# VRT 실행 (baseline 대비 비교)
npm run test:vrt

# Baseline 스크린샷 생성/갱신
npm run test:vrt:update

# Playwright UI에서 diff 확인
npm run test:vrt:ui
```

---

## 3. 스크린샷 목록

### Studio (`studio.vrt.spec.ts`)
| 이름 | 상태 |
|------|------|
| `studio-empty.png` | 빈 스튜디오 |
| `studio-with-scenes.png` | 씬이 있는 스튜디오 (?id=1) |

### Characters (`characters.vrt.spec.ts`)
| 이름 | 상태 |
|------|------|
| `characters-list.png` | 캐릭터 목록 (2개) |
| `characters-empty.png` | 빈 캐릭터 목록 |
| `characters-new.png` | 새 캐릭터 생성 폼 |
| `characters-detail.png` | 캐릭터 상세 |

### Voices (`voices.vrt.spec.ts`)
| 이름 | 상태 |
|------|------|
| `voices-list.png` | 보이스 프리셋 목록 |
| `voices-empty.png` | 빈 보이스 목록 |

### Music (`music.vrt.spec.ts`)
| 이름 | 상태 |
|------|------|
| `music-list.png` | 음악 프리셋 목록 |
| `music-empty.png` | 빈 음악 목록 |

### Backgrounds (`backgrounds.vrt.spec.ts`)
| 이름 | 상태 |
|------|------|
| `backgrounds-list.png` | 배경 목록 |
| `backgrounds-empty.png` | 빈 배경 목록 |

### Scripts (`scripts.vrt.spec.ts`)
| 이름 | 상태 |
|------|------|
| `scripts-list.png` | 스크립트 목록 |
| `scripts-empty.png` | 빈 스크립트 목록 |

### Lab (`lab.vrt.spec.ts`)
| 이름 | 상태 |
|------|------|
| `lab-tag-lab.png` | Tag Lab 탭 |
| `lab-scene-lab.png` | Scene Lab 탭 |
| `lab-analytics.png` | Analytics 탭 |

### Manage (`manage.vrt.spec.ts`)
| 이름 | 상태 |
|------|------|
| `manage-tags.png` | Tags 탭 |
| `manage-style.png` | Style 탭 |
| `manage-prompts.png` | Prompts 탭 |
| `manage-presets.png` | Render Presets 탭 |
| `manage-youtube.png` | YouTube 탭 |
| `manage-settings.png` | Settings 탭 |
| `manage-trash.png` | Trash 탭 |

---

## 4. 새 테스트 추가 방법

### Step 1: Mock 데이터 추가

`frontend/tests/helpers/fixtures/` 에 필요한 fixture 데이터 추가.

### Step 2: Mock API 함수 추가/수정

`frontend/tests/helpers/mockApi.ts` 에 `page.route()` 패턴으로 API 인터셉터 추가.

### Step 3: VRT 스펙 작성

```typescript
import { test, expect } from "@playwright/test";
import { mockGlobalApis, mockXxxApis } from "../helpers/mockApi";
import { clearLocalStorage, hideAnimations, waitForPageReady } from "../helpers/vrtUtils";

test.describe("PageName — VRT", () => {
  test.beforeEach(async ({ page }) => {
    await clearLocalStorage(page);
    await mockGlobalApis(page);
    await mockXxxApis(page);
  });

  test("screenshot-name", async ({ page }) => {
    await page.goto("/path");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("screenshot-name.png");
  });
});
```

### Step 4: Baseline 생성

```bash
npm run test:vrt:update
```

### Step 5: Git 커밋

`__snapshots__/` 디렉토리의 새 PNG 파일을 커밋.

---

## 5. 실패 대응

### 의도적 UI 변경

CSS/컴포넌트 변경으로 인한 정상적인 실패:

```bash
npm run test:vrt:update   # baseline 갱신
npm run test:vrt           # 통과 확인
git add tests/vrt/__snapshots__/
git commit -m "chore: update VRT baselines"
```

### 의도치 않은 변경

예상치 못한 실패:

1. `npm run test:vrt:ui` 로 diff 확인
2. 원인 파악 및 코드 수정
3. `npm run test:vrt` 로 통과 확인

---

## 6. 유틸리티 (`vrtUtils.ts`)

| 함수 | 역할 |
|------|------|
| `waitForPageReady(page)` | networkidle + skeleton 사라짐 대기 |
| `hideAnimations(page)` | CSS animation/transition 0s 주입 |
| `clearLocalStorage(page)` | Zustand persisted state 초기화 |

---

## 7. Mock 데이터 구조

```
tests/helpers/
├── fixtures/
│   ├── index.ts          # 전체 re-export
│   ├── common.ts         # 프로젝트, 그룹 (AppShell 공통)
│   ├── characters.ts     # 캐릭터 목록/상세
│   ├── voices.ts         # 보이스 프리셋
│   ├── music.ts          # 음악 프리셋
│   ├── backgrounds.ts    # 배경
│   ├── manage.ts         # 관리 페이지 데이터
│   └── lab.ts            # Lab 페이지 데이터
├── mockApi.ts            # page.route() 기반 API 인터셉터
└── vrtUtils.ts           # 스크린샷 안정화 유틸리티
```

---

## 8. 설정 (`playwright.config.ts`)

| 항목 | 값 |
|------|-----|
| `testDir` | `./tests/vrt` |
| `snapshotDir` | `./tests/vrt/__snapshots__` |
| `maxDiffPixels` | 100 |
| `threshold` | 0.2 |
| `animations` | `disabled` |
| `browser` | Chromium (Desktop Chrome) |
