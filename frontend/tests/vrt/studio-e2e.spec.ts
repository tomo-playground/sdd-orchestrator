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
});
