// ── Studio page fixtures (storyboards, scenes, presets) ─────

import { MOCK_LANGUAGES } from "./voices";

export const MOCK_STORYBOARDS = [
  {
    id: 1,
    title: "Morning Routine",
    description: "A daily morning routine vlog",
    scene_count: 3,
    image_count: 2,
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
        steps: 27,
        cfg_scale: 7,
        sampler_name: "DPM++ 2M Karras",
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
        steps: 27,
        cfg_scale: 7,
        sampler_name: "DPM++ 2M Karras",
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
        steps: 27,
        cfg_scale: 7,
        sampler_name: "DPM++ 2M Karras",
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
    preview_image_url: null,
    tags: [],
    loras: [],
  },
];

export const MOCK_GENERATED_SCENES = {
  scenes: [
    {
      script: "Scene one narration",
      speaker: "Narrator",
      duration: 4,
      image_prompt: "1girl, park, sunny_day",
      image_prompt_ko: "공원의 소녀",
    },
    {
      script: "Dialogue line",
      speaker: "A",
      duration: 3,
      image_prompt: "1girl, talking, cafe",
      image_prompt_ko: "카페에서 이야기하는 소녀",
    },
    {
      script: "Closing narration",
      speaker: "Narrator",
      duration: 3,
      image_prompt: "1girl, sunset, smiling",
      image_prompt_ko: "석양 속 미소 짓는 소녀",
    },
  ],
};

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
