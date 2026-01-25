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
 * Based on SD best practices: quality → subject → appearance → clothing → expression → gaze → pose → camera → environment → mood → LoRA
 */
export const TOKEN_PRIORITY: Record<string, number> = {
  // Priority 1: Quality (맨 앞에 배치)
  "masterpiece": 1, "best quality": 1, "high quality": 1, "amazing quality": 1,
  "detailed": 1, "ultra detailed": 1, "extremely detailed": 1,
  "absurdres": 1, "highres": 1, "8k": 1,

  // Priority 2: Subject (who/how many)
  "1girl": 2, "1boy": 2, "2girls": 2, "2boys": 2, "3girls": 2, "3boys": 2,
  "multiple girls": 2, "multiple boys": 2,
  "solo": 2, "duo": 2, "trio": 2, "group": 2, "couple": 2,

  // Priority 3-4: Character appearance (hair, eyes, features)
  // Matched by patterns below

  // Priority 5: Clothing
  // Matched by patterns below

  // Priority 6: Expression/emotion
  "smile": 6, "smiling": 6, "happy": 6, "sad": 6, "crying": 6, "angry": 6,
  "surprised": 6, "shocked": 6, "embarrassed": 6, "shy": 6, "blush": 6, "blushing": 6,
  "serious": 6, "determined": 6, "confident": 6, "nervous": 6, "scared": 6,
  "laughing": 6, "grin": 6, "frown": 6, "pout": 6, "expressionless": 6,
  "open mouth": 6, "closed mouth": 6, "tongue out": 6,

  // Priority 7: Gaze direction
  "looking at viewer": 7, "looking away": 7, "looking up": 7, "looking down": 7,
  "looking to the side": 7, "looking back": 7, "eye contact": 7,
  "eyes closed": 7, "closed eyes": 7, "half-closed eyes": 7, "wink": 7,

  // Priority 8: Pose (static)
  "standing": 8, "sitting": 8, "kneeling": 8, "crouching": 8, "squatting": 8,
  "lying": 8, "lying down": 8, "on back": 8, "on stomach": 8,
  "leaning": 8, "reclining": 8, "lounging": 8,
  "arms crossed": 8, "arms behind back": 8, "hands on hips": 8,
  "hand on hip": 8, "hand up": 8, "peace sign": 8, "v": 8,

  // Priority 9: Action (dynamic)
  "walking": 9, "running": 9, "jumping": 9, "dancing": 9,
  "reading": 9, "writing": 9, "eating": 9, "drinking": 9,
  "sleeping": 9, "waving": 9, "pointing": 9, "hugging": 9,

  // Priority 10: Camera/composition
  "close-up": 10, "portrait": 10, "bust shot": 10, "upper body": 10,
  "cowboy shot": 10, "full body": 10, "wide shot": 10,
  "from above": 10, "from below": 10, "from side": 10, "from behind": 10,
  "dutch angle": 10, "low angle": 10, "high angle": 10, "pov": 10,

  // Priority 11: Location/environment
  "indoors": 11, "outdoors": 11,
  "library": 11, "cafe": 11, "street": 11, "room": 11, "bedroom": 11, "office": 11,
  "classroom": 11, "park": 11, "forest": 11, "beach": 11, "city": 11,

  // Priority 12: Background type
  "simple background": 12, "white background": 12, "black background": 12,
  "gradient background": 12, "blurry background": 12, "detailed background": 12,

  // Priority 13: Time/weather
  "day": 13, "night": 13, "sunset": 13, "sunrise": 13, "dusk": 13, "dawn": 13,
  "sunny": 13, "cloudy": 13, "rainy": 13, "rain": 13, "snowy": 13, "snow": 13,

  // Priority 14: Lighting
  "natural light": 14, "sunlight": 14, "moonlight": 14,
  "backlighting": 14, "rim light": 14, "dramatic lighting": 14,
  "soft lighting": 14, "neon lights": 14,

  // Priority 15: Mood
  "romantic": 15, "melancholic": 15, "peaceful": 15, "dramatic": 15,
  "mysterious": 15, "ethereal": 15, "cozy": 15, "lonely": 15,
};

// Patterns for categorizing tokens by priority
export const TOKEN_PRIORITY_PATTERNS: Array<{ pattern: RegExp; priority: number }> = [
  // Priority 3-4: Appearance (hair, eyes, etc.)
  { pattern: /hair$/i, priority: 3.5 },         // "blue hair", "long hair"
  { pattern: /eyes$/i, priority: 4 },           // "red eyes", "blue eyes"
  { pattern: /skin$/i, priority: 4 },           // "pale skin", "dark skin"
  { pattern: /ears$/i, priority: 4 },           // "animal ears", "elf ears"
  { pattern: /horns?$/i, priority: 4 },         // "horns"
  { pattern: /wings?$/i, priority: 4 },         // "wings"
  { pattern: /tail$/i, priority: 4 },           // "tail"
  { pattern: /bangs$/i, priority: 3.5 },        // "blunt bangs", "side bangs"
  { pattern: /ponytail$/i, priority: 3.5 },     // "high ponytail"
  { pattern: /twintails$/i, priority: 3.5 },    // "twintails"
  { pattern: /braid$/i, priority: 3.5 },        // "side braid"

  // Priority 5: Clothing
  { pattern: /dress$/i, priority: 5 },
  { pattern: /shirt$/i, priority: 5 },
  { pattern: /skirt$/i, priority: 5 },
  { pattern: /pants$/i, priority: 5 },
  { pattern: /shorts$/i, priority: 5 },
  { pattern: /uniform$/i, priority: 5 },
  { pattern: /outfit$/i, priority: 5 },
  { pattern: /clothes$/i, priority: 5 },
  { pattern: /jacket$/i, priority: 5 },
  { pattern: /coat$/i, priority: 5 },
  { pattern: /sweater$/i, priority: 5 },
  { pattern: /hoodie$/i, priority: 5 },
  { pattern: /hat$/i, priority: 5 },
  { pattern: /cap$/i, priority: 5 },
  { pattern: /glasses$/i, priority: 5 },
  { pattern: /ribbon$/i, priority: 5 },
  { pattern: /accessory$/i, priority: 5 },
  { pattern: /boots$/i, priority: 5 },
  { pattern: /shoes$/i, priority: 5 },
  { pattern: /socks$/i, priority: 5 },
  { pattern: /stockings$/i, priority: 5 },
  { pattern: /thighhighs$/i, priority: 5 },

  // Priority 99: LoRA tags (always last)
  { pattern: /^<lora:/i, priority: 99 },
  { pattern: /^<model:/i, priority: 99 },
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

  // Default: middle priority (between camera and location)
  return 10.5;
};
