import { test, expect } from "@playwright/test";
import { mockGlobalApis, mockStudioApis } from "../helpers/mockApi";

test.describe("Home Page", () => {
  test.beforeEach(async ({ page }) => {
    await mockGlobalApis(page);
    await mockStudioApis(page);
    // Home page components fetch these APIs directly
    await page.route("**/style-profiles**", (route) => route.fulfill({ json: [] }));
    await page.route("**/voice-presets**", (route) =>
      route.fulfill({ json: { items: [], total: 0 } })
    );
    await page.route("**/music-presets**", (route) =>
      route.fulfill({ json: { items: [], total: 0 } })
    );
    await page.route("**/video/render-history**", (route) =>
      route.fulfill({ json: { items: [], total: 0 } })
    );
    await page.goto("/");
  });

  test("initial render shows welcome bar and new story button", async ({ page }) => {
    // Welcome greeting visible
    await expect(
      page.getByRole("heading", { name: /good (morning|afternoon|evening)/i })
    ).toBeVisible();

    // 새 영상 button visible
    await expect(page.getByRole("button", { name: /새 영상/i })).toBeVisible();
  });

  test("새 영상 button navigates to studio", async ({ page }) => {
    await page.getByRole("button", { name: /새 영상/i }).click();
    await expect(page).toHaveURL(/\/studio/);
  });

  test("continue working section shows recent storyboards", async ({ page }) => {
    // Wait for the continue working section to load
    await expect(page.getByText("이어서 작업")).toBeVisible({ timeout: 5000 });

    // Storyboard titles from mock data should appear
    await expect(page.getByText("Morning Routine")).toBeVisible();
  });

  test("clicking storyboard card navigates to studio", async ({ page }) => {
    await expect(page.getByText("이어서 작업")).toBeVisible({ timeout: 5000 });
    await page.getByText("Morning Routine").click();
    await expect(page).toHaveURL(/\/studio\?id=1/);
  });

  test("nav links are present", async ({ page }) => {
    await expect(page.getByRole("link", { name: "홈" })).toBeVisible();
    await expect(page.getByRole("link", { name: "스튜디오" })).toBeVisible();
    await expect(page.getByRole("link", { name: "라이브러리" })).toBeVisible();
    await expect(page.getByRole("link", { name: "설정" })).toBeVisible();
  });
});
