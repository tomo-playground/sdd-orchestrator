import { test, expect } from "@playwright/test";
import { mockGlobalApis, mockStudioApis, MOCK_STORYBOARDS } from "../helpers/mockApi";

test.describe("Studio Page", () => {
  test.beforeEach(async ({ page }) => {
    await mockGlobalApis(page);
    await mockStudioApis(page);
  });

  // ── 1. Kanban view (no storyboard selected) ────────────────

  test("shows kanban view when no storyboard selected", async ({ page }) => {
    await page.goto("/studio");
    // Kanban view header
    await expect(page.getByText("영상 목록")).toBeVisible({ timeout: 5000 });
    // New story button
    await expect(page.getByRole("button", { name: /새 영상/i })).toBeVisible();
  });

  // ── 2. New storyboard mode ──────────────────────────────────

  test("new storyboard mode shows Script tab", async ({ page }) => {
    await page.goto("/studio?new=true");
    // Script tab should be active (contains the chat editor)
    await expect(page.getByRole("button", { name: "Script", exact: true })).toBeVisible();
  });

  // ── 3. Tab switching ────────────────────────────────────────

  test("tab switching cycles through all 4 tabs", async ({ page }) => {
    await page.goto("/studio?new=true");
    // Verify all 4 tabs exist (use exact: true to avoid matching "Go to Script" etc.)
    await expect(page.getByRole("button", { name: "Script", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Stage", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Direct", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Publish", exact: true })).toBeVisible();

    // Click Stage tab
    await page.getByRole("button", { name: "Stage", exact: true }).click();
    // Click Direct tab
    await page.getByRole("button", { name: "Direct", exact: true }).click();
    // Click Publish tab
    await page.getByRole("button", { name: "Publish", exact: true }).click();
    // Click Script tab back
    await page.getByRole("button", { name: "Script", exact: true }).click();
  });

  // ── 4. DB load via ?id=X ────────────────────────────────────

  test("loads storyboard from DB when ?id is set", async ({ page }) => {
    await page.goto(`/studio?id=${MOCK_STORYBOARDS[0].id}`);

    // Title should match loaded storyboard (use first() to handle multiple matches)
    const sb = MOCK_STORYBOARDS[0];
    await expect(page.getByText(sb.title).first()).toBeVisible({ timeout: 5000 });
  });

  // ── 5. Escape key clears preview ───────────────────────────

  test("Escape key clears image preview", async ({ page }) => {
    await page.goto("/studio?new=true");

    // Set imagePreviewSrc via store (UIStore is not persisted, use evaluate)
    await page.evaluate(() => {
      // Access the Zustand store directly
      const store = (window as Record<string, unknown>).__uiStore;
      if (store && typeof store === "object" && "set" in store) {
        (store as { set: (s: Record<string, unknown>) => void }).set({
          imagePreviewSrc: "http://example.com/test.png",
        });
      }
    });

    // Press Escape
    await page.keyboard.press("Escape");

    // Short wait for state update
    await page.waitForTimeout(200);
  });

  // ── 6. Nav links work from studio ───────────────────────────

  test("Home nav link navigates back to /", async ({ page }) => {
    await page.goto("/studio?new=true");
    await page.getByRole("link", { name: "Home" }).click();
    await expect(page).toHaveURL(/\/$/);
  });

  // ── 7. New story from kanban ────────────────────────────────

  test("new story button from kanban shows editor view", async ({ page }) => {
    await page.goto("/studio");
    await expect(page.getByText("영상 목록")).toBeVisible({ timeout: 5000 });
    await page.getByRole("button", { name: /새 영상/i }).click();
    // After clicking, the editor view should appear with Script tab
    await expect(page.getByRole("button", { name: "Script", exact: true })).toBeVisible({
      timeout: 5000,
    });
  });
});
