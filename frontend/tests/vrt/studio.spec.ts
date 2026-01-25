import { test, expect } from "@playwright/test";

test.describe("Studio Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // Wait for page to be fully loaded
    await page.waitForLoadState("networkidle");
  });

  test("initial state", async ({ page }) => {
    await expect(page).toHaveScreenshot("studio-initial.png", {
      fullPage: true,
    });
  });

  test("preset selection area", async ({ page }) => {
    const presetSection = page.locator('[data-testid="preset-section"]').first();
    if (await presetSection.isVisible()) {
      await expect(presetSection).toHaveScreenshot("preset-section.png");
    }
  });

  test("scene list area", async ({ page }) => {
    const sceneList = page.locator('[data-testid="scene-list"]').first();
    if (await sceneList.isVisible()) {
      await expect(sceneList).toHaveScreenshot("scene-list-empty.png");
    }
  });

  test("render settings panel", async ({ page }) => {
    const renderPanel = page.locator('[data-testid="render-settings"]').first();
    if (await renderPanel.isVisible()) {
      await expect(renderPanel).toHaveScreenshot("render-settings.png");
    }
  });
});
