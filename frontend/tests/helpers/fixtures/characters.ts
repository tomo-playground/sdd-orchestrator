// ── Characters page fixtures ─────────────────────────────────

export const MOCK_CHARACTERS_LIST = [
  {
    id: 1,
    name: "Hana",
    gender: "female",
    description: "Cheerful high school girl",
    preview_image_url: null,
    prompt_mode: "auto",
    preview_locked: false,
    custom_base_prompt: null,
    tags: [
      { id: 1, name: "brown_hair" },
      { id: 2, name: "blue_eyes" },
    ],
    loras: [{ id: 1, name: "hana_v1", trigger_word: "hana", weight: 0.8 }],
  },
  {
    id: 2,
    name: "Riku",
    gender: "male",
    description: "Calm university student",
    preview_image_url: null,
    prompt_mode: "auto",
    preview_locked: false,
    custom_base_prompt: null,
    tags: [{ id: 3, name: "black_hair" }],
    loras: [],
  },
];

export const MOCK_CHARACTER_DETAIL = {
  id: 1,
  name: "Hana",
  gender: "female",
  description: "Cheerful high school girl with brown hair",
  preview_image_url: null,
  prompt_mode: "auto",
  preview_locked: false,
  custom_base_prompt: null,
  tags: [
    { id: 1, name: "brown_hair" },
    { id: 2, name: "blue_eyes" },
  ],
  loras: [{ id: 1, name: "hana_v1", trigger_word: "hana", weight: 0.8 }],
  negative_tags: [],
  created_at: "2026-01-12T00:00:00Z",
  updated_at: "2026-01-20T00:00:00Z",
};
