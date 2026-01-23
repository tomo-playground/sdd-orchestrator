import type { OverlaySettings, PostCardSettings } from "../types";
import { DEFAULT_OVERLAY_SETTINGS, DEFAULT_POST_CARD_SETTINGS } from "../constants";

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
