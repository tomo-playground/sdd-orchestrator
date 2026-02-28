// ── AppShell global fixtures (projects, groups) ──────────────

export const MOCK_PROJECTS = [
  { id: 1, name: "My Project", description: "Default project", created_at: "2026-01-10T00:00:00Z" },
];

export const MOCK_GROUPS = [
  {
    id: 1,
    name: "Default Group",
    project_id: 1,
    created_at: "2026-01-10T00:00:00Z",
    render_preset_id: null,
    style_profile_id: null,
    narrator_voice_preset_id: null,
  },
  {
    id: 2,
    name: "Chibi Group",
    project_id: 1,
    created_at: "2026-01-15T00:00:00Z",
    render_preset_id: null,
    style_profile_id: null,
    narrator_voice_preset_id: null,
  },
];
