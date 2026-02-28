import { test, expect } from "@playwright/test";
import { mockGlobalApis, mockLabApis } from "../helpers/mockApi";
import { clearLocalStorage, hideAnimations, waitForPageReady } from "../helpers/vrtUtils";

test.describe("Lab — VRT", () => {
  test.beforeEach(async ({ page }) => {
    await clearLocalStorage(page);
    await mockGlobalApis(page);
    await mockLabApis(page);
  });

  test("lab-tag-lab", async ({ page }) => {
    await page.goto("/dev/lab?tab=tag-lab");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("lab-tag-lab.png");
  });

  test("lab-scene-lab", async ({ page }) => {
    await page.goto("/dev/lab?tab=scene-lab");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("lab-scene-lab.png");
  });

  test("lab-analytics", async ({ page }) => {
    await page.goto("/dev/lab?tab=analytics");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("lab-analytics.png");
  });
});
