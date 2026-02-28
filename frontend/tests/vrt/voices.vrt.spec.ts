import { test, expect } from "@playwright/test";
import { mockGlobalApis, mockVoicesApis, mockVoicesEmptyApis } from "../helpers/mockApi";
import { clearLocalStorage, hideAnimations, waitForPageReady } from "../helpers/vrtUtils";

test.describe("Voices — VRT", () => {
  test("voices-list", async ({ page }) => {
    await clearLocalStorage(page);
    await mockGlobalApis(page);
    await mockVoicesApis(page);
    await page.goto("/admin/voices");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("voices-list.png");
  });

  test("voices-empty", async ({ page }) => {
    await clearLocalStorage(page);
    await mockGlobalApis(page);
    await mockVoicesEmptyApis(page);
    await page.goto("/admin/voices");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("voices-empty.png");
  });
});
