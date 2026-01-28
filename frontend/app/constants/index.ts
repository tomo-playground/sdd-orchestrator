import type { OverlaySettings, PostCardSettings } from "../types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const DEFAULT_BGM = "kawaii-dance-upbeat-japan-anime-edm-242104.mp3";
export const DEFAULT_SUBTITLE_FONT = "온글잎 박다현체.ttf";
export const DRAFT_STORAGE_KEY = "shorts-producer:draft:v1";
export const PROMPT_APPLY_KEY = "shorts-producer:apply-prompt";
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
  "Facts",
  "Motivation",
];

export const CAMERA_KEYWORDS = [
  "close_up",
  "wide_shot",
  "medium_shot",
  "full_body",
  "low_angle",
  "high_angle",
  "from_above",
  "top_down",
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
  "soft_light",
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
  "from_above", "top_down", "low_angle", "high_angle", "close_up", "wide_shot", "full_body",
  // Locations
  "library", "cafe", "street", "room", "bedroom", "office", "classroom", "park", "forest", "beach", "city",
  // Time/weather
  "night", "sunset", "sunrise", "rain", "snow",
  // Other
  "background", "lighting", "indoors", "outdoors",
];

/**
 * SD Prompt Token Priority Order (lower = earlier in prompt)
 * Single Source of Truth: backend/services/keywords.py (CATEGORY_PRIORITY)
 * Keep this in sync with the backend /keywords/priority endpoint.
 */
export const TOKEN_PRIORITY: Record<string, number> = {
  // Priority 1: Quality
  "masterpiece": 1, "best_quality": 1, "high_quality": 1, "amazing_quality": 1,
  "detailed": 1, "ultra_detailed": 1, "extremely_detailed": 1,
  "absurdres": 1, "highres": 1, "8k": 1,

  // Priority 2: Subject
  "1girl": 2, "1boy": 2, "2girls": 2, "2boys": 2, "3girls": 2, "3boys": 2,
  "multiple_girls": 2, "multiple_boys": 2,
  "solo": 2, "duo": 2, "trio": 2, "group": 2, "couple": 2,

  // Priority 3: Identity (LoRA triggers)
  // Matched by character identity tags

  // Priority 4: Character appearance (hair, eyes, features)
  // Matched by patterns below (priority 4)

  // Priority 5: Clothing
  // Matched by patterns below (priority 5)

  // Priority 6: Expression
  "smile": 6, "smiling": 6, "happy": 6, "sad": 6, "crying": 6, "angry": 6,
  "surprised": 6, "shocked": 6, "embarrassed": 6, "shy": 6, "blush": 6, "blushing": 6,
  "serious": 6, "determined": 6, "confident": 6, "nervous": 6, "scared": 6,
  "laughing": 6, "grin": 6, "frown": 6, "pout": 6, "expressionless": 6,
  "open_mouth": 6, "closed_mouth": 6, "tongue_out": 6,

  // Priority 7: Gaze
  "looking_at_viewer": 7, "looking_away": 7, "looking_up": 7, "looking_down": 7,
  "looking_to_the_side": 7, "looking_back": 7, "eye_contact": 7,
  "eyes_closed": 7, "closed_eyes": 7, "half_closed_eyes": 7, "wink": 7,

  // Priority 8: Pose (static)
  "standing": 8, "sitting": 8, "kneeling": 8, "crouching": 8, "squatting": 8,
  "lying": 8, "lying_down": 8, "on_back": 8, "on_stomach": 8,
  "leaning": 8, "reclining": 8, "lounging": 8,
  "arms_crossed": 8, "arms_behind_back": 8, "hands_on_hips": 8,
  "hand_on_hip": 8, "hand_up": 8, "peace_sign": 8, "v": 8,

  // Priority 9: Action (dynamic)
  "walking": 9, "running": 9, "jumping": 9, "dancing": 9,
  "reading": 9, "writing": 9, "eating": 9, "drinking": 9,
  "sleeping": 9, "waving": 9, "pointing": 9, "hugging": 9,

  // Priority 10: Camera
  "close_up": 10, "portrait": 10, "bust_shot": 10, "upper_body": 10,
  "cowboy_shot": 10, "full_body": 10, "wide_shot": 10,
  "from_above": 10, "from_below": 10, "from_side": 10, "from_behind": 10,
  "dutch_angle": 10, "low_angle": 10, "high_angle": 10, "pov": 10,

  // Priority 11: Location / Environment / Background
  "indoors": 11, "outdoors": 11,
  "library": 11, "cafe": 11, "street": 11, "room": 11, "bedroom": 11, "office": 11,
  "classroom": 11, "park": 11, "forest": 11, "beach": 11, "city": 11,
  "simple_background": 11, "white_background": 11, "black_background": 11,
  "gradient_background": 11, "blurry_background": 11, "detailed_background": 11,

  // Priority 12: Time / Weather
  "day": 12, "night": 12, "sunset": 12, "sunrise": 12, "dusk": 12, "dawn": 12,
  "sunny": 12, "cloudy": 12, "rainy": 12, "rain": 12, "snowy": 12, "snow": 12,

  // Priority 13: Lighting
  "natural_light": 13, "sunlight": 13, "moonlight": 13,
  "backlighting": 13, "rim_light": 13, "dramatic_lighting": 13,
  "soft_lighting": 13, "neon_lights": 13,

  // Priority 14: Mood
  "romantic": 14, "melancholic": 14, "peaceful": 14, "dramatic": 14,
  "mysterious": 14, "ethereal": 14, "cozy": 14, "lonely": 14,

  // Priority 15: Style
  "anime": 15, "photorealistic": 15, "sketch": 15, "watercolor": 15,
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
 * Category descriptions in Korean for UI display
 * Helps users understand what tags belong in each category
 */
export const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  // Priority 1-2: Meta
  quality: "품질 (masterpiece, best_quality)",
  subject: "대상 (1girl, 1boy, solo)",

  // Priority 3-4: Appearance
  identity: "신원/캐릭터 (LoRA 트리거)",
  hair_color: "머리 색 (blue_hair, blonde)",
  hair_length: "머리 길이 (long/short_hair)",
  hair_style: "헤어스타일 (ponytail, twintails)",
  hair_accessory: "머리 장식 (hairpin, ribbon)",
  eye_color: "눈 색 (blue_eyes, red_eyes)",
  skin_color: "피부 색 (pale_skin)",
  body_feature: "신체 특징 (elf_ears, wings)",
  appearance: "외모 (freckles, makeup, tattoo)",

  // Priority 5-9: Character state
  clothing: "의류/액세서리 (shirt, dress, shoes)",
  expression: "표정 (smile, angry, blush)",
  gaze: "시선 (looking_at_viewer)",
  pose: "정적 자세 (standing, sitting)",
  action: "동적 행동 (running, dancing)",

  // Priority 10-15: Scene
  camera: "카메라/샷 (close_up, full_body)",
  location_indoor: "실내 장소 (classroom, cafe)",
  location_outdoor: "실외 장소 (beach, forest)",
  environment: "소품/가구 (desk, computer, plant)",
  background_type: "배경 타입 (white/simple_bg)",
  time_weather: "시간/날씨 (day, night, rain)",
  lighting: "조명 (sunlight, dramatic)",
  mood: "분위기 (romantic, peaceful)",
  style: "스타일 (anime, realistic)",
};

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
