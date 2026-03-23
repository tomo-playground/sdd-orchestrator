import { test, expect, type Page } from "@playwright/test";

/**
 * QA Patrol — 핵심 플로우 자동 순찰
 *
 * 감지 항목:
 * - 콘솔 에러 (JS errors)
 * - API 4xx/5xx 응답
 * - DOM 요소 부재 (로딩 실패)
 * - 로딩 timeout
 */

interface PatrolError {
  type: "console" | "api" | "dom" | "timeout";
  message: string;
  url?: string;
  status?: number;
}

/** 쿼리 파라미터·해시를 제거해 토큰/PII 유출 방지 */
function redactUrl(raw: string): string {
  try {
    const u = new URL(raw);
    return `${u.origin}${u.pathname}`;
  } catch {
    return raw.split("?")[0];
  }
}

/** 민감 키워드 마스킹 + 500자 truncate */
function redactMessage(raw: string): string {
  return raw
    .replace(/(token|authorization|password|apikey|api_key|secret)=([^&\s"']+)/gi, "$1=[REDACTED]")
    .slice(0, 500);
}

function setupErrorCollector(page: Page) {
  const errors: PatrolError[] = [];

  page.on("console", (msg) => {
    if (msg.type() === "error") {
      const text = msg.text();
      if (text.includes("Warning:") || text.includes("DevTools")) return;
      errors.push({ type: "console", message: redactMessage(text), url: redactUrl(page.url()) });
    }
  });

  page.on("pageerror", (err) => {
    errors.push({
      type: "console",
      message: redactMessage(`Uncaught: ${err.message}`),
      url: redactUrl(page.url()),
    });
  });

  page.on("response", (response) => {
    const status = response.status();
    const url = response.url();
    if (status >= 400 && url.includes("/api/")) {
      const safeUrl = redactUrl(url);
      errors.push({ type: "api", message: `${status} ${safeUrl}`, status, url: safeUrl });
    }
  });

  return errors;
}

async function assertNoCriticalErrors(page: Page, errors: PatrolError[]) {
  await Promise.race([page.waitForLoadState("networkidle"), page.waitForTimeout(2000)]);
  const critical = errors.filter(
    (e) => e.type === "console" || (e.type === "api" && (e.status ?? 0) >= 500)
  );
  expect(critical, `Critical errors: ${JSON.stringify(critical)}`).toHaveLength(0);
}

// ── 순찰 대상 페이지 ──
const PATROL_PAGES = [
  { name: "홈", path: "/", selector: "h1, h2" },
  {
    name: "Studio 칸반",
    path: "/studio",
    selector: "영상 목록, 채널이 필요합니다, 시리즈를 만들어야",
  },
  { name: "새 영상", path: "/studio?new=true", selector: "button" },
  { name: "Settings", path: "/settings", selector: "a" },
  { name: "Library", path: "/library", selector: "h1, h2" },
  { name: "Characters", path: "/library/characters", selector: "h1, h2, 캐릭터" },
  { name: "Voices", path: "/library/voices", selector: "h1, h2" },
  { name: "Styles", path: "/library/styles", selector: "h1, h2" },
  { name: "LoRA", path: "/library/loras", selector: "h1, h2" },
  { name: "Scripts", path: "/scripts", selector: "h1, h2" },
  { name: "Storyboards", path: "/storyboards", selector: "h1, h2" },
];

// ── 고정 순찰 (핵심 4개) ──
test.describe("QA Patrol — Core", () => {
  test("홈 접속", async ({ page }) => {
    const errors = setupErrorCollector(page);
    await page.goto("/");
    await expect(page.getByRole("link", { name: /home/i })).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("link", { name: /studio/i })).toBeVisible();
    await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 15000 });
    await assertNoCriticalErrors(page, errors);
  });

  test("Studio 접속", async ({ page }) => {
    const errors = setupErrorCollector(page);
    await page.goto("/studio");
    await expect(
      page
        .getByText("영상 목록")
        .or(page.getByText("채널이 필요합니다"))
        .or(page.getByText("시리즈를 만들어야"))
        .first()
    ).toBeVisible({ timeout: 15000 });
    await assertNoCriticalErrors(page, errors);
  });

  test("새 영상", async ({ page }) => {
    const errors = setupErrorCollector(page);
    await page.goto("/studio?new=true");
    await expect(
      page
        .getByRole("button", { name: "채널" })
        .or(page.getByRole("button", { name: /시리즈/ }))
        .or(page.getByRole("button", { name: "Script", exact: true }))
        .first()
    ).toBeVisible({ timeout: 15000 });
    await assertNoCriticalErrors(page, errors);
  });

  test("Settings 접속", async ({ page }) => {
    const errors = setupErrorCollector(page);
    await page.goto("/settings");
    await expect(
      page
        .getByRole("link", { name: /Render Presets/i })
        .or(page.getByRole("link", { name: /YouTube/i }))
        .first()
    ).toBeVisible({ timeout: 15000 });
    await assertNoCriticalErrors(page, errors);
  });
});

