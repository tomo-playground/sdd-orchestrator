import type { OverlaySettings, PostCardSettings } from "../types";
import {
  DEFAULT_OVERLAY_SETTINGS,
  DEFAULT_POST_CARD_SETTINGS,
  HEART_EMOJIS,
  ASCII_HEARTS,
} from "../constants";

export { computeValidationResults, getFixSuggestions } from "./validation";

/**
 * Slugify a string for use as an avatar key.
 * Converts to lowercase, removes non-ASCII characters, and creates a hash fallback for non-Latin text.
 */
export const slugifyAvatarKey = (value: string): string => {
  const trimmed = value.trim().toLowerCase();
  const ascii = trimmed
    .normalize("NFKD")
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "");
  if (ascii) return ascii;
  // Fallback for non-Latin characters: generate a hash
  let hash = 0;
  for (let i = 0; i < trimmed.length; i += 1) {
    hash = (hash * 31 + trimmed.charCodeAt(i)) >>> 0;
  }
  return `channel-${hash.toString(16).slice(0, 6)}`;
};

/**
 * Normalize overlay settings from potentially malformed data.
 * Handles legacy field names and ensures all required fields are present.
 */
export const normalizeOverlaySettings = (raw: any): OverlaySettings => {
  const channelName = raw?.channel_name ?? raw?.profile_name ?? "";
  const avatarKey = raw?.avatar_key ?? raw?.profile_name ?? slugifyAvatarKey(channelName);
  return {
    ...DEFAULT_OVERLAY_SETTINGS,
    ...(raw || {}),
    channel_name: channelName,
    avatar_key: avatarKey,
  };
};

/**
 * Normalize post card settings from potentially malformed data.
 * Handles legacy field names and ensures all required fields are present.
 */
export const normalizePostCardSettings = (raw: any): PostCardSettings => {
  const channelName = raw?.channel_name ?? raw?.profile_name ?? "";
  const avatarKey = raw?.avatar_key ?? raw?.profile_name ?? slugifyAvatarKey(channelName);
  return {
    ...DEFAULT_POST_CARD_SETTINGS,
    ...(raw || {}),
    channel_name: channelName,
    avatar_key: avatarKey,
  };
};

/**
 * Get the first character of a name as an uppercase initial for avatar display.
 */
export const getAvatarInitial = (name: string): string => {
  const trimmed = name.trim();
  return (trimmed[0] || "A").toUpperCase();
};

/**
 * Split a comma-separated prompt string into individual tokens.
 */
export const splitPromptTokens = (text: string): string[] =>
  text
    .split(",")
    .map((token) => token.trim())
    .filter(Boolean);

/**
 * Merge and deduplicate prompt tokens.
 * Handles special cases for LoRA and model tags (only one of each type).
 */
export const mergePromptTokens = (
  baseTokens: string[],
  sceneTokens: string[]
): string[] => {
  const merged: string[] = [];
  const seen = new Set<string>();
  const loraSeen = new Set<string>();
  const modelSeen = new Set<string>();

  const pushToken = (token: string) => {
    const lower = token.toLowerCase();
    if (lower.startsWith("<lora:")) {
      if (loraSeen.has(lower)) return;
      loraSeen.add(lower);
    }
    if (lower.startsWith("<model:")) {
      if (modelSeen.has(lower)) return;
      modelSeen.add(lower);
    }
    if (seen.has(lower)) return;
    seen.add(lower);
    merged.push(token);
  };

  baseTokens.forEach(pushToken);
  sceneTokens.forEach(pushToken);
  return merged;
};

/**
 * Deduplicate tokens in a comma-separated string.
 */
export const deduplicatePromptTokens = (combined: string): string => {
  const tokens = splitPromptTokens(combined);
  const seen = new Set<string>();
  const merged: string[] = [];
  for (const token of tokens) {
    const lower = token.toLowerCase();
    if (seen.has(lower)) continue;
    seen.add(lower);
    merged.push(token);
  }
  return merged.join(", ");
};

/**
 * Strip leading heart emojis from text.
 */
export const stripLeadingHearts = (text: string): string => {
  let result = text.trimStart();
  let updated = true;
  while (updated) {
    updated = false;
    for (const heart of HEART_EMOJIS) {
      if (result.startsWith(heart)) {
        result = result.slice(heart.length).trimStart();
        updated = true;
      }
    }
  }
  return result;
};

/**
 * Add a random heart emoji prefix to text.
 */
export const applyHeartPrefix = (text: string): string => {
  const cleaned = stripLeadingHearts(text);
  const hearts = Array.from({ length: 3 }, () => {
    const idx = Math.floor(Math.random() * ASCII_HEARTS.length);
    return ASCII_HEARTS[idx];
  }).join("");
  if (!cleaned) return hearts;
  return `${hearts} ${cleaned}`;
};

/**
 * Generate a channel name from seed text using Korean adjective/noun combinations.
 */
export const generateChannelName = (seedText: string): string => {
  const adjectives = [
    "잔잔한", "빛나는", "조용한", "따뜻한", "느린",
    "고요한", "푸른", "은은한", "깊은", "희미한",
    "아련한", "눈부신", "부드러운", "차분한", "맑은",
    "희미한", "조심스런", "여린", "섬세한", "포근한", "잔잔한",
  ];
  const nouns = [
    "하늘", "밤", "바람", "별빛", "파도",
    "기억", "노을", "꿈", "길", "숲",
    "빛", "여운", "달", "안개", "새벽",
    "기척", "울림", "정원", "호수", "온기", "숨결", "편지",
  ];
  const base = seedText.trim() || "shorts";
  let hash = 0;
  for (let i = 0; i < base.length; i += 1) {
    hash = (hash * 31 + base.charCodeAt(i)) >>> 0;
  }
  const adjective = adjectives[hash % adjectives.length];
  const noun = nouns[Math.floor(hash / adjectives.length) % nouns.length];
  return `${adjective} ${noun}`;
};
