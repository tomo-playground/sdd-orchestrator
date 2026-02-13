// ── AppShell global fixtures (projects, groups) ──────────────

export const MOCK_PROJECTS = [
  { id: 1, name: "My Project", description: "Default project", created_at: "2026-01-10T00:00:00Z" },
];

export const MOCK_GROUPS = [
  { id: 1, name: "Default Group", project_id: 1, created_at: "2026-01-10T00:00:00Z" },
  { id: 2, name: "Chibi Group", project_id: 1, created_at: "2026-01-15T00:00:00Z" },
];

export const MOCK_GROUP_CONFIG = {
  id: 1,
  group_id: 1,
  default_structure: "Monologue",
  default_language: "Korean",
  default_duration: 30,
  style_profile_id: null,
  character_id: null,
  sd_steps: 27,
  sd_cfg_scale: 7,
  sd_sampler_name: "DPM++ 2M Karras",
  sd_clip_skip: 2,
};
