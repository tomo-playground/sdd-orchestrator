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

  // 콘솔 에러 수집
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      const text = msg.text();
      // React 개발 모드 경고 제외
      if (text.includes("Warning:") || text.includes("DevTools")) return;
      errors.push({ type: "console", message: redactMessage(text), url: redactUrl(page.url()) });
    }
  });

  // JS 예외 수집
  page.on("pageerror", (err) => {
    errors.push({
      type: "console",
      message: redactMessage(`Uncaught: ${err.message}`),
      url: redactUrl(page.url()),
    });
  });

  // API 4xx/5xx 수집
  page.on("response", (response) => {
    const status = response.status();
    const url = response.url();
    // API 응답만 감시 (정적 리소스 제외)
    if (status >= 400 && url.includes("/api/")) {
      const safeUrl = redactUrl(url);
      errors.push({ type: "api", message: `${status} ${safeUrl}`, status, url: safeUrl });
    }
  });

  return errors;
}

/** networkidle 대기 후 치명적 에러 assertion — 늦게 도착하는 API 5xx 누락 방지 */
async function assertNoCriticalErrors(page: Page, errors: PatrolError[]) {
  await Promise.race([page.waitForLoadState("networkidle"), page.waitForTimeout(2000)]);
  const critical = errors.filter(
    (e) => e.type === "console" || (e.type === "api" && (e.status ?? 0) >= 500)
  );
  expect(critical, `Critical errors: ${JSON.stringify(critical)}`).toHaveLength(0);
}

test.describe("QA Patrol", () => {
  test("홈 접속 — 페이지 로드 확인", async ({ page }) => {
    const errors = setupErrorCollector(page);

    await page.goto("/");
    await expect(page.getByRole("link", { name: /home/i })).toBeVisible({
      timeout: 15000,
    });
    await expect(page.getByRole("link", { name: /studio/i })).toBeVisible();

    // 메인 콘텐츠 렌더링 확인
    await expect(page.locator("h1, h2").first()).toBeVisible({
      timeout: 15000,
    });

    // 치명적 에러가 없어야 함 (API 404는 허용)
    await assertNoCriticalErrors(page, errors);
  });

  test("Studio 접속 — 칸반 보드 로드 확인", async ({ page }) => {
    const errors = setupErrorCollector(page);

    await page.goto("/studio");
    // 칸반 뷰 또는 채널/시리즈 필요 안내
    await expect(
      page
        .getByText("영상 목록")
        .or(page.getByText("채널이 필요합니다"))
        .or(page.getByText("시리즈를 만들어야"))
        .first()
    ).toBeVisible({ timeout: 15000 });

    await assertNoCriticalErrors(page, errors);
  });

  test("새 영상 — 에디터 로드 확인", async ({ page }) => {
    const errors = setupErrorCollector(page);

    await page.goto("/studio?new=true");

    // Studio UI — 채널/시리즈 선택 또는 에디터 탭
    await expect(
      page
        .getByRole("button", { name: "채널" })
        .or(page.getByRole("button", { name: /시리즈/ }))
        .or(page.getByRole("button", { name: "Script", exact: true }))
        .first()
    ).toBeVisible({ timeout: 15000 });

    await assertNoCriticalErrors(page, errors);
  });

  test("Settings 접속 — 페이지 로드 확인", async ({ page }) => {
    const errors = setupErrorCollector(page);

    await page.goto("/settings");
    // Settings 서브 네비게이션
    await expect(
      page
        .getByRole("link", { name: /Render Presets/i })
        .or(page.getByRole("link", { name: /YouTube/i }))
        .first()
    ).toBeVisible({ timeout: 15000 });

    await assertNoCriticalErrors(page, errors);
  });
});
