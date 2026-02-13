import { test, expect } from "@playwright/test";
import { mockGlobalApis, mockCharactersApis, mockCharactersEmptyApis } from "../helpers/mockApi";
import { clearLocalStorage, hideAnimations, waitForPageReady } from "../helpers/vrtUtils";

test.describe("Characters — VRT", () => {
  test("characters-list", async ({ page }) => {
    await clearLocalStorage(page);
    await mockGlobalApis(page);
    await mockCharactersApis(page);
    await page.goto("/characters");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("characters-list.png");
  });

  test("characters-empty", async ({ page }) => {
    await clearLocalStorage(page);
    await mockGlobalApis(page);
    await mockCharactersEmptyApis(page);
    await page.goto("/characters");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("characters-empty.png");
  });

  test("characters-new", async ({ page }) => {
    await clearLocalStorage(page);
    await mockGlobalApis(page);
    await mockCharactersApis(page);
    await page.goto("/characters/new");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("characters-new.png");
  });

  test("characters-detail", async ({ page }) => {
    await clearLocalStorage(page);
    await mockGlobalApis(page);
    await mockCharactersApis(page);
    await page.goto("/characters/1");
    await waitForPageReady(page);
    await hideAnimations(page);
    await expect(page).toHaveScreenshot("characters-detail.png");
  });
});
