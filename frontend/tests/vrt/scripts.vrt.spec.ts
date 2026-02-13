import { test, expect } from "@playwright/test";
import { mockGlobalApis, mockScriptsApis, mockScriptsEmptyApis } from "../helpers/mockApi";
import { clearLocalStorage, hideAnimations, waitForPageReady } from "../helpers/vrtUtils";

test.describe("Scripts — VRT", () => {
  test("scripts-list", async ({ page }) => {
    await clearLocalStorage(page);
    await mockGlobalApis(page);
    await mockScriptsApis(page);
    await page.goto("/scripts");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("scripts-list.png");
  });

  test("scripts-empty", async ({ page }) => {
    await clearLocalStorage(page);
    await mockGlobalApis(page);
    await mockScriptsEmptyApis(page);
    await page.goto("/scripts");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("scripts-empty.png");
  });
});
