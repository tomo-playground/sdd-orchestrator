import { test, expect } from "@playwright/test";
import { mockStudioApis } from "../helpers/mockApi";

test.describe("Home Page", () => {
  test.beforeEach(async ({ page }) => {
    await mockStudioApis(page);
    await page.goto("/");
  });

  test("initial render shows Storyboards tab active with list", async ({ page }) => {
    // Storyboards tab is active by default
    const sbTab = page.getByTestId("home-tab-storyboards");
    await expect(sbTab).toHaveClass(/bg-white/);

    // Storyboard cards rendered
    await expect(page.getByTestId("storyboard-card-1")).toBeVisible();
    await expect(page.getByTestId("storyboard-card-2")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Morning Routine" })).toBeVisible();
  });

  test("New Storyboard navigates to /studio with Plan tab", async ({ page }) => {
    await page.getByTestId("new-storyboard-btn").click();
    await expect(page).toHaveURL(/\/studio$/);
    // Plan tab should be default active
    await expect(page.getByTestId("tab-plan")).toHaveClass(/bg-white/);
  });

  test("clicking storyboard card navigates to /studio?id=1", async ({ page }) => {
    await page.getByTestId("storyboard-card-1").click();
    await expect(page).toHaveURL(/\/studio\?id=1/);
    // With scenes → Scenes tab active
    await expect(page.getByTestId("tab-scenes")).toHaveClass(/bg-white/);
  });

  test("Characters tab shows character grid", async ({ page }) => {
    await page.getByTestId("home-tab-characters").click();
    await expect(page.getByText("Hana")).toBeVisible();
    await expect(page.getByText("Characters (1)")).toBeVisible();
  });

  test("Manage button navigates to /manage", async ({ page }) => {
    await page.getByTestId("manage-link").click();
    await expect(page).toHaveURL(/\/manage/);
    await expect(page.getByRole("heading", { name: "Manage" })).toBeVisible();
  });
});
