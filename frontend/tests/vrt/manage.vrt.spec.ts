import { test, expect } from "@playwright/test";
import { mockGlobalApis, mockManageApis } from "../helpers/mockApi";
import { clearLocalStorage, hideAnimations, waitForPageReady } from "../helpers/vrtUtils";

test.describe("Admin — VRT", () => {
  test.beforeEach(async ({ page }) => {
    await clearLocalStorage(page);
    await mockGlobalApis(page);
    await mockManageApis(page);
  });

  test("admin-tags", async ({ page }) => {
    await page.goto("/admin/tags");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("manage-tags.png");
  });

  test("admin-styles", async ({ page }) => {
    await page.goto("/admin/styles");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("manage-style.png");
  });

  test("admin-prompts", async ({ page }) => {
    await page.goto("/admin/prompts");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("manage-prompts.png");
  });

  test("admin-system-presets", async ({ page }) => {
    await page.goto("/admin/system?tab=presets");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("manage-presets.png");
  });

  test("admin-system-youtube", async ({ page }) => {
    await page.goto("/admin/system?tab=youtube");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("manage-youtube.png");
  });

  test("admin-system-general", async ({ page }) => {
    await page.goto("/admin/system?tab=general");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("manage-settings.png");
  });

  test("admin-system-trash", async ({ page }) => {
    await page.goto("/admin/system?tab=trash");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("manage-trash.png");
  });
});
