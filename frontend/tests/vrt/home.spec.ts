import { test, expect } from "@playwright/test";
import { mockGlobalApis, mockStudioApis } from "../helpers/mockApi";

test.describe("Home Page", () => {
  test.beforeEach(async ({ page }) => {
    await mockGlobalApis(page);
    await mockStudioApis(page);
    // Home page components fetch these APIs directly
    await page.route("**/style-profiles**", (route) => route.fulfill({ json: [] }));
    await page.route("**/voice-presets**", (route) =>
      route.fulfill({ json: { items: [], total: 0 } }),
    );
    await page.route("**/music-presets**", (route) =>
      route.fulfill({ json: { items: [], total: 0 } }),
    );
    await page.route("**/video/render-history**", (route) =>
      route.fulfill({ json: { items: [], total: 0 } }),
    );
    await page.goto("/");
  });

  test("initial render shows welcome bar and new story button", async ({ page }) => {
    // Welcome greeting visible
    await expect(
      page.getByRole("heading", { name: /good (morning|afternoon|evening)/i }),
    ).toBeVisible();

    // New Story button visible
    await expect(page.getByRole("button", { name: /new story/i })).toBeVisible();
  });

  test("New Story button navigates to studio", async ({ page }) => {
    await page.getByRole("button", { name: /new story/i }).click();
    await expect(page).toHaveURL(/\/studio/);
  });

  test("continue working section shows recent storyboards", async ({ page }) => {
    // Wait for the continue working section to load
    await expect(page.getByText("Continue Working")).toBeVisible({ timeout: 5000 });

    // Storyboard titles from mock data should appear
    await expect(page.getByText("Morning Routine")).toBeVisible();
  });

  test("clicking storyboard card navigates to studio", async ({ page }) => {
    await expect(page.getByText("Continue Working")).toBeVisible({ timeout: 5000 });
    await page.getByText("Morning Routine").click();
    await expect(page).toHaveURL(/\/studio\?id=1/);
  });

  test("nav links are present", async ({ page }) => {
    await expect(page.getByRole("link", { name: "Home" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Studio" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Library" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Settings" })).toBeVisible();
  });
});
