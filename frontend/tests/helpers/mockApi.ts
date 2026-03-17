import type { Page } from "@playwright/test";
import {
  MOCK_PROJECTS,
  MOCK_GROUPS,
  MOCK_CHARACTERS_LIST,
  MOCK_CHARACTER_DETAIL,
  MOCK_VOICE_PRESETS,
  MOCK_MUSIC_PRESETS,
  MOCK_TAG_GROUPS,
  MOCK_STYLE_PROFILES,
  MOCK_STORAGE_STATS,
  MOCK_RENDER_PRESETS,
  MOCK_TRASH_ITEMS,
  MOCK_STORYBOARDS,
  MOCK_CHARACTERS,
  MOCK_PRESETS,
} from "./fixtures";

// Re-export for backward compat with existing E2E tests
export { MOCK_STORYBOARDS, MOCK_CHARACTERS };

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const storyboardListItems = () => MOCK_STORYBOARDS.map(({ scenes: _s, ...rest }) => rest);

// ── Global APIs (AppShell: health, projects, groups) ─────────
export async function mockGlobalApis(page: Page) {
  await page.route("**/health", (route) => route.fulfill({ json: { status: "ok" } }));

  await page.route(/\/projects(\?.*)?$/, (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: MOCK_PROJECTS });
    }
    return route.continue();
  });

  await page.route("**/api/**/groups**", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: MOCK_GROUPS });
    }
    return route.continue();
  });
}
// ── Studio page ──────────────────────────────────────────────

export async function mockStudioApis(page: Page) {
  // Match storyboards list (with or without query params) and individual storyboard by ID
  await page.route(/\/storyboards(\?.*)?$/, (route) => {
    if (route.request().method() === "GET") {
      const items = storyboardListItems();
      return route.fulfill({
        json: { items, total: items.length, offset: 0, limit: 50 },
      });
    }
    return route.continue();
  });

  await page.route(/\/storyboards\/(\d+)$/, (route) => {
    const url = route.request().url();
    const match = url.match(/\/storyboards\/(\d+)$/);
    if (match && route.request().method() === "GET") {
      const id = Number(match[1]);
      const sb = MOCK_STORYBOARDS.find((s) => s.id === id);
      return route.fulfill({ json: sb ?? { error: "not found" }, status: sb ? 200 : 404 });
    }
    return route.continue();
  });

  await page.route("**/api/**/characters", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: { items: MOCK_CHARACTERS, total: MOCK_CHARACTERS.length, offset: 0, limit: 50 },
      });
    }
    return route.continue();
  });

  await page.route("**/controlnet/ip-adapter/references", (route) =>
    route.fulfill({ json: { references: [] } })
  );

  await page.route("**/audio/list", (route) =>
    route.fulfill({ json: { audios: [{ name: "bgm_chill.mp3", url: "/audio/bgm_chill.mp3" }] } })
  );
  await page.route("**/fonts/list", (route) =>
    route.fulfill({ json: { fonts: ["온글잎 박다현체.ttf"] } })
  );
  await page.route("**/sd/models", (route) =>
    route.fulfill({ json: { models: [{ title: "animagine-v3", model_name: "animagine-v3" }] } })
  );

  await page.route("**/presets", (route) => route.fulfill({ json: MOCK_PRESETS }));
  await page.route("**/tags", (route) => route.fulfill({ json: [] }));
  await page.route("**/loras", (route) => route.fulfill({ json: [] }));
}
// ── Characters page ──────────────────────────────────────────

export async function mockCharactersApis(page: Page) {
  await page.route("**/api/**/characters", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: {
          items: MOCK_CHARACTERS_LIST,
          total: MOCK_CHARACTERS_LIST.length,
          offset: 0,
          limit: 50,
        },
      });
    }
    return route.continue();
  });

  await page.route("**/api/**/characters/*", (route) => {
    const url = route.request().url();
    if (url.match(/\/characters\/\d+$/) && route.request().method() === "GET") {
      return route.fulfill({ json: MOCK_CHARACTER_DETAIL });
    }
    return route.continue();
  });

  await page.route("**/tags**", (route) => route.fulfill({ json: [] }));
  await page.route("**/loras**", (route) => route.fulfill({ json: [] }));
  await page.route("**/voice-presets**", (route) =>
    route.fulfill({ json: { items: MOCK_VOICE_PRESETS, total: MOCK_VOICE_PRESETS.length } })
  );
}

export async function mockCharactersEmptyApis(page: Page) {
  await page.route("**/api/**/characters", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: { items: [], total: 0, offset: 0, limit: 50 } });
    }
    return route.continue();
  });
  await page.route("**/tags**", (route) => route.fulfill({ json: [] }));
  await page.route("**/loras**", (route) => route.fulfill({ json: [] }));
}
// ── Voices page ──────────────────────────────────────────────

export async function mockVoicesApis(page: Page) {
  await page.route("**/voice-presets**", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: { items: MOCK_VOICE_PRESETS, total: MOCK_VOICE_PRESETS.length, offset: 0, limit: 50 },
      });
    }
    return route.continue();
  });
  await page.route("**/presets", (route) => route.fulfill({ json: MOCK_PRESETS }));
}