// ── 확장 순찰 (Library + Scripts + Storyboards) ──
test.describe("QA Patrol — Extended", () => {
  test("Library 메인", async ({ page }) => {
    const errors = setupErrorCollector(page);
    await page.goto("/library");
    await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 15000 });
    await assertNoCriticalErrors(page, errors);
  });

  test("Characters 목록", async ({ page }) => {
    const errors = setupErrorCollector(page);
    await page.goto("/library/characters");
    await expect(page.locator("h1, h2, [data-testid]").first()).toBeVisible({ timeout: 15000 });
    await assertNoCriticalErrors(page, errors);
  });

  test("Voices 목록", async ({ page }) => {
    const errors = setupErrorCollector(page);
    await page.goto("/library/voices");
    await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 15000 });
    await assertNoCriticalErrors(page, errors);
  });

  test("Styles 목록", async ({ page }) => {
    const errors = setupErrorCollector(page);
    await page.goto("/library/styles");
    await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 15000 });
    await assertNoCriticalErrors(page, errors);
  });

  test("LoRA 목록", async ({ page }) => {
    const errors = setupErrorCollector(page);
    await page.goto("/library/loras");
    await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 15000 });
    await assertNoCriticalErrors(page, errors);
  });

  test("Scripts 페이지", async ({ page }) => {
    const errors = setupErrorCollector(page);
    await page.goto("/scripts");
    await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 15000 });
    await assertNoCriticalErrors(page, errors);
  });

  test("Storyboards 목록", async ({ page }) => {
    const errors = setupErrorCollector(page);
    await page.goto("/storyboards");
    await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 15000 });
    await assertNoCriticalErrors(page, errors);
  });
});

// ── 랜덤 순찰 (매 실행마다 다른 3페이지 선택) ──
test.describe("QA Patrol — Random", () => {
  const shuffled = [...PATROL_PAGES].sort(() => Math.random() - 0.5).slice(0, 3);

  for (const target of shuffled) {
    test(`랜덤 순찰: ${target.name} (${target.path})`, async ({ page }) => {
      const errors = setupErrorCollector(page);
      await page.goto(target.path);
      await expect(page.locator("h1, h2, button, a").first()).toBeVisible({ timeout: 15000 });
      await assertNoCriticalErrors(page, errors);
    });
  }
});

// ── Studio 탭 전환 순찰 ──
test.describe("QA Patrol — Studio Tabs", () => {
  const TABS = ["Script", "Stage", "Direct", "Publish"];

  test("Studio 탭 전환", async ({ page }) => {
    const errors = setupErrorCollector(page);
    await page.goto("/studio?new=true");

    // 에디터가 로드될 때까지 대기
    await page.waitForTimeout(3000);

    for (const tab of TABS) {
      const tabButton = page.getByRole("button", { name: tab, exact: true });
      if (await tabButton.isVisible().catch(() => false)) {
        await tabButton.click();
        await page.waitForTimeout(1000);
      }
    }

    await assertNoCriticalErrors(page, errors);
  });
});
