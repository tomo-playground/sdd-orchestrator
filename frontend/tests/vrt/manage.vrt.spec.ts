import { test, expect } from "@playwright/test";
import { mockGlobalApis, mockManageApis } from "../helpers/mockApi";
import { clearLocalStorage, hideAnimations, waitForPageReady } from "../helpers/vrtUtils";

test.describe("Manage — VRT", () => {
  test.beforeEach(async ({ page }) => {
    await clearLocalStorage(page);
    await mockGlobalApis(page);
    await mockManageApis(page);
  });

  test("manage-tags", async ({ page }) => {
    await page.goto("/manage?tab=tags");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("manage-tags.png");
  });

  test("manage-style", async ({ page }) => {
    await page.goto("/manage?tab=style");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("manage-style.png");
  });

  test("manage-prompts", async ({ page }) => {
    await page.goto("/manage?tab=prompts");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("manage-prompts.png");
  });

  test("manage-presets", async ({ page }) => {
    await page.goto("/manage?tab=presets");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("manage-presets.png");
  });

  test("manage-youtube", async ({ page }) => {
    await page.goto("/manage?tab=youtube");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("manage-youtube.png");
  });

  test("manage-settings", async ({ page }) => {
    await page.goto("/manage?tab=settings");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("manage-settings.png");
  });

  test("manage-trash", async ({ page }) => {
    await page.goto("/manage?tab=trash");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("manage-trash.png");
  });
});