export async function mockVoicesEmptyApis(page: Page) {
  await page.route("**/voice-presets**", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: { items: [], total: 0, offset: 0, limit: 50 } });
    }
    return route.continue();
  });
  await page.route("**/presets", (route) => route.fulfill({ json: MOCK_PRESETS }));
}
// ── Music page ───────────────────────────────────────────────

export async function mockMusicApis(page: Page) {
  await page.route("**/music-presets**", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: { items: MOCK_MUSIC_PRESETS, total: MOCK_MUSIC_PRESETS.length, offset: 0, limit: 50 },
      });
    }
    return route.continue();
  });
}

export async function mockMusicEmptyApis(page: Page) {
  await page.route("**/music-presets**", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: { items: [], total: 0, offset: 0, limit: 50 } });
    }
    return route.continue();
  });
}
// ── Scripts page ─────────────────────────────────────────────

export async function mockScriptsApis(page: Page) {
  await page.route(/\/storyboards(\?.*)?$/, (route) => {
    if (route.request().method() === "GET") {
      const items = storyboardListItems();
      return route.fulfill({
        json: { items, total: items.length, offset: 0, limit: 50 },
      });
    }
    return route.continue();
  });

  await page.route(/\/storyboards\/(\d+)$/, (route) => {
    const url = route.request().url();
    const match = url.match(/\/storyboards\/(\d+)$/);
    if (match && route.request().method() === "GET") {
      const id = Number(match[1]);
      const sb = MOCK_STORYBOARDS.find((s) => s.id === id);
      return route.fulfill({ json: sb ?? { error: "not found" }, status: sb ? 200 : 404 });
    }
    return route.continue();
  });

  await page.route("**/presets", (route) => route.fulfill({ json: MOCK_PRESETS }));
  await page.route("**/api/**/characters", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: {
          items: MOCK_CHARACTERS_LIST,
          total: MOCK_CHARACTERS_LIST.length,
          offset: 0,
          limit: 50,
        },
      });
    }
    return route.continue();
  });
}

/** Scripts page mock returning empty storyboard list */
export async function mockScriptsEmptyApis(page: Page) {
  await page.route(/\/storyboards(\?.*)?$/, (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: { items: [], total: 0, offset: 0, limit: 50 } });
    }
    return route.continue();
  });
  await page.route("**/presets", (route) => route.fulfill({ json: MOCK_PRESETS }));
  await page.route("**/api/**/characters", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: { items: [], total: 0, offset: 0, limit: 50 } });
    }
    return route.continue();
  });
}
// ── Manage page ──────────────────────────────────────────────

export async function mockManageApis(page: Page) {
  // TagsTab
  await page.route("**/tags/groups**", (route) => route.fulfill({ json: MOCK_TAG_GROUPS }));
  await page.route("**/tags/pending**", (route) => route.fulfill({ json: [] }));
  await page.route("**/tags/search**", (route) => route.fulfill({ json: [] }));
  await page.route("**/admin/tags/deprecated**", (route) => route.fulfill({ json: [] }));

  // StyleTab
  await page.route("**/style-profiles**", (route) => route.fulfill({ json: MOCK_STYLE_PROFILES }));
  await page.route("**/sd/models**", (route) =>
    route.fulfill({ json: { models: [{ title: "animagine-v3", model_name: "animagine-v3" }] } })
  );
  await page.route("**/embeddings**", (route) => route.fulfill({ json: [] }));

  // RenderPresetsTab
  await page.route("**/render-presets**", (route) => route.fulfill({ json: MOCK_RENDER_PRESETS }));
  await page.route("**/audio/list", (route) =>
    route.fulfill({ json: { audios: [{ name: "bgm_chill.mp3", url: "/audio/bgm_chill.mp3" }] } })
  );
  await page.route("**/fonts/list", (route) =>
    route.fulfill({ json: { fonts: ["온글잎 박다현체.ttf"] } })
  );
  await page.route("**/overlay/list**", (route) => route.fulfill({ json: { overlays: [] } }));

  // TrashTab
  await page.route("**/storyboards/trash**", (route) => route.fulfill({ json: MOCK_TRASH_ITEMS }));
  await page.route("**/characters/trash**", (route) => route.fulfill({ json: MOCK_TRASH_ITEMS }));

  // YouTubeTab
  await page.route("**/youtube/credentials/**", (route) =>
    route.fulfill({ json: { connected: false } })
  );

  // SettingsTab
  await page.route("**/storage/stats**", (route) => route.fulfill({ json: MOCK_STORAGE_STATS }));
  await page.route("**/admin/media-assets/stats**", (route) =>
    route.fulfill({ json: { total: 0, total_size_mb: 0 } })
  );

  // Shared
  await page.route("**/presets", (route) => route.fulfill({ json: MOCK_PRESETS }));
  await page.route("**/tags", (route) => route.fulfill({ json: [] }));
  await page.route("**/loras**", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/**/characters", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: {
          items: MOCK_CHARACTERS_LIST,
          total: MOCK_CHARACTERS_LIST.length,
          offset: 0,
          limit: 50,
        },
      });
    }
    return route.continue();
  });
  await page.route(/\/storyboards(\?.*)?$/, (route) => {
    if (route.request().method() === "GET") {
      const items = storyboardListItems();
      return route.fulfill({
        json: { items, total: items.length, offset: 0, limit: 50 },
      });
    }
    return route.continue();
  });
}
