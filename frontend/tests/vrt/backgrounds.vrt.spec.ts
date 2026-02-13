import { test, expect } from "@playwright/test";
import { mockGlobalApis, mockBackgroundsApis, mockBackgroundsEmptyApis } from "../helpers/mockApi";
import { clearLocalStorage, hideAnimations, waitForPageReady } from "../helpers/vrtUtils";

test.describe("Backgrounds — VRT", () => {
  test("backgrounds-list", async ({ page }) => {
    await clearLocalStorage(page);
    await mockGlobalApis(page);
    await mockBackgroundsApis(page);
    await page.goto("/backgrounds");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("backgrounds-list.png");
  });

  test("backgrounds-empty", async ({ page }) => {
    await clearLocalStorage(page);
    await mockGlobalApis(page);
    await mockBackgroundsEmptyApis(page);
    await page.goto("/backgrounds");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("backgrounds-empty.png");
  });
});
