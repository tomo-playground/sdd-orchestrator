// ── Studio page fixtures (storyboards, scenes, presets) ─────

import { MOCK_LANGUAGES } from "./voices";

export const MOCK_STORYBOARDS = [
  {
    id: 1,
    title: "Morning Routine",
    description: "A daily morning routine vlog",
    scene_count: 3,
    image_count: 2,
    kanban_status: "in_prod" as const,
    cast: [] as Array<{ id: number; name: string; speaker: string; reference_url: string | null }>,
    stage_status: null,
    created_at: "2026-01-20T10:00:00Z",
    updated_at: "2026-01-25T14:30:00Z",
    character_id: 1,
    scenes: [
      {
        script: "Good morning everyone!",
        speaker: "A",
        duration: 4,
        image_prompt: "1girl, waking_up, bedroom",
        image_prompt_ko: "아침에 일어나는 소녀",
        image_url: null,
        negative_prompt: "bad quality",
        steps: 28,
        cfg_scale: 4.5,
        sampler_name: "Euler",
        seed: -1,
        clip_skip: 2,
      },
      {
        script: "Time for coffee.",
        speaker: "Narrator",
        duration: 3,
        image_prompt: "1girl, drinking_coffee, kitchen",
        image_prompt_ko: "커피를 마시는 소녀",
        image_url: null,
        negative_prompt: "bad quality",
        steps: 28,
        cfg_scale: 4.5,
        sampler_name: "Euler",
        seed: -1,
        clip_skip: 2,
      },
      {
        script: "Let's head out!",
        speaker: "A",
        duration: 3,
        image_prompt: "1girl, walking, street",
        image_prompt_ko: "거리를 걷는 소녀",
        image_url: null,
        negative_prompt: "bad quality",
        steps: 28,
        cfg_scale: 4.5,
        sampler_name: "Euler",
        seed: -1,
        clip_skip: 2,
      },
    ],
  },
  {
    id: 2,
    title: "Travel Tips",
    description: "Top 5 travel tips for beginners",
    scene_count: 0,
    image_count: 0,
    kanban_status: "draft" as const,
    cast: [] as Array<{ id: number; name: string; speaker: string; reference_url: string | null }>,
    stage_status: null,
    created_at: "2026-01-22T08:00:00Z",
    updated_at: "2026-01-22T08:00:00Z",
    scenes: [],
  },
];

export const MOCK_CHARACTERS = [
  {
    id: 1,
    name: "Hana",
    gender: "female",
    description: "Cheerful high school girl",
    reference_image_url: null,
    tags: [],
    loras: [],
  },
];

export const MOCK_PRESETS = {
  presets: [
    {
      id: "monologue",
      name: "Monologue",
      name_ko: "독백",
      structure: "Monologue",
      sample_topics: ["A rainy day reflection"],
      default_duration: 30,
      default_language: "Korean",
    },
  ],
  languages: MOCK_LANGUAGES,
};
