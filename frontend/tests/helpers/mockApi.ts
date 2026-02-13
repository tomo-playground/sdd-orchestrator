import type { Page } from "@playwright/test";
import {
  MOCK_PROJECTS,
  MOCK_GROUPS,
  MOCK_GROUP_CONFIG,
  MOCK_CHARACTERS_LIST,
  MOCK_CHARACTER_DETAIL,
  MOCK_VOICE_PRESETS,
  MOCK_MUSIC_PRESETS,
  MOCK_BACKGROUNDS,
  MOCK_BG_CATEGORIES,
  MOCK_TAG_GROUPS,
  MOCK_STYLE_PROFILES,
  MOCK_STORAGE_STATS,
  MOCK_RENDER_PRESETS,
  MOCK_TRASH_ITEMS,
  MOCK_TAG_EFFECTIVENESS,
  MOCK_ANALYTICS_SUMMARY,
  MOCK_STORYBOARDS,
  MOCK_CHARACTERS,
  MOCK_GENERATED_SCENES,
  MOCK_PRESETS,
} from "./fixtures";

// Re-export for backward compat with existing E2E tests
export { MOCK_STORYBOARDS, MOCK_CHARACTERS };

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const storyboardListItems = () => MOCK_STORYBOARDS.map(({ scenes: _s, ...rest }) => rest);

// ── Global APIs (AppShell: health, projects, groups) ─────────
export async function mockGlobalApis(page: Page) {
  await page.route("**/health", (route) => route.fulfill({ json: { status: "ok" } }));

  await page.route("**/projects", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: { items: MOCK_PROJECTS, total: MOCK_PROJECTS.length, offset: 0, limit: 50 },
      });
    }
    return route.continue();
  });

  await page.route("**/groups/*/config", (route) => route.fulfill({ json: MOCK_GROUP_CONFIG }));

  await page.route("**/groups**", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: { items: MOCK_GROUPS, total: MOCK_GROUPS.length, offset: 0, limit: 50 },
      });
    }
    return route.continue();
  });
}
// ── Studio page ──────────────────────────────────────────────

export async function mockStudioApis(page: Page) {
  await page.route("**/storyboards", (route) => {
    if (route.request().method() === "GET") {
      const items = storyboardListItems();
      return route.fulfill({
        json: { items, total: items.length, offset: 0, limit: 50 },
      });
    }
    return route.continue();
  });

  await page.route("**/storyboards/*", (route) => {
    const url = route.request().url();
    const match = url.match(/\/storyboards\/(\d+)$/);
    if (match && route.request().method() === "GET") {
      const id = Number(match[1]);
      const sb = MOCK_STORYBOARDS.find((s) => s.id === id);
      return route.fulfill({ json: sb ?? { error: "not found" }, status: sb ? 200 : 404 });
    }
    return route.continue();
  });

  await page.route("**/storyboards/create", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({ json: MOCK_GENERATED_SCENES });
    }
    return route.continue();
  });

  await page.route("**/characters", (route) => {
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
  await page.route("**/characters", (route) => {
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

  await page.route("**/characters/*", (route) => {
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
  await page.route("**/characters", (route) => {
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
// ── Backgrounds page ─────────────────────────────────────────

export async function mockBackgroundsApis(page: Page) {
  await page.route("**/backgrounds/categories**", (route) =>
    route.fulfill({ json: MOCK_BG_CATEGORIES })
  );
  await page.route("**/backgrounds**", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: { items: MOCK_BACKGROUNDS, total: MOCK_BACKGROUNDS.length, offset: 0, limit: 50 },
      });
    }
    return route.continue();
  });
}

/** Backgrounds page mock returning empty list */
export async function mockBackgroundsEmptyApis(page: Page) {
  await page.route("**/backgrounds/categories**", (route) => route.fulfill({ json: [] }));
  await page.route("**/backgrounds**", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: { items: [], total: 0, offset: 0, limit: 50 } });
    }
    return route.continue();
  });
}
// ── Scripts page ─────────────────────────────────────────────

export async function mockScriptsApis(page: Page) {
  await page.route("**/storyboards", (route) => {
    if (route.request().method() === "GET") {
      const items = storyboardListItems();
      return route.fulfill({
        json: { items, total: items.length, offset: 0, limit: 50 },
      });
    }
    return route.continue();
  });

  await page.route("**/storyboards/*", (route) => {
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
  await page.route("**/characters", (route) => {
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
  await page.route("**/storyboards", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: { items: [], total: 0, offset: 0, limit: 50 } });
    }
    return route.continue();
  });
  await page.route("**/presets", (route) => route.fulfill({ json: MOCK_PRESETS }));
  await page.route("**/characters", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: { items: [], total: 0, offset: 0, limit: 50 } });
    }
    return route.continue();
  });
}
// ── Lab page ─────────────────────────────────────────────────

export async function mockLabApis(page: Page) {
  await page.route("**/characters", (route) => {
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

  await page.route("**/groups**", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: { items: MOCK_GROUPS, total: MOCK_GROUPS.length, offset: 0, limit: 50 },
      });
    }
    return route.continue();
  });

  await page.route("**/lab/experiments**", (route) =>
    route.fulfill({ json: { items: [], total: 0 } })
  );

  await page.route("**/lab/analytics/tag-effectiveness**", (route) =>
    route.fulfill({ json: MOCK_TAG_EFFECTIVENESS })
  );

  await page.route("**/lab/analytics/summary**", (route) =>
    route.fulfill({ json: MOCK_ANALYTICS_SUMMARY })
  );

  await page.route("**/tags**", (route) => route.fulfill({ json: [] }));
  await page.route("**/loras**", (route) => route.fulfill({ json: [] }));
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

  // PromptsTab
  await page.route("**/prompt-histories**", (route) =>
    route.fulfill({ json: { items: [], total: 0 } })
  );

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
  await page.route("**/settings/auto-edit**", (route) =>
    route.fulfill({ json: { enabled: false } })
  );
  await page.route("**/analytics/gemini-edits**", (route) =>
    route.fulfill({ json: { items: [], total: 0 } })
  );
  await page.route("**/admin/media-assets/stats**", (route) =>
    route.fulfill({ json: { total: 0, total_size_mb: 0 } })
  );

  // Shared
  await page.route("**/presets", (route) => route.fulfill({ json: MOCK_PRESETS }));
  await page.route("**/tags", (route) => route.fulfill({ json: [] }));
  await page.route("**/loras**", (route) => route.fulfill({ json: [] }));
  await page.route("**/characters", (route) => {
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
  await page.route("**/storyboards", (route) => {
    if (route.request().method() === "GET") {
      const items = storyboardListItems();
      return route.fulfill({
        json: { items, total: items.length, offset: 0, limit: 50 },
      });
    }
    return route.continue();
  });
}
