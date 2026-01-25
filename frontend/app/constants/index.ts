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

/**
 * SD Prompt Token Priority Order (lower = earlier in prompt)
 * Based on SD best practices: identity → appearance → expression → pose → camera → environment → quality → LoRA
 */
export const TOKEN_PRIORITY: Record<string, number> = {
  // Priority 1: Identity (who)
  "1girl": 1, "1boy": 1, "2girls": 1, "2boys": 1, "multiple girls": 1, "multiple boys": 1,
  "solo": 1, "duo": 1, "trio": 1, "group": 1,

  // Priority 2: Character appearance (hair, eyes, features)
  // Matched by patterns below

  // Priority 3: Expression/emotion
  "smile": 3, "smiling": 3, "happy": 3, "sad": 3, "crying": 3, "angry": 3,
  "surprised": 3, "shocked": 3, "embarrassed": 3, "shy": 3, "blush": 3, "blushing": 3,
  "serious": 3, "determined": 3, "confident": 3, "nervous": 3, "scared": 3,
  "laughing": 3, "grin": 3, "frown": 3, "pout": 3, "expressionless": 3,
  "closed eyes": 3, "half-closed eyes": 3, "open mouth": 3, "closed mouth": 3,

  // Priority 4: Gaze direction
  "looking at viewer": 4, "looking away": 4, "looking up": 4, "looking down": 4,
  "looking to the side": 4, "looking back": 4, "eye contact": 4,

  // Priority 5: Pose/action
  "sitting": 5, "standing": 5, "walking": 5, "running": 5, "jumping": 5,
  "kneeling": 5, "crouching": 5, "lying": 5, "leaning": 5, "arms crossed": 5,
  "hands on hips": 5, "hand up": 5, "waving": 5, "pointing": 5,
  "reading": 5, "writing": 5, "eating": 5, "drinking": 5, "sleeping": 5,

  // Priority 6: Camera/composition
  "close-up": 6, "portrait": 6, "bust shot": 6, "cowboy shot": 6, "full body": 6,
  "wide shot": 6, "from above": 6, "from below": 6, "from side": 6,
  "dutch angle": 6, "low angle": 6, "high angle": 6,

  // Priority 7: Environment/background
  "indoors": 7, "outdoors": 7, "simple background": 7, "white background": 7,
  "library": 7, "cafe": 7, "street": 7, "room": 7, "bedroom": 7, "office": 7,
  "classroom": 7, "park": 7, "forest": 7, "beach": 7, "city": 7,
  "night": 7, "day": 7, "sunset": 7, "sunrise": 7, "rain": 7, "snow": 7,

  // Priority 8: Quality/style tags
  "masterpiece": 8, "best quality": 8, "high quality": 8, "detailed": 8,
  "ultra detailed": 8, "absurdres": 8, "highres": 8,
};

// Patterns for categorizing tokens by priority
export const TOKEN_PRIORITY_PATTERNS: Array<{ pattern: RegExp; priority: number }> = [
  // Priority 2: Appearance (hair, eyes, etc.)
  { pattern: /hair$/i, priority: 2 },           // "blue hair", "long hair"
  { pattern: /eyes$/i, priority: 2 },           // "red eyes", "closed eyes"
  { pattern: /skin$/i, priority: 2 },           // "pale skin", "dark skin"
  { pattern: /ears$/i, priority: 2 },           // "animal ears", "elf ears"
  { pattern: /horns?$/i, priority: 2 },         // "horns"
  { pattern: /wings?$/i, priority: 2 },         // "wings"
  { pattern: /tail$/i, priority: 2 },           // "tail"

  // Priority 2.5: Clothing (after appearance, before expression)
  { pattern: /dress$/i, priority: 2.5 },
  { pattern: /shirt$/i, priority: 2.5 },
  { pattern: /skirt$/i, priority: 2.5 },
  { pattern: /pants$/i, priority: 2.5 },
  { pattern: /uniform$/i, priority: 2.5 },
  { pattern: /outfit$/i, priority: 2.5 },
  { pattern: /clothes$/i, priority: 2.5 },
  { pattern: /jacket$/i, priority: 2.5 },
  { pattern: /coat$/i, priority: 2.5 },
  { pattern: /hat$/i, priority: 2.5 },
  { pattern: /glasses$/i, priority: 2.5 },
  { pattern: /ribbon$/i, priority: 2.5 },
  { pattern: /accessory$/i, priority: 2.5 },

  // Priority 9: LoRA tags (always last)
  { pattern: /^<lora:/i, priority: 9 },
  { pattern: /^<model:/i, priority: 9 },
];

/**
 * Get priority for a token (lower = earlier in prompt)
 */
export const getTokenPriority = (token: string): number => {
  const lower = token.toLowerCase().trim();

  // Check exact match first
  if (TOKEN_PRIORITY[lower] !== undefined) {
    return TOKEN_PRIORITY[lower];
  }

  // Check patterns
  for (const { pattern, priority } of TOKEN_PRIORITY_PATTERNS) {
    if (pattern.test(lower)) {
      return priority;
    }
  }

  // Default: middle priority (between pose and camera)
  return 5.5;
};
