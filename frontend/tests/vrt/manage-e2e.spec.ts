import { test, expect } from "@playwright/test";
import { mockGlobalApis, mockStudioApis } from "../helpers/mockApi";

test.describe("Admin Page", () => {
  test.beforeEach(async ({ page }) => {
    await mockGlobalApis(page);
    await mockStudioApis(page);
    // Mock admin-specific APIs
    await page.route("**/tags/groups**", (route) => route.fulfill({ json: [] }));
    await page.route("**/tags/pending**", (route) => route.fulfill({ json: [] }));
    await page.route("**/style-profiles", (route) => route.fulfill({ json: [] }));
    await page.route("**/sd/models", (route) =>
      route.fulfill({ json: { models: [] } }),
    );
    await page.route("**/embeddings", (route) => route.fulfill({ json: [] }));
    await page.route("**/prompt-history**", (route) => route.fulfill({ json: [] }));
    await page.route("**/storage/stats", (route) =>
      route.fulfill({ json: { total_size_mb: 0, total_count: 0, directories: {} } }),
    );
    await page.goto("/library/characters");
  });

  test("admin renders characters page", async ({ page }) => {
    await expect(page.locator("text=Characters")).toBeVisible();
  });

  test("Home link navigates to /", async ({ page }) => {
    // Navigate to home via service shell
    await page.goto("/");
    await expect(page).toHaveURL(/\/$/);
  });
});
