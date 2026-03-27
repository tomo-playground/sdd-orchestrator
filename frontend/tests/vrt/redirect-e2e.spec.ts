import { test, expect } from "@playwright/test";
import { mockGlobalApis, mockStudioApis } from "../helpers/mockApi";

test.describe("Ghost route redirects", () => {
  test.beforeEach(async ({ page }) => {
    await mockGlobalApis(page);
    await mockStudioApis(page);
  });

  test("/scripts redirects to /studio", async ({ page }) => {
    await page.goto("/scripts");
    await expect(page).toHaveURL(/\/studio$/);
  });

  test("/scripts?id=1 redirects to /studio?id=1", async ({ page }) => {
    await page.goto("/scripts?id=1");
    await expect(page).toHaveURL(/\/studio\?id=1/);
  });

  test("/scripts?new=true redirects to /studio?new=true", async ({ page }) => {
    await page.goto("/scripts?new=true");
    await expect(page).toHaveURL(/\/studio\?new=true/);
  });

  test("/storyboards redirects to /", async ({ page }) => {
    await page.goto("/storyboards");
    await expect(page).toHaveURL("/");
  });
});

test.describe("Ghost route server-level 301 assertions", () => {
  test("/scripts returns 301 to /studio", async ({ page }) => {
    const res = await page.request.get("/scripts", { maxRedirects: 0 });
    expect(res.status()).toBe(301);
    expect(res.headers()["location"]).toContain("/studio");
  });

  test("/scripts?id=1 returns 301 with query forwarded", async ({ page }) => {
    const res = await page.request.get("/scripts?id=1", { maxRedirects: 0 });
    expect(res.status()).toBe(301);
    expect(res.headers()["location"]).toContain("/studio?id=1");
  });

  test("/storyboards returns 301 to /", async ({ page }) => {
    const res = await page.request.get("/storyboards", { maxRedirects: 0 });
    expect(res.status()).toBe(301);
    expect(res.headers()["location"]).toMatch(/^(https?:\/\/[^/]+)?\/$/);
  });
});
