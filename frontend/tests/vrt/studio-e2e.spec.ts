import { test, expect } from "@playwright/test";
import { mockStudioApis, MOCK_STORYBOARDS } from "../helpers/mockApi";

test.describe("Studio Page", () => {
  test.beforeEach(async ({ page }) => {
    await mockStudioApis(page);
  });

  // ── 1. Empty state ───────────────────────────────────────────

  test("initial empty state shows Plan tab active", async ({ page }) => {
    await page.goto("/studio");
    await expect(page.getByTestId("tab-plan")).toHaveClass(/bg-white/);
    await expect(page.getByTestId("tab-content-plan")).toBeVisible();
    await expect(page.getByTestId("storyboard-title")).toHaveText("New Storyboard");
  });

  // ── 2. Tab switching ─────────────────────────────────────────

  test("tab switching cycles through all 4 tabs", async ({ page }) => {
    await page.goto("/studio");

    // Plan → Scenes
    await page.getByTestId("tab-scenes").click();
    await expect(page.getByTestId("tab-scenes")).toHaveClass(/bg-white/);
    await expect(page.getByTestId("tab-content-scenes")).toBeVisible();

    // Scenes → Output
    await page.getByTestId("tab-output").click();
    await expect(page.getByTestId("tab-output")).toHaveClass(/bg-white/);
    await expect(page.getByTestId("tab-content-output")).toBeVisible();

    // Output → Insights
    await page.getByTestId("tab-insights").click();
    await expect(page.getByTestId("tab-insights")).toHaveClass(/bg-white/);
    await expect(page.getByTestId("tab-content-insights")).toBeVisible();

    // Insights → Plan
    await page.getByTestId("tab-plan").click();
    await expect(page.getByTestId("tab-plan")).toHaveClass(/bg-white/);
    await expect(page.getByTestId("tab-content-plan")).toBeVisible();
  });

  // ── 3. Plan: topic input + generate ──────────────────────────

  test("generate storyboard switches to Scenes tab with scene count", async ({ page }) => {
    await page.goto("/studio");

    // Fill topic
    await page.getByTestId("topic-input").fill("Travel tips for students");
    await expect(page.getByTestId("generate-btn")).toBeEnabled();

    // Click generate
    await page.getByTestId("generate-btn").click();

    // Should auto-switch to Scenes tab
    await expect(page.getByTestId("tab-scenes")).toHaveClass(/bg-white/, { timeout: 5000 });

    // Scene count badge on Scenes tab
    const scenesTab = page.getByTestId("tab-scenes");
    await expect(scenesTab).toContainText("3");
  });

  // ── 4. Scenes: empty state prompts Plan ──────────────────────

  test("empty Scenes tab shows Go to Plan button", async ({ page }) => {
    await page.goto("/studio");
    await page.getByTestId("tab-scenes").click();

    await expect(page.getByText("No scenes yet")).toBeVisible();
    const goToPlan = page.getByRole("button", { name: /Go to Plan/i });
    await expect(goToPlan).toBeVisible();

    // Click → switches to Plan tab
    await goToPlan.click();
    await expect(page.getByTestId("tab-plan")).toHaveClass(/bg-white/);
  });

  // ── 5. Scenes: keyboard navigation ───────────────────────────

  test("arrow keys navigate scenes", async ({ page }) => {
    await page.goto("/studio");

    // Generate scenes first
    await page.getByTestId("topic-input").fill("Test topic");
    await page.getByTestId("generate-btn").click();
    await expect(page.getByTestId("tab-scenes")).toHaveClass(/bg-white/, { timeout: 5000 });

    // Scene 0 should be selected initially — press ArrowRight to go to scene 1
    await page.keyboard.press("ArrowRight");
    // Press ArrowRight again → scene 2
    await page.keyboard.press("ArrowRight");
    // Press ArrowLeft → back to scene 1
    await page.keyboard.press("ArrowLeft");

    // Verify we're not on the first scene (index should be 1 now)
    // We can verify via the store state through evaluate
    const idx = await page.evaluate(() => {
      const store = JSON.parse(localStorage.getItem("shorts-producer:studio:v1") || "{}");
      return store?.state?.currentSceneIndex ?? 0;
    });
    expect(idx).toBe(1);
  });

  // ── 6. Scenes tab badge ──────────────────────────────────────

  test("Scenes tab shows count badge after generation", async ({ page }) => {
    await page.goto("/studio");
    await page.getByTestId("topic-input").fill("Test");
    await page.getByTestId("generate-btn").click();
    await expect(page.getByTestId("tab-scenes")).toHaveClass(/bg-white/, { timeout: 5000 });

    // Switch away and verify badge persists
    await page.getByTestId("tab-plan").click();
    const scenesTab = page.getByTestId("tab-scenes");
    await expect(scenesTab).toContainText("3");
  });

  // ── 7. Output tab: resource APIs called ──────────────────────

  test("Output tab loads resource APIs", async ({ page }) => {
    const apiCalls: string[] = [];
    page.on("request", (req) => {
      const url = req.url();
      if (url.includes("/audio/list") || url.includes("/fonts") || url.includes("/sd/models")) {
        apiCalls.push(url);
      }
    });

    await page.goto("/studio");
    await page.getByTestId("tab-output").click();
    await expect(page.getByTestId("tab-content-output")).toBeVisible();

    // Wait a moment for API calls to fire
    await page.waitForTimeout(500);
    expect(apiCalls.some((u) => u.includes("/audio/list"))).toBe(true);
    expect(apiCalls.some((u) => u.includes("/fonts"))).toBe(true);
    expect(apiCalls.some((u) => u.includes("/sd/models"))).toBe(true);
  });

  // ── 8. Insights tab ─────────────────────────────────────────

  test("Insights tab shows dashboard headings", async ({ page }) => {
    await page.goto("/studio");
    await page.getByTestId("tab-insights").click();
    await expect(page.getByTestId("tab-content-insights")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Quality Dashboard" }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Analytics" }).first()).toBeVisible();
  });

  // ── 9. DB load via ?id=X ─────────────────────────────────────

  test("loads storyboard from DB when ?id is set", async ({ page }) => {
    await page.goto("/studio?id=1");

    // Title should match loaded storyboard
    await expect(page.getByTestId("storyboard-title")).toHaveText("Morning Routine", { timeout: 5000 });

    // Scenes tab should be active (has scenes)
    await expect(page.getByTestId("tab-scenes")).toHaveClass(/bg-white/);

    // Scene count displayed in header
    const sb = MOCK_STORYBOARDS[0];
    await expect(page.getByText(`${sb.scenes.length} scenes`)).toBeVisible();
  });

  // ── 10. Escape key clears preview ────────────────────────────

  test("Escape key clears image preview", async ({ page }) => {
    await page.goto("/studio");

    // Set imagePreviewSrc via store
    await page.evaluate(() => {
      const raw = localStorage.getItem("shorts-producer:studio:v1");
      if (raw) {
        const data = JSON.parse(raw);
        if (data.state) data.state.imagePreviewSrc = "http://example.com/test.png";
        localStorage.setItem("shorts-producer:studio:v1", JSON.stringify(data));
      }
    });

    // Press Escape
    await page.keyboard.press("Escape");

    // Verify cleared
    const preview = await page.evaluate(() => {
      const raw = localStorage.getItem("shorts-producer:studio:v1");
      if (raw) {
        const data = JSON.parse(raw);
        return data?.state?.imagePreviewSrc ?? null;
      }
      return null;
    });
    expect(preview).toBeNull();
  });
});

// ── Home button ─────────────────────────────────────────────────

test("Home button navigates back to /", async ({ page }) => {
  await mockStudioApis(page);
  await page.goto("/studio");
  await page.getByTestId("studio-home-btn").click();
  await expect(page).toHaveURL(/\/$/);
});
