import { test, expect, type Page } from "@playwright/test";
import { mockGlobalApis, mockStudioApis } from "../helpers/mockApi";

// ── SSE mock helpers ────────────────────────────────────────────

/** Build a minimal SSE body with finalize completion event. */
function buildSSEBody(options: { warnings?: string[] }): string {
  const scenes = [
    {
      script: "테스트 씬",
      speaker: "speaker_1",
      duration: 3,
      image_prompt: "1girl, standing",
      image_prompt_ko: "서있는 소녀",
    },
  ];

  const events = [
    { node: "writer", label: "작성 중", percent: 50, status: "running" },
    {
      node: "finalize",
      label: "완료",
      percent: 100,
      status: "completed",
      result: {
        scenes,
        character_id: 1,
        structure: "monologue",
        ...(options.warnings?.length ? { warnings: options.warnings } : {}),
      },
    },
  ];

  return events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("");
}

const MOCK_RECOMMENDATION = {
  status: "recommend",
  resolved_topic: "테스트 주제",
  reasoning: "30초 독백으로 제작합니다.",
  duration: 30,
  language: "korean",
  structure: "monologue",
  available_options: {
    durations: [15, 30, 60],
    languages: [{ value: "korean", label: "한국어" }],
  },
};

/** Mock pipeline APIs needed for chat → analyze → generate flow. */
async function mockPipelineApis(page: Page) {
  await page.route("**/scripts/analyze-topic", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({ json: MOCK_RECOMMENDATION });
    }
    return route.continue();
  });

  await page.route("**/groups/*/effective-config", (route) =>
    route.fulfill({
      json: { style_profile_id: 1, render_preset: null, sources: {} },
    })
  );

  await page.route("**/video-meta**", (route) => route.fulfill({ json: {} }));
  await page.route("**/style-profiles/*", (route) =>
    route.fulfill({
      json: { id: 1, name: "Test", checkpoint: "test.safetensors" },
    })
  );
  await page.route("**/youtube/credentials/**", (route) =>
    route.fulfill({ json: { connected: false } })
  );
  await page.route("**/materials/check**", (route) =>
    route.fulfill({ json: { ready: true, missing: [] } })
  );
}

/**
 * Navigate to Studio with an existing empty storyboard (?id=2).
 * This avoids the draft-creation race condition from ?new=true.
 * Storyboard 2 (Travel Tips) has no scenes → enables generate flow.
 */
async function navigateToEmptyStoryboard(page: Page) {
  await page.goto("/studio?id=2");
  // Wait for Script tab to be ready
  await expect(page.getByRole("button", { name: "Script", exact: true })).toBeVisible({
    timeout: 15000,
  });
  // Dismiss style profile modal — click "건너뛰기" (skip) with auto-wait
  await page
    .getByRole("button", { name: "건너뛰기" })
    .click({ timeout: 8000 })
    .catch(() => {});
  // Wait for dialog to fully close before interacting with chat
  await expect(page.getByRole("dialog"))
    .not.toBeVisible({ timeout: 5000 })
    .catch(() => {});
  // Ensure chat input is interactive
  await expect(page.locator("[data-chat-input]")).toBeEnabled({ timeout: 5000 });
}

// ── Tests ────────────────────────────────────────────────────────

test.describe("Warning Toast — SSE completion warnings", () => {
  test.beforeEach(async ({ page }) => {
    // Pre-seed context store with groupId
    await page.addInitScript(() => {
      window.localStorage.setItem(
        "shorts-producer:context:v1",
        JSON.stringify({
          state: { projectId: 1, groupId: 1, storyboardId: null, storyboardTitle: "" },
          version: 0,
        })
      );
    });

    await mockGlobalApis(page);
    await mockStudioApis(page);
    await mockPipelineApis(page);
  });

  test("shows warning toast when SSE completion has warnings", async ({ page }) => {
    const WARNING_MSG =
      "TTS Designer 실패: voice design이 누락되어 기본 음성으로 생성됩니다. (timeout)";

    await page.route("**/scripts/generate-stream", (route) => {
      return route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        headers: { "Cache-Control": "no-cache" },
        body: buildSSEBody({ warnings: [WARNING_MSG] }),
      });
    });

    await navigateToEmptyStoryboard(page);

    // Type topic and send
    const input = page.locator("[data-chat-input]");
    await input.fill("테스트 주제");
    await page.keyboard.press("Enter");

    // Wait for settings recommendation card → click "스크립트 생성"
    const generateBtn = page.getByRole("button", { name: "스크립트 생성" });
    await expect(generateBtn).toBeVisible({ timeout: 10000 });
    await generateBtn.click();

    // Verify: success toast should appear (role="status" for success/info types)
    const successToast = page.getByRole("status").filter({ hasText: /스크립트 생성 완료/ });
    await expect(successToast).toBeVisible({ timeout: 10000 });

    // Verify: warning toast should appear (role="alert" for warning/error types)
    const warningToast = page.getByRole("alert").filter({ hasText: /TTS Designer 실패/ });
    await expect(warningToast).toBeVisible({ timeout: 5000 });
  });

  test("shows only success toast when SSE completion has no warnings", async ({ page }) => {
    await page.route("**/scripts/generate-stream", (route) => {
      return route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        headers: { "Cache-Control": "no-cache" },
        body: buildSSEBody({}),
      });
    });

    await navigateToEmptyStoryboard(page);

    const input = page.locator("[data-chat-input]");
    await input.fill("테스트 주제");
    await page.keyboard.press("Enter");

    const generateBtn = page.getByRole("button", { name: "스크립트 생성" });
    await expect(generateBtn).toBeVisible({ timeout: 10000 });
    await generateBtn.click();

    // Verify: success toast appears (use role="status" to target toast specifically)
    const successToast = page.getByRole("status").filter({ hasText: /스크립트 생성 완료/ });
    await expect(successToast).toBeVisible({ timeout: 10000 });

    // Verify: NO warning toast
    await page.waitForTimeout(1000);
    await expect(page.getByRole("alert").filter({ hasText: /TTS Designer/ })).not.toBeVisible();
  });
});
