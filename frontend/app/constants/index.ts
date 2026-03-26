import type { OverlaySettings, PostCardSettings } from "../types";

export const API_ROOT = "";
export const API_BASE = "/api/v1";
export const ADMIN_API_BASE = "/api/admin";

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
export const DEFAULT_STRUCTURE = "monologue";

// Backend SSOT fallback: /presets API image_defaults (config.py SD_DEFAULT_WIDTH/HEIGHT)
export const DEFAULT_IMAGE_WIDTH = 832;
export const DEFAULT_IMAGE_HEIGHT = 1216;
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

/**
 * 파이프라인 실행 단계 (Frontend 유지 정당성: SP-074)
 * - step ID에 AutoRunStepId 타입 + autopilot 로직이 강결합
 * - 단계 변경 = 아키텍처 변경이므로 동적 로드 불필요
 * - Backend 대응: services/agent/nodes/ 노드 구조
 */
export const AUTO_RUN_STEPS = [
  { id: "stage", label: "준비" },
  { id: "images", label: "이미지" },
  { id: "tts", label: "TTS" },
  { id: "render", label: "렌더" },
] as const;

/** AutoRun 이미지 생성 시 동시 실행 제한 (서버 과부하 방지) */
export const AUTORUN_CONCURRENCY = 2;

export const HEART_EMOJIS = ["❤", "💖", "💗", "💘", "💜", "💙", "💚", "🧡", "🤍"];
export const ASCII_HEARTS = ["<3", "**", "^^", "<<>>"];
