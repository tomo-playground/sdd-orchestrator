import { test, expect, type Page } from "@playwright/test";
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
    await expect(page.getByRole("button", { name: "대본", exact: true })).toBeVisible();
  });

  // ── 3. Tab switching ────────────────────────────────────────

  test("tab switching cycles through all 4 tabs", async ({ page }) => {
    await page.goto("/studio?new=true");
    // Verify all 4 tabs exist (use exact: true to avoid matching "Go to Script" etc.)
    await expect(page.getByRole("button", { name: "대본", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "준비", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "이미지", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "게시", exact: true })).toBeVisible();

    // Click Stage tab
    await page.getByRole("button", { name: "준비", exact: true }).click();
    // Click Direct tab
    await page.getByRole("button", { name: "이미지", exact: true }).click();
    // Click Publish tab
    await page.getByRole("button", { name: "게시", exact: true }).click();
    // Click Script tab back
    await page.getByRole("button", { name: "대본", exact: true }).click();
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
    await page.getByRole("link", { name: "홈" }).click();
    await expect(page).toHaveURL(/\/$/);
  });

  // ── 7. New story from kanban ────────────────────────────────

  test("new story button from kanban shows editor view", async ({ page }) => {
    await page.goto("/studio");
    await expect(page.getByText("영상 목록")).toBeVisible({ timeout: 5000 });
    await page.getByRole("button", { name: /새 영상/i }).click();
    // After clicking, the editor view should appear with Script tab
    await expect(page.getByRole("button", { name: "대본", exact: true })).toBeVisible({
      timeout: 5000,
    });
  });

  // ── 8. Chat history not overwritten on storyboard load ──────

  test("preserves chat history in localStorage when storyboard loads", async ({ page }) => {
    const sbId = MOCK_STORYBOARDS[0].id;

    // Pre-seed localStorage with chat history for storyboard 1
    await page.addInitScript((id: number) => {
      const chatStore = {
        state: {
          histories: {
            [String(id)]: [
              {
                id: "welcome-1",
                role: "assistant",
                contentType: "assistant",
                text: "주제를 입력하면 AI가 최적의 설정을 추천해 드립니다.",
                timestamp: 1000,
              },
              {
                id: "user-1",
                role: "user",
                contentType: "user",
                text: "아침 루틴 영상 만들어줘",
                timestamp: 2000,
              },
              {
                id: "assistant-1",
                role: "assistant",
                contentType: "completion",
                text: "대본이 생성되었습니다. (3개 씬)",
                timestamp: 3000,
              },
            ],
          },
        },
        version: 0,
      };
      window.localStorage.setItem("shorts-producer:chat:v1", JSON.stringify(chatStore));
    }, sbId);

    await page.goto(`/studio?id=${sbId}`);
    await page.waitForTimeout(2000);

    // Verify localStorage was NOT overwritten with just welcome message
    const historyCount = await page.evaluate((id: number) => {
      const raw = window.localStorage.getItem("shorts-producer:chat:v1");
      if (!raw) return 0;
      const parsed = JSON.parse(raw);
      const msgs = parsed?.state?.histories?.[String(id)] ?? [];
      return msgs.length;
    }, sbId);

    // Should still have 3 messages (welcome + user + completion), not 1 (just welcome)
    expect(historyCount).toBeGreaterThanOrEqual(3);
  });

  // ── 9. New storyboard clears temp chat data ───────────────

  test("new storyboard clears __new__ temp key", async ({ page }) => {
    // Pre-seed __new__ with stale data
    await page.addInitScript(() => {
      const chatStore = {
        state: {
          histories: {
            __new__: [
              {
                id: "stale-1",
                role: "user",
                contentType: "user",
                text: "이전 세션 잔여 데이터",
                timestamp: 1000,
              },
            ],
          },
        },
        version: 0,
      };
      window.localStorage.setItem("shorts-producer:chat:v1", JSON.stringify(chatStore));
    });

    await page.goto("/studio?new=true");
    await page.waitForTimeout(2000);

    // __new__ key should be cleared by resetAllStores
    const newKeyCount = await page.evaluate(() => {
      const raw = window.localStorage.getItem("shorts-producer:chat:v1");
      if (!raw) return 0;
      const parsed = JSON.parse(raw);
      return (parsed?.state?.histories?.["__new__"] ?? []).length;
    });

    expect(newKeyCount).toBe(0);
  });

  // ── 10. Direct tab: image generation trigger ──────────────

  test("Direct tab: Generate button triggers scene/generate API", async ({ page }) => {
    await page.goto(`/studio?id=${MOCK_STORYBOARDS[0].id}`);
    await expect(page.getByText(MOCK_STORYBOARDS[0].title).first()).toBeVisible({ timeout: 5000 });

    // Switch to Direct tab
    await page.getByRole("button", { name: /^Direct/ }).click();

    // Wait for scenes to render (Scenes heading visible in SceneListPanel)
    await expect(page.getByRole("heading", { name: "Scenes" })).toBeVisible({ timeout: 5000 });

    // Track if scene/generate API was called
    const generateRequest = interceptRequest(page, "scene/generate");

    // Click Generate button
    await page.getByRole("button", { name: "Generate" }).click();

    // Verify API call was made
    const req = await generateRequest;
    expect(req).toBeTruthy();
  });

  // ── 11. Direct tab: scene prompt edit + save ──────────────

  test("Direct tab: editing script triggers autoSave PUT", async ({ page }) => {
    await page.goto(`/studio?id=${MOCK_STORYBOARDS[0].id}`);
    await expect(page.getByText(MOCK_STORYBOARDS[0].title).first()).toBeVisible({ timeout: 5000 });

    // Switch to Direct tab
    await page.getByRole("button", { name: /^Direct/ }).click();
    await expect(page.getByRole("heading", { name: "Scenes" })).toBeVisible({ timeout: 5000 });

    // Track PUT storyboard call (autoSave)
    const saveRequest = interceptRequest(page, /\/storyboards\/\d+$/, "PUT");

    // Find the scene Script textbox (visible in SceneDetailPanel)
    const scriptInput = page.getByRole("textbox").first();
    await expect(scriptInput).toBeVisible({ timeout: 5000 });
    await scriptInput.fill("Hello world!");

    // Wait for autoSave debounce (2s) + network
    const req = await saveRequest;
    expect(req).toBeTruthy();

    // Verify text is retained
    await expect(scriptInput).toHaveValue("Hello world!");
  });

  // ── 12. Direct tab: scene delete → list update + autoSave ─
  test("Direct tab: deleting scene updates scene list", async ({ page }) => {
    await page.goto(`/studio?id=${MOCK_STORYBOARDS[0].id}`);
    await expect(page.getByText(MOCK_STORYBOARDS[0].title).first()).toBeVisible({ timeout: 5000 });

    // Switch to Direct tab
    await page.getByRole("button", { name: /^Direct/ }).click();

    // Verify initial scene count (3 scenes) — use the SceneListPanel summary text
    const sceneCountText = page.getByText(/3개 씬 · 총/);
    await expect(sceneCountText).toBeVisible({ timeout: 5000 });

    // Track autoSave PUT triggered by removeScene → isDirty
    const saveRequest = interceptRequest(page, /\/storyboards\/\d+$/, "PUT");

    // Click "Delete Scene" button (visible in SceneNavHeader)
    await page.getByRole("button", { name: "Delete Scene" }).click();

    // Confirm in ConfirmDialog — the confirm button text is "삭제" (exact match)
    const confirmBtn = page.getByText("삭제", { exact: true });
    await expect(confirmBtn).toBeVisible({ timeout: 3000 });
    await confirmBtn.click();

    // Verify scene count decreased to 2
    await expect(page.getByText(/2개 씬 · 총/)).toBeVisible({ timeout: 5000 });

    // Verify autoSave PUT was triggered (removeScene sets isDirty → 2s debounce → PUT)
    const saved = await saveRequest;
    expect(saved).toBeTruthy();
  });

  // ── 13. Direct tab: TTS preview → audio state ─────────────

  test("Direct tab: TTS preview button triggers API and shows play button", async ({ page }) => {
    await page.goto(`/studio?id=${MOCK_STORYBOARDS[0].id}`);
    await expect(page.getByText(MOCK_STORYBOARDS[0].title).first()).toBeVisible({ timeout: 5000 });

    // Switch to Direct tab
    await page.getByRole("button", { name: /^Direct/ }).click();
    await expect(page.getByRole("heading", { name: "Scenes" })).toBeVisible({ timeout: 5000 });

    // Track TTS preview API call
    const ttsRequest = interceptRequest(page, "preview/tts");

    // Click 미리듣기 button
    const previewBtn = page.getByRole("button", { name: "미리듣기" });
    await expect(previewBtn).toBeVisible({ timeout: 5000 });
    await previewBtn.click();

    // Verify API call
    const req = await ttsRequest;
    expect(req).toBeTruthy();

    // After TTS response, stop/play button should appear
    await expect(page.getByRole("button", { name: /^■ 정지$/ })).toBeVisible({ timeout: 5000 });
  });
});

// ── Helpers ──────────────────────────────────────────────────

/** Intercept a request matching a URL pattern and optional method, resolving when it fires. */
function interceptRequest(
  page: Page,
  urlPattern: string | RegExp,
  method?: string
): Promise<boolean> {
  return page
    .waitForRequest(
      (req) => {
        const matchesUrl =
          typeof urlPattern === "string"
            ? req.url().includes(urlPattern)
            : urlPattern.test(req.url());
        return matchesUrl && (!method || req.method() === method);
      },
      { timeout: 15000 }
    )
    .then(() => true)
    .catch(() => false);
}
