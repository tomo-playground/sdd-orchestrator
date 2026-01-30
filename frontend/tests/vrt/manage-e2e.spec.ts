import { test, expect } from "@playwright/test";
import { mockStudioApis } from "../helpers/mockApi";

test.describe("Manage Page", () => {
  test.beforeEach(async ({ page }) => {
    await mockStudioApis(page);
    // Mock manage-specific APIs
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
    await page.goto("/manage");
  });

  test("initial render shows Tags tab active", async ({ page }) => {
    // Default tab is "tags"
    const tagsBtn = page.getByRole("button", { name: "Tags" });
    await expect(tagsBtn).toHaveClass(/bg-zinc-900/);
  });

  test("all 6 tabs switch correctly", async ({ page }) => {
    const tabs = ["Assets", "Style", "Tags", "Prompts", "Eval", "Settings"];

    for (const label of tabs) {
      const btn = page.getByRole("button", { name: label, exact: true });
      await btn.click();
      await expect(btn).toHaveClass(/bg-zinc-900/);
    }
  });

  test("Home link navigates to /", async ({ page }) => {
    await page.getByRole("link", { name: "Home" }).click();
    await expect(page).toHaveURL(/\/$/);
  });
});
