import { test, expect } from "@playwright/test";
import { mockGlobalApis, mockStudioApis, MOCK_STORYBOARDS } from "../helpers/mockApi";
import { clearLocalStorage, hideAnimations, waitForPageReady } from "../helpers/vrtUtils";

test.describe("Studio — VRT", () => {
  test.beforeEach(async ({ page }) => {
    await clearLocalStorage(page);
    await mockGlobalApis(page);
    await mockStudioApis(page);
  });

  test("studio-empty", async ({ page }) => {
    await page.goto("/studio");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("studio-empty.png");
  });

  test("studio-with-scenes", async ({ page }) => {
    await page.goto(`/studio?id=${MOCK_STORYBOARDS[0].id}`);
    await waitForPageReady(page);
    // Extra wait for async data loading (chat editor, storyboard data)
    await page.waitForTimeout(1000);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("studio-with-scenes.png", { maxDiffPixels: 5000 });
  });
});
