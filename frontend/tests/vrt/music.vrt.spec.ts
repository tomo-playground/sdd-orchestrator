import { test, expect } from "@playwright/test";
import { mockGlobalApis, mockMusicApis, mockMusicEmptyApis } from "../helpers/mockApi";
import { clearLocalStorage, hideAnimations, waitForPageReady } from "../helpers/vrtUtils";

test.describe("Music — VRT", () => {
  test("music-list", async ({ page }) => {
    await clearLocalStorage(page);
    await mockGlobalApis(page);
    await mockMusicApis(page);
    await page.goto("/music");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("music-list.png");
  });

  test("music-empty", async ({ page }) => {
    await clearLocalStorage(page);
    await mockGlobalApis(page);
    await mockMusicEmptyApis(page);
    await page.goto("/music");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("music-empty.png");
  });
});
