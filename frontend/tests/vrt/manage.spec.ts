import { test, expect } from "@playwright/test";

test.describe("Manage Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/manage");
    await page.waitForLoadState("networkidle");
  });

  test("initial state", async ({ page }) => {
    await expect(page).toHaveScreenshot("manage-initial.png", {
      fullPage: true,
    });
  });

  test("tabs navigation", async ({ page }) => {
    const tabs = page.locator('[role="tablist"]').first();
    if (await tabs.isVisible()) {
      await expect(tabs).toHaveScreenshot("manage-tabs.png");
    }
  });

  test("characters tab", async ({ page }) => {
    const charactersTab = page.getByRole("tab", { name: /character/i });
    if (await charactersTab.isVisible()) {
      await charactersTab.click();
      await page.waitForTimeout(500);
      await expect(page).toHaveScreenshot("manage-characters.png", {
        fullPage: true,
      });
    }
  });

  test("loras tab", async ({ page }) => {
    const lorasTab = page.getByRole("tab", { name: /lora/i });
    if (await lorasTab.isVisible()) {
      await lorasTab.click();
      await page.waitForTimeout(500);
      await expect(page).toHaveScreenshot("manage-loras.png", {
        fullPage: true,
      });
    }
  });

  test("tags tab", async ({ page }) => {
    const tagsTab = page.getByRole("tab", { name: /tag/i });
    if (await tagsTab.isVisible()) {
      await tagsTab.click();
      await page.waitForTimeout(500);
      await expect(page).toHaveScreenshot("manage-tags.png", {
        fullPage: true,
      });
    }
  });
});
