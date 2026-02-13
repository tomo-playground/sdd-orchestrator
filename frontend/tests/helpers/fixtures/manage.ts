// ── Manage page fixtures ─────────────────────────────────────

export const MOCK_STYLE_PROFILES: unknown[] = [];

export const MOCK_STORAGE_STATS = {
  total_size_mb: 256.4,
  total_count: 142,
  directories: {
    images: { size_mb: 180.2, count: 95 },
    audio: { size_mb: 45.1, count: 30 },
    video: { size_mb: 31.1, count: 17 },
  },
};

export const MOCK_TAG_GROUPS = [
  {
    category: "hair_color",
    tags: [
      { id: 1, name: "brown_hair", category: "hair_color" },
      { id: 2, name: "black_hair", category: "hair_color" },
    ],
  },
];

export const MOCK_RENDER_PRESETS: unknown[] = [];

export const MOCK_TRASH_ITEMS = {
  items: [],
  total: 0,
  offset: 0,
  limit: 50,
};
