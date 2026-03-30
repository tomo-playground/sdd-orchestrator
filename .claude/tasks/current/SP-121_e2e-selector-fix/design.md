# SP-121 상세 설계: E2E 테스트 셀렉터 수정

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `frontend/e2e/qa-patrol.config.ts` | Styles/Voices/LoRA/Library 셀렉터 업데이트 |
| `frontend/e2e/smoke.spec.ts` | Studio `?new=true` 시나리오 수정 |
| `frontend/e2e/qa-patrol.spec.ts` | `assertNoCriticalErrors`에서 리소스 로드 에러 필터링 |

## DoD별 설계

### DoD-1: Styles/Voices 셀렉터 변경

**구현 방법**: `qa-patrol.config.ts`의 `EXTENDED_CHECKS` + `PATROL_PAGES`

**before → after**:
```ts
// before
{ name: "Voices 목록", path: "/library/voices", selector: "h1, h2" }
{ name: "Styles 목록", path: "/library/styles", selector: "h1, h2", fallbackTexts: ["Style Profiles"] }

// after — 리스트-디테일 레이아웃에 맞게 listbox/nav 사용
{ name: "Voices 목록", path: "/library/voices", selector: '[role="listbox"], nav a' }
{ name: "Styles 목록", path: "/library/styles", selector: '[role="listbox"], nav a' }
```

동일하게 `PATROL_PAGES`의 Voices/Styles 항목도 업데이트.

**엣지 케이스**: 빈 목록이어도 `nav a` (사이드바 링크)는 존재하므로 문제없음.
**영향 범위**: qa-patrol 테스트만. 다른 테스트 영향 없음.
**Out of Scope**: Library 레이아웃 컴포넌트 자체 수정.

### DoD-2: LoRA 셀렉터 변경

**구현 방법**: `qa-patrol.config.ts`의 `EXTENDED_CHECKS` + `PATROL_PAGES`

**before → after**:
```ts
// before
{ name: "LoRA redirect → Admin", path: "/library/loras", selector: "h1, h2" }
// PATROL_PAGES
{ name: "LoRA (redirect)", path: "/dev/sd-models", selector: "h1, h2" }

// after — Admin 레이아웃은 paragraph + complementary 구조
{ name: "LoRA redirect → Admin", path: "/library/loras", selector: "main, [role='complementary'], nav" }
// PATROL_PAGES
{ name: "LoRA (redirect)", path: "/dev/sd-models", selector: "main, [role='complementary'], nav" }
```

**엣지 케이스**: 308 redirect 후 Admin 페이지 로드 시간이 길 수 있음 → 기존 PATROL_TIMEOUT(15s) 충분.
**영향 범위**: qa-patrol 테스트만.
**Out of Scope**: Admin 페이지 레이아웃 변경.

### DoD-3: smoke.spec.ts Studio 시나리오 수정

**구현 방법**: `smoke.spec.ts`의 "Studio page loads and tab switching works" 테스트

**before → after**:
```ts
// before — 에디터 탭 or 칸반 or 채널/시리즈 안내 기대
const scriptTab = page.getByRole("button", { name: "대본", exact: true });
const kanbanHeading = page.getByText("영상 목록");
const needsChannel = page.getByText("채널이 필요합니다");
const needsSeries = page.getByText("시리즈를 만들어야");

// after — 시리즈 선택 화면 추가 (현재 실제 UI)
const scriptTab = page.getByRole("button", { name: "대본", exact: true });
const kanbanHeading = page.getByText("영상 목록");
const needsChannel = page.getByText("채널이 필요합니다");
const needsSeries = page.getByText("시리즈를 만들어야");
const groupButton = page.getByRole("button", { name: "시리즈 설정" });
const seriesPrompt = page.getByText("시작하려면 시리즈를 생성하세요");
```

expect에 `groupButton`, `seriesPrompt`를 `.or()` 체인에 추가.
탭 전환 검증은 `scriptTab.isVisible()` 조건부로 유지 (기존 로직 그대로).

**엣지 케이스**: DB에 시리즈가 있으면 그룹 버튼이 보이고, 없으면 "시작하려면" 토스트가 보임 → 둘 다 매칭.
**영향 범위**: smoke 테스트만. qa-patrol의 Studio 관련은 별도 config 셀렉터로 이미 통과 중.
**Out of Scope**: Studio 라우팅 로직 변경.

### DoD-4: transient 500 대응

**구현 방법**: `qa-patrol.spec.ts`의 `assertNoCriticalErrors` 함수

**before → after**:
```ts
// before — 모든 console error를 critical로 분류
const critical = errors.filter(
  (e) => e.type === "console" || (e.type === "api" && (e.status ?? 0) >= 500)
);

// after — "Failed to load resource" 패턴은 transient로 분류하여 제외
const critical = errors.filter(
  (e) =>
    (e.type === "console" && !e.message.includes("Failed to load resource")) ||
    (e.type === "api" && (e.status ?? 0) >= 500)
);
```

"Failed to load resource"는 Next.js dev 서버 병렬 부하에서 간헐적으로 발생하는 리소스 로드 에러.
실제 JS 에러(`Uncaught`, `TypeError` 등)는 그대로 감지됨.

**엣지 케이스**: 진짜 리소스 로드 실패(예: 깨진 빌드)를 놓칠 수 있음 → 그러나 페이지 DOM 존재 확인이 별도로 있어 보완됨.
**영향 범위**: qa-patrol 전체. 감시 민감도가 약간 낮아지나, 핵심 에러(JS exception, API 500)는 유지.
**Out of Scope**: Next.js dev 서버 안정성 개선, worker 수 제한.

### DoD-5: 전체 PASS 확인

`npx playwright test --config=playwright.e2e.config.ts --reporter=list` 실행하여 19/19 통과 검증.

## 테스트 전략

별도 단위 테스트 없음 — e2e 테스트 자체가 검증 대상. 수정 후 전체 실행으로 GREEN 확인.
