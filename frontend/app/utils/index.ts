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

// Gender enhancement tags to overcome SD model bias
// Male characters need reinforcement due to training data imbalance
// Reviewed by prompt engineer - using Danbooru standard tags only
const MALE_ENHANCEMENT_POSITIVE = [
  "(1boy:1.3)",
  "(male_focus:1.2)",
  "(bishounen:1.1)",
];

const MALE_ENHANCEMENT_NEGATIVE = [
  "1girl",
  "multiple_girls",
  "breasts",
  "large_breasts",
  "cleavage",
  "female_focus",
];

/**
 * Detect gender from prompt tokens.
 * Returns 'male', 'female', or null if undetermined.
 */
export const detectGenderFromTokens = (tokens: string[]): "male" | "female" | null => {
  const lowerTokens = tokens.map((t) => t.toLowerCase().trim());

  const maleIndicators = ["1boy", "2boys", "3boys", "male", "man", "boy"];
  const femaleIndicators = ["1girl", "2girls", "3girls", "female", "woman", "girl"];

  const hasMale = maleIndicators.some((m) => lowerTokens.includes(m));
  const hasFemale = femaleIndicators.some((f) => lowerTokens.includes(f));

  if (hasMale && !hasFemale) return "male";
  if (hasFemale && !hasMale) return "female";
  return null;
};

/**
 * Get gender-based prompt enhancements to overcome SD model bias.
 */
export const getGenderEnhancements = (
  tokens: string[]
): { positive: string[]; negative: string[] } => {
  const gender = detectGenderFromTokens(tokens);

  if (gender === "male") {
    return {
      positive: MALE_ENHANCEMENT_POSITIVE,
      negative: MALE_ENHANCEMENT_NEGATIVE,
    };
  }

  // No enhancement needed for female (model already biased towards female)
  return { positive: [], negative: [] };
};

// Camera tags that are risky (head cutoff risk)
// Maps risky camera to safer alternative
// These are unconditionally replaced regardless of pose
const UNSAFE_CAMERA_REPLACEMENTS: Record<string, string> = {
  "medium shot": "cowboy shot",  // medium shot has unclear definition, cowboy shot is well-defined
  "close-up": "portrait",        // close-up is ambiguous in SD, portrait explicitly includes face
  "close up": "portrait",        // alternative spelling
};

// Actions that raise hands/arms above shoulder level (often causes head cutoff)
const HIGH_ARM_ACTIONS = [
  "thumbs up", "thumbs_up",
  "hand up", "hand_up", "hands up", "hands_up",
  "arms up", "arms_up",
  "waving", "wave",
  "peace sign", "v",
  "salute", "saluting",
];

/**
 * Fix camera-action conflicts that often cause head cutoff in generated images.
 *
 * Fixes applied:
 * 1. Replace unsafe camera tags (medium shot → cowboy shot, close-up → portrait)
 * 2. Add "face in frame" when using cowboy shot with high-arm actions
 * 3. Replace thumbs up → peace sign (face-level gesture is safer)
 */
export const fixCameraPoseConflicts = (tokens: string[]): string[] => {
  const result = [...tokens];
  const lowerTokens = result.map((t) => t.toLowerCase().trim());

  // Step 1: Replace unsafe camera tags
  for (let i = 0; i < result.length; i++) {
    const lower = result[i].toLowerCase().trim();
    if (UNSAFE_CAMERA_REPLACEMENTS[lower]) {
      console.log(`[fixCameraPoseConflicts] Replacing "${result[i]}" → "${UNSAFE_CAMERA_REPLACEMENTS[lower]}"`);
      result[i] = UNSAFE_CAMERA_REPLACEMENTS[lower];
    }
  }

  // Step 2: Detect high-arm actions
  const hasHighArmAction = HIGH_ARM_ACTIONS.some((action) => lowerTokens.includes(action));
  const hasCowboyShot = lowerTokens.includes("cowboy shot");

  // Step 3: Add "face in frame" if cowboy shot + high-arm action
  if (hasCowboyShot && hasHighArmAction) {
    console.log(`[fixCameraPoseConflicts] High-arm action detected with cowboy shot, adding "face in frame"`);
    result.push("face in frame");
  }

  // Step 4: Replace "thumbs up" with "peace sign" (safer for framing)
  for (let i = 0; i < result.length; i++) {
    const lower = result[i].toLowerCase().trim();
    if (lower === "thumbs up" || lower === "thumbs_up") {
      console.log(`[fixCameraPoseConflicts] Replacing "${result[i]}" → "peace sign" (safer gesture)`);
      result[i] = "peace sign";
    }
  }

  return result;
};

// Conflicting tag groups - only one from each group should be used
// Base prompt takes priority over scene prompt
const CONFLICTING_TAG_GROUPS = [
  ["1girl", "1boy", "1other"],
  ["2girls", "2boys"],
  ["3girls", "3boys"],
  ["female", "male"],
  ["woman", "man"],
  ["girl", "boy"],
];

/**
 * Merge and deduplicate prompt tokens.
 * Handles special cases for LoRA and model tags (only one of each type).
 * Also handles conflicting tags (e.g., 1girl vs 1boy) - base prompt takes priority.
 */
export const mergePromptTokens = (
  baseTokens: string[],
  sceneTokens: string[]
): string[] => {
  const merged: string[] = [];
  const seen = new Set<string>();
  const loraSeen = new Set<string>();
  const modelSeen = new Set<string>();

  // Build a set of tags to exclude from scene tokens based on base tokens
  const baseTokenLowers = new Set(
    baseTokens
      .filter((t) => typeof t === "string")
      .map((t) => t.toLowerCase().trim())
  );
  const excludeFromScene = new Set<string>();

  for (const group of CONFLICTING_TAG_GROUPS) {
    const baseHasConflict = group.some((tag) => baseTokenLowers.has(tag));
    if (baseHasConflict) {
      // Exclude all other tags in this group from scene tokens
      for (const tag of group) {
        if (!baseTokenLowers.has(tag)) {
          excludeFromScene.add(tag);
        }
      }
    }
  }

  const pushToken = (token: unknown, isScene: boolean = false) => {
    // Guard: skip non-string values
    if (typeof token !== "string" || !token.trim()) return;
    const lower = token.toLowerCase().trim();

    // Skip conflicting tags from scene tokens
    if (isScene && excludeFromScene.has(lower)) {
      console.log(`[mergePromptTokens] Filtered conflicting tag: ${token}`);
      return;
    }

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

  baseTokens.forEach((t) => pushToken(t, false));
  sceneTokens.forEach((t) => pushToken(t, true));
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
    if (typeof token !== "string" || !token.trim()) continue;
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
