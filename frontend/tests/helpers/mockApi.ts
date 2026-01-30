import type { Page } from "@playwright/test";

// ── Fixture data ───────────────────────────────────────────────

export const MOCK_STORYBOARDS = [
  {
    id: 1,
    title: "Morning Routine",
    description: "A daily morning routine vlog",
    scene_count: 3,
    image_count: 2,
    created_at: "2026-01-20T10:00:00Z",
    updated_at: "2026-01-25T14:30:00Z",
    default_character_id: 1,
    scenes: [
      { script: "Good morning everyone!", speaker: "A", duration: 4, image_prompt: "1girl, waking_up, bedroom", image_prompt_ko: "아침에 일어나는 소녀", image_url: null, negative_prompt: "bad quality", steps: 27, cfg_scale: 7, sampler_name: "DPM++ 2M Karras", seed: -1, clip_skip: 2 },
      { script: "Time for coffee.", speaker: "Narrator", duration: 3, image_prompt: "1girl, drinking_coffee, kitchen", image_prompt_ko: "커피를 마시는 소녀", image_url: null, negative_prompt: "bad quality", steps: 27, cfg_scale: 7, sampler_name: "DPM++ 2M Karras", seed: -1, clip_skip: 2 },
      { script: "Let's head out!", speaker: "A", duration: 3, image_prompt: "1girl, walking, street", image_prompt_ko: "거리를 걷는 소녀", image_url: null, negative_prompt: "bad quality", steps: 27, cfg_scale: 7, sampler_name: "DPM++ 2M Karras", seed: -1, clip_skip: 2 },
    ],
  },
  {
    id: 2,
    title: "Travel Tips",
    description: "Top 5 travel tips for beginners",
    scene_count: 0,
    image_count: 0,
    created_at: "2026-01-22T08:00:00Z",
    updated_at: "2026-01-22T08:00:00Z",
    scenes: [],
  },
];

export const MOCK_CHARACTERS = [
  { id: 1, name: "Hana", gender: "female", description: "Cheerful high school girl", preview_image_url: null, prompt_mode: "auto", tags: [], loras: [] },
];

const MOCK_GENERATED_SCENES = {
  scenes: [
    { script: "Scene one narration", speaker: "Narrator", duration: 4, image_prompt: "1girl, park, sunny_day", image_prompt_ko: "공원의 소녀" },
    { script: "Dialogue line", speaker: "A", duration: 3, image_prompt: "1girl, talking, cafe", image_prompt_ko: "카페에서 이야기하는 소녀" },
    { script: "Closing narration", speaker: "Narrator", duration: 3, image_prompt: "1girl, sunset, smiling", image_prompt_ko: "석양 속 미소 짓는 소녀" },
  ],
};

const MOCK_PRESETS = {
  presets: [
    { id: "monologue", name: "Monologue", name_ko: "독백", structure: "Monologue", sample_topics: ["A rainy day reflection"], default_duration: 30, default_language: "Korean" },
  ],
};

// ── Route mocking ──────────────────────────────────────────────

export async function mockStudioApis(page: Page) {
  // Storyboard list
  await page.route("**/storyboards", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: MOCK_STORYBOARDS.map(({ scenes: _s, ...rest }) => rest) });
    }
    return route.continue();
  });

  // Storyboard detail
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

  // Create storyboard
  await page.route("**/storyboards/create", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({ json: MOCK_GENERATED_SCENES });
    }
    return route.continue();
  });

  // Characters
  await page.route("**/characters", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: MOCK_CHARACTERS });
    }
    return route.continue();
  });

  // IP-Adapter references
  await page.route("**/controlnet/ip-adapter/references", (route) =>
    route.fulfill({ json: { references: [] } }),
  );

  // Output tab resources
  await page.route("**/audio/list", (route) =>
    route.fulfill({ json: { audios: [{ name: "bgm_chill.mp3", url: "/audio/bgm_chill.mp3" }] } }),
  );
  await page.route("**/fonts/list", (route) =>
    route.fulfill({ json: { fonts: ["온글잎 박다현체.ttf"] } }),
  );
  await page.route("**/sd/models", (route) =>
    route.fulfill({ json: { models: [{ title: "animagine-v3", model_name: "animagine-v3" }] } }),
  );

  // Presets
  await page.route("**/presets", (route) =>
    route.fulfill({ json: MOCK_PRESETS }),
  );

  // Tags & LoRAs (for Home characters tab)
  await page.route("**/tags", (route) => route.fulfill({ json: [] }));
  await page.route("**/loras", (route) => route.fulfill({ json: [] }));
}
