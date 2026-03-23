import { test, expect } from "@playwright/test";

/**
 * N+1 API Call 회귀 테스트 — Sentry #146
 *
 * 캐릭터 페이지 진입 시 /api/v1/tags 호출이 1회인지 검증.
 * (수정 전: WIZARD_CATEGORIES 30개 × 개별 호출 = 30회)
 */
test.describe("N+1 Tag Fetch Regression", () => {
  test("캐릭터 빌더 — /tags 호출이 정확히 1회", async ({ page }) => {
    const tagRequests: string[] = [];

    page.on("request", (req) => {
      const url = req.url();
      if (url.includes("/api/") && url.includes("/tags") && !url.includes("/tags/search")) {
        tagRequests.push(url);
      }
    });

    await page.goto("/library/characters/new");

    // 페이지 로드 대기 (태그 데이터 fetch 완료까지)
    await page.waitForLoadState("networkidle");

    // /tags/search 제외 → 배치 호출 1회만 카운트. 수정 전이면 30회 이상 발생.
    expect(
      tagRequests.length,
      `Expected 1 /tags call, got ${tagRequests.length}: ${tagRequests.join("\n")}`
    ).toBe(1);
  });
});
