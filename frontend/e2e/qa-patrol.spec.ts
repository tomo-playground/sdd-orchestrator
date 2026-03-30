import { test, expect, type Page } from "@playwright/test";
import {
  PATROL_TIMEOUT,
  PATROL_PAGES,
  CORE_CHECKS,
  EXTENDED_CHECKS,
  STUDIO_TABS,
} from "./qa-patrol.config";

/**
 * QA Patrol — 핵심 플로우 자동 순찰
 *
 * 순찰 대상 변경 시 qa-patrol.config.ts만 수정.
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
    (e) =>
      (e.type === "console" && !e.message.includes("Failed to load resource")) ||
      (e.type === "api" && (e.status ?? 0) >= 500)
  );
  expect(critical, `Critical errors: ${JSON.stringify(critical)}`).toHaveLength(0);
}

// ── Core 순찰 (핵심 4개) ──
test.describe("QA Patrol — Core", () => {
  test("홈 접속", async ({ page }) => {
    const errors = setupErrorCollector(page);
    const cfg = CORE_CHECKS.home;
    await page.goto(cfg.path);
    for (const pattern of cfg.navLinks) {
      await expect(page.getByRole("link", { name: pattern })).toBeVisible({
        timeout: PATROL_TIMEOUT,
      });
    }
    await expect(page.locator(cfg.contentSelector).first()).toBeVisible({
      timeout: PATROL_TIMEOUT,
    });
    await assertNoCriticalErrors(page, errors);
  });

  test("Studio 접속", async ({ page }) => {
    const errors = setupErrorCollector(page);
    const cfg = CORE_CHECKS.studio;
    await page.goto(cfg.path);
    let locator = page.getByText(cfg.contentTexts[0]);
    for (const text of cfg.contentTexts.slice(1)) {
      locator = locator.or(page.getByText(text));
    }
    await expect(locator.first()).toBeVisible({ timeout: PATROL_TIMEOUT });
    await assertNoCriticalErrors(page, errors);
  });

  test("새 영상", async ({ page }) => {
    const errors = setupErrorCollector(page);
    const cfg = CORE_CHECKS.newVideo;
    await page.goto(cfg.path);
    let locator = page.getByRole("button", {
      name: cfg.buttons[0].name,
      exact: cfg.buttons[0].exact,
    });
    for (const btn of cfg.buttons.slice(1)) {
      locator = locator.or(page.getByRole("button", { name: btn.name, exact: btn.exact }));
    }
    await expect(locator.first()).toBeVisible({ timeout: PATROL_TIMEOUT });
    await assertNoCriticalErrors(page, errors);
  });

  test("Settings 접속", async ({ page }) => {
    const errors = setupErrorCollector(page);
    const cfg = CORE_CHECKS.settings;
    await page.goto(cfg.path);
    let locator = page.getByRole("link", { name: cfg.links[0] });
    for (const link of cfg.links.slice(1)) {
      locator = locator.or(page.getByRole("link", { name: link }));
    }
    await expect(locator.first()).toBeVisible({ timeout: PATROL_TIMEOUT });
    await assertNoCriticalErrors(page, errors);
  });
});

// ── Extended 순찰 (config 기반 자동 생성) ──
test.describe("QA Patrol — Extended", () => {
  for (const check of EXTENDED_CHECKS) {
    test(check.name, async ({ page }) => {
      const errors = setupErrorCollector(page);
      await page.goto(check.path);
      let locator = page.locator(check.selector).first();
      if (check.fallbackTexts) {
        for (const text of check.fallbackTexts) {
          locator = locator.or(page.getByText(text));
        }
      }
      await expect(locator).toBeVisible({ timeout: PATROL_TIMEOUT });
      await assertNoCriticalErrors(page, errors);
    });
  }
});

// ── 랜덤 순찰 (날짜 기반 결정론적 선택 — worker 간 동일 제목 보장) ──
test.describe("QA Patrol — Random", () => {
  const daySeed = new Date().toISOString().slice(0, 10);
  const hash = [...daySeed].reduce((acc, c) => acc + c.charCodeAt(0), 0);
  const picked = Array.from(
    { length: 3 },
    (_, i) => PATROL_PAGES[(hash + i * 7) % PATROL_PAGES.length]
  );

  for (const target of picked) {
    test(`랜덤 순찰: ${target.name} (${target.path})`, async ({ page }) => {
      const errors = setupErrorCollector(page);
      await page.goto(target.path);
      await expect(page.locator("h1, h2, button, a").first()).toBeVisible({
        timeout: PATROL_TIMEOUT,
      });
      await assertNoCriticalErrors(page, errors);
    });
  }
});

// ── Studio 탭 전환 순찰 ──
test.describe("QA Patrol — Studio Tabs", () => {
  test("Studio 탭 전환", async ({ page }) => {
    const errors = setupErrorCollector(page);
    await page.goto("/studio?new=true");
    await page.waitForTimeout(3000);

    for (const tab of STUDIO_TABS) {
      const tabButton = page.getByRole("button", { name: tab, exact: true });
      if (await tabButton.isVisible().catch(() => false)) {
        await tabButton.click();
        await page.waitForTimeout(1000);
      }
    }

    await assertNoCriticalErrors(page, errors);
  });
});
