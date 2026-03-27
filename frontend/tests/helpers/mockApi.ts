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
    const method = route.request().method();
    if (method === "GET") {
      const items = storyboardListItems();
      return route.fulfill({
        json: { items, total: items.length, offset: 0, limit: 50 },
      });
    }
    if (method === "POST") {
      const sb = MOCK_STORYBOARDS[0];
      return route.fulfill({
        json: {
          status: "ok",
          storyboard_id: sb.id,
          scene_ids: [],
          client_ids: [],
          version: 1,
        },
      });
    }
    return route.continue();
  });

  await page.route(/\/storyboards\/(\d+)$/, (route) => {
    const url = route.request().url();
    const match = url.match(/\/storyboards\/(\d+)$/);
    const method = route.request().method();
    if (match && method === "GET") {
      const id = Number(match[1]);
      const sb = MOCK_STORYBOARDS.find((s) => s.id === id);
      return route.fulfill({ json: sb ?? { error: "not found" }, status: sb ? 200 : 404 });
    }
    if (match && method === "PUT") {
      const id = Number(match[1]);
      const sb = MOCK_STORYBOARDS.find((s) => s.id === id) ?? MOCK_STORYBOARDS[0];
      return route.fulfill({
        json: {
          status: "ok",
          storyboard_id: id,
          scene_ids: sb.scenes.map((s) => s.id),
          client_ids: sb.scenes.map((s) => s.client_id),
          version: 2,
        },
      });
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

  // Individual character by ID
  await page.route(/\/characters\/\d+$/, (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: {
          ...MOCK_CHARACTERS[0],
          positive_prompt: "1girl, cheerful",
          negative_prompt: "bad quality",
          loras: [],
        },
      });
    }
    return route.continue();
  });

  // Style profiles (list + individual full)
  await page.route("**/style-profiles**", (route) =>
    route.fulfill({
      json: [{ id: 1, name: "Test Profile", model_name: "animagine-v3", default_steps: 28 }],
    })
  );
  await page.route(/\/style-profiles\/\d+\/full$/, (route) =>
    route.fulfill({
      json: {
        id: 1,
        name: "test-profile",
        display_name: "Test Profile",
        sd_model: { name: "animagine-v3", display_name: "Animagine V3" },
        loras: [],
        negative_embeddings: [],
        positive_embeddings: [],
        default_steps: 28,
        default_cfg_scale: 4.5,
        default_sampler_name: "Euler",
        default_clip_skip: 2,
      },
    })
  );

  // Quality scores
  await page.route("**/quality/summary/**", (route) => route.fulfill({ json: { scores: [] } }));

  // Group effective config
  await page.route("**/groups/*/effective-config", (route) =>
    route.fulfill({
      json: { style_profile_id: 1, character_id: null, render_preset_id: null },
    })
  );

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

  // SD model switch (fires during style profile load)
  await page.route("**/sd/switch**", (route) => route.fulfill({ json: { ok: true } }));

  // Direct tab: image generation (sync + async)
  await page.route("**/scene/generate**", (route) =>
    route.fulfill({
      json: {
        image: "data:image/png;base64,iVBORw0KGgo=",
        images: ["data:image/png;base64,iVBORw0KGgo="],
        seed: 42,
        used_prompt: "1girl, cheerful",
        used_negative_prompt: "",
        used_steps: 28,
        used_cfg_scale: 4.5,
        used_sampler: "Euler",
        debug_payload: '{"request":{},"actual":{}}',
      },
    })
  );

  // Direct tab: TTS preview
  await page.route("**/preview/tts", (route) =>
    route.fulfill({
      json: {
        audio_url: "/audio/mock_tts_preview.wav",
        duration: 3.5,
        cache_key: "mock-cache-key",
        cached: false,
        temp_asset_id: 500,
      },
    })
  );

  // Direct tab: image store
  await page.route("**/image/store", (route) =>
    route.fulfill({
      json: { url: "http://localhost:8188/output/mock_stored.png", asset_id: 1000 },
    })
  );
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
