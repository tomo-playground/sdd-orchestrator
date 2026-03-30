import { test, expect } from "@playwright/test";

test.describe("Smoke Tests", () => {
  test("Home page loads with navigation", async ({ page }) => {
    await page.goto("/");

    // Global navigation links should be visible
    await expect(page.getByRole("link", { name: /홈/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /스튜디오/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /라이브러리/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /설정/i })).toBeVisible();

    // Page content should render (heading or main content area)
    await expect(page.locator("h1, h2").first()).toBeVisible({
      timeout: 15000,
    });
  });

  test("Studio page loads and tab switching works", async ({ page }) => {
    await page.goto("/studio?new=true");

    // Wait for either editor tabs, kanban view, or series selection screen (depends on DB state)
    const scriptTab = page.getByRole("button", {
      name: "대본",
      exact: true,
    });
    const kanbanHeading = page.getByText("영상 목록");
    const needsChannel = page.getByText("채널이 필요합니다");
    const needsSeries = page.getByText("시리즈를 만들어야");
    const groupButton = page.getByRole("button", { name: "시리즈 설정" });
    const seriesPrompt = page.getByText("시작하려면 시리즈를 생성하세요");

    await expect(
      scriptTab
        .or(kanbanHeading)
        .or(needsChannel)
        .or(needsSeries)
        .or(groupButton)
        .or(seriesPrompt)
        .first()
    ).toBeVisible({
      timeout: 15000,
    });

    // If editor tabs are visible, verify all 4 tabs and test switching
    if (await scriptTab.isVisible()) {
      await expect(page.getByRole("button", { name: "준비", exact: true })).toBeVisible();
      await expect(page.getByRole("button", { name: "이미지", exact: true })).toBeVisible();
      await expect(page.getByRole("button", { name: "게시", exact: true })).toBeVisible();

      // Switch to Stage tab — no crash = success
      await page.getByRole("button", { name: "준비", exact: true }).click();
    }
  });

  test("Storyboard list page loads", async ({ page }) => {
    await page.goto("/studio");

    // Should show kanban view with storyboard list or empty state
    await expect(
      page
        .getByText("영상 목록")
        .or(page.getByText("채널이 필요합니다"))
        .or(page.getByText("시리즈를 만들어야"))
        .first()
    ).toBeVisible({ timeout: 15000 });

    // Navigation should remain functional
    await expect(page.getByRole("link", { name: /스튜디오/i })).toBeVisible();
  });
});
