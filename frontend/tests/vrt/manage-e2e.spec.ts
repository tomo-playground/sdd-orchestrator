import { test, expect } from "@playwright/test";
import { mockGlobalApis, mockStudioApis } from "../helpers/mockApi";

test.describe("Admin Page", () => {
  test.beforeEach(async ({ page }) => {
    await mockGlobalApis(page);
    await mockStudioApis(page);
  });

  test("admin renders characters page", async ({ page }) => {
    await page.goto("/library/characters");
    await expect(page.getByRole("heading", { name: /characters/i })).toBeVisible({ timeout: 5000 });
  });

  test("Home link navigates to /", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/$/);
  });
});
