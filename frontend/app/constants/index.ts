import type { OverlaySettings, PostCardSettings } from "../types";

export const API_ROOT = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const API_BASE = `${API_ROOT}/api/v1`;
export const ADMIN_API_BASE = `${API_ROOT}/api/admin`;

// API Timeout settings (milliseconds)
export const API_TIMEOUT = {
  DEFAULT: 60_000, // 60 seconds
  STORYBOARD_SAVE: 120_000, // 2 minutes (large scene data)
  VIDEO_RENDER: 1200_000, // 20 minutes (video processing)
  IMAGE_GENERATION: 300_000, // 5 minutes (SD image generation, Hi-Res may exceed 3min)
  STAGE_GENERATE: 300_000, // 5 minutes (multiple SD background generations)
} as const;

export const Z_INDEX = {
  PREVIEW: 100,
  MODAL: 1000,
  MODAL_CLOSE: 1010,
  NESTED_MODAL: 1100,
  TOAST: 2000,
} as const;

/** Sentinel value: "All Groups" selected (skip group_id filter in API calls) */
export const ALL_GROUPS_ID = -1;

export const DEFAULT_BGM = "kawaii-dance-upbeat-japan-anime-edm-242104.mp3";
export const DEFAULT_SCENE_TEXT_FONT = "온글잎 박다현체.ttf";
export const DEFAULT_STRUCTURE = "Monologue";
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
  { id: "stage", label: "Stage" },
  { id: "images", label: "Images" },
  { id: "render", label: "Render" },
] as const;

export const SAMPLERS = ["Euler", "Euler a", "DPM++ 2M Karras", "DDIM"];

export const OVERLAY_STYLES = [{ id: "overlay_minimal.png", label: "Minimal" }];

export const HEART_EMOJIS = ["❤", "💖", "💗", "💘", "💜", "💙", "💚", "🧡", "🤍"];
export const ASCII_HEARTS = ["<3", "**", "^^", "<<>>"];

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

/** TTS engine identifier. 값 변경 시 backend의 tts_engine 파라미터와 동기화 필요. */
export const TTS_ENGINE = "qwen" as const;
