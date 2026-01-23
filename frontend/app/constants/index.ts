import type { OverlaySettings, PostCardSettings } from "../types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const DEFAULT_BGM = "kawaii-dance-upbeat-japan-anime-edm-242104.mp3";
export const DEFAULT_SUBTITLE_FONT = "온글잎 박다현체.ttf";
export const DRAFT_STORAGE_KEY = "shorts-producer:draft:v1";
export const MAX_IMAGE_CACHE_SIZE = 8_000_000;

export const DEFAULT_OVERLAY_SETTINGS: OverlaySettings = {
  channel_name: "",
  avatar_key: "",
  likes_count: "",
  caption: "",
  frame_style: "overlay_minimal.png",
};

export const DEFAULT_POST_CARD_SETTINGS: PostCardSettings = {
  channel_name: "",
  avatar_key: "",
  caption: "",
};

export const AUTO_RUN_STEPS = [
  { id: "storyboard", label: "Storyboard" },
  { id: "fix", label: "Auto Fix" },
  { id: "images", label: "Images" },
  { id: "validate", label: "Validate" },
  { id: "render", label: "Render" },
] as const;

export const VOICES = [
  { id: "ko-KR-SunHiNeural", label: "SunHi (F)" },
  { id: "ko-KR-InJoonNeural", label: "InJoon (M)" },
  { id: "ko-KR-HyunsuMultilingualNeural", label: "Hyunsu (M)" },
];

export const SAMPLERS = ["DPM++ 2M Karras", "Euler a", "Euler", "DDIM"];

export const OVERLAY_STYLES = [{ id: "overlay_minimal.png", label: "Minimal" }];

export const HEART_EMOJIS = ["❤", "💖", "💗", "💘", "💜", "💙", "💚", "🧡", "🤍"];
export const ASCII_HEARTS = ["<3", "**", "^^", "<<>>"];

export const PROMPT_SAMPLES = [
  {
    id: "eureka",
    label: "Eureka",
    basePrompt:
      "1girl, eureka, (black t-shirt:1.2), purple eyes, aqua hair, short hair, jeans, glasses, hairclip, short sleeves, <lora:eureka_v9:1.0>",
    baseNegative: "verybadimagenegative_v1.3",
  },
  {
    id: "chibi-laugh",
    label: "Chibi Laugh",
    basePrompt: "chibi, eyebrow, laughing, eyebrow down, <lora:chibi-laugh:0.6>",
    baseNegative: "easynegative",
  },
];

export const STRUCTURES = ["Monologue"];

export const CAMERA_KEYWORDS = [
  "close-up",
  "close up",
  "wide shot",
  "medium shot",
  "full body",
  "low angle",
  "high angle",
  "from above",
  "top-down",
];

export const ACTION_KEYWORDS = [
  "sitting",
  "standing",
  "walking",
  "running",
  "jumping",
  "reading",
  "looking",
  "holding",
  "smiling",
  "crying",
  "talking",
];

export const BACKGROUND_KEYWORDS = [
  "library",
  "street",
  "room",
  "city",
  "park",
  "school",
  "classroom",
  "bedroom",
  "office",
  "cafe",
  "forest",
  "beach",
  "sky",
];

export const LIGHTING_KEYWORDS = [
  "lighting",
  "sunlight",
  "shadow",
  "moody",
  "warm",
  "soft light",
  "neon",
  "rain",
  "night",
  "sunset",
];
