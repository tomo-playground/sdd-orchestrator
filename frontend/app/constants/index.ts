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
  // 한국어
  { id: "ko-KR-SunHiNeural", label: "SunHi (한국어, 여)" },
  { id: "ko-KR-InJoonNeural", label: "InJoon (한국어, 남)" },
  // 다국어
  { id: "ko-KR-HyunsuMultilingualNeural", label: "Hyunsu (다국어, 남)" },
  { id: "en-US-AvaMultilingualNeural", label: "Ava (다국어, 여)" },
  { id: "en-US-EmmaMultilingualNeural", label: "Emma (다국어, 여)" },
  // 일본어
  { id: "ja-JP-NanamiNeural", label: "Nanami (일본어, 여)" },
  { id: "ja-JP-KeitaNeural", label: "Keita (일본어, 남)" },
];

export const SAMPLERS = ["DPM++ 2M Karras", "Euler a", "Euler", "DDIM"];

export const OVERLAY_STYLES = [{ id: "overlay_minimal.png", label: "Minimal" }];

export const HEART_EMOJIS = ["❤", "💖", "💗", "💘", "💜", "💙", "💚", "🧡", "🤍"];
export const ASCII_HEARTS = ["<3", "**", "^^", "<<>>"];

export const STRUCTURES = [
  "Monologue",
  "Storytelling",
  "Tutorial",
  "Japanese Lesson",
  "Facts",
  "Motivation",
  "Math Lesson",
];

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

// Combined keywords for scene-specific tokens (used in buildPositivePrompt to filter base prompt)
export const SCENE_SPECIFIC_KEYWORDS = [
  // Actions/poses
  "sitting", "standing", "walking", "running", "jumping", "kneeling", "crouching", "lying",
  // Camera angles
  "from above", "top-down", "low angle", "high angle", "close-up", "wide shot", "full body",
  // Locations
  "library", "cafe", "street", "room", "bedroom", "office", "classroom", "park", "forest", "beach", "city",
  // Time/weather
  "night", "sunset", "sunrise", "rain", "snow",
  // Other
  "background", "lighting", "indoors", "outdoors",
];
