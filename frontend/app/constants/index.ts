import type { OverlaySettings, PostCardSettings } from "../types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const DEFAULT_BGM = "kawaii-dance-upbeat-japan-anime-edm-242104.mp3";
export const DEFAULT_SCENE_TEXT_FONT = "온글잎 박다현체.ttf";
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

export const OVERLAY_STYLES = [
  { id: "overlay_minimal.png", label: "Minimal" },
];

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
 * @deprecated Use backend sorting instead
 */
export const getTokenPriority = (token: string): number => {
  return 10.5;
};

