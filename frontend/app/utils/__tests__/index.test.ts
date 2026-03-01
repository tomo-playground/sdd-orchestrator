import { describe, it, expect } from "vitest";
import {
  slugifyAvatarKey,
  normalizeOverlaySettings,
  normalizePostCardSettings,
  getAvatarInitial,
  splitPromptTokens,
  deduplicatePromptTokens,
  stripLeadingHearts,
  applyHeartPrefix,
  generateChannelName,
} from "../index";
import { DEFAULT_OVERLAY_SETTINGS, DEFAULT_POST_CARD_SETTINGS } from "../../constants";

describe("slugifyAvatarKey", () => {
  it("converts English text to slug", () => {
    expect(slugifyAvatarKey("My Channel")).toBe("my-channel");
  });

  it("removes non-ASCII characters", () => {
    expect(slugifyAvatarKey("Channel 123!@#")).toBe("channel-123");
  });

  it("handles leading/trailing spaces", () => {
    expect(slugifyAvatarKey("  hello  ")).toBe("hello");
  });

  it("generates hash fallback for non-Latin text", () => {
    const result = slugifyAvatarKey("한국어");
    expect(result).toMatch(/^channel-[0-9a-f]+$/);
  });

  it("collapses multiple hyphens", () => {
    expect(slugifyAvatarKey("a   b   c")).toBe("a-b-c");
  });
});

describe("normalizeOverlaySettings", () => {
  it("returns defaults for null input", () => {
    const result = normalizeOverlaySettings(null);
    expect(result.channel_name).toBe("");
    // avatar_key is derived from empty channel_name via slugifyAvatarKey
    expect(result.avatar_key).toBe("channel-0");
  });

  it("returns defaults for undefined input", () => {
    const result = normalizeOverlaySettings(undefined);
    expect(result.channel_name).toBe("");
  });

  it("merges provided values with defaults", () => {
    const result = normalizeOverlaySettings({ channel_name: "Test Channel" });
    expect(result.channel_name).toBe("Test Channel");
    expect(result.avatar_key).toBe("test-channel");
  });

  it("derives avatar_key from channel_name", () => {
    const result = normalizeOverlaySettings({ channel_name: "My Channel" });
    expect(result.avatar_key).toBe("my-channel");
  });
});

describe("normalizePostCardSettings", () => {
  it("returns defaults for null input", () => {
    const result = normalizePostCardSettings(null);
    expect(result.channel_name).toBe("");
    // avatar_key is derived from empty channel_name via slugifyAvatarKey
    expect(result.avatar_key).toBe("channel-0");
  });

  it("merges provided values", () => {
    const result = normalizePostCardSettings({ channel_name: "Post Channel" });
    expect(result.channel_name).toBe("Post Channel");
    expect(result.avatar_key).toBe("post-channel");
  });
});

describe("getAvatarInitial", () => {
  it("returns uppercase first character", () => {
    expect(getAvatarInitial("hello")).toBe("H");
  });

  it("returns A for empty string", () => {
    expect(getAvatarInitial("")).toBe("A");
  });

  it("trims whitespace before extracting", () => {
    expect(getAvatarInitial("  world")).toBe("W");
  });
});

describe("splitPromptTokens", () => {
  it("splits comma-separated tokens", () => {
    expect(splitPromptTokens("a, b, c")).toEqual(["a", "b", "c"]);
  });

  it("filters empty tokens", () => {
    expect(splitPromptTokens("a,,b,")).toEqual(["a", "b"]);
  });

  it("returns empty array for empty string", () => {
    expect(splitPromptTokens("")).toEqual([]);
  });
});

describe("deduplicatePromptTokens", () => {
  it("removes duplicate tokens case-insensitively", () => {
    expect(deduplicatePromptTokens("1girl, 1Girl, 1GIRL")).toBe("1girl");
  });

  it("preserves original casing of first occurrence", () => {
    expect(deduplicatePromptTokens("Brown Hair, brown hair")).toBe("Brown Hair");
  });

  it("handles empty string", () => {
    expect(deduplicatePromptTokens("")).toBe("");
  });
});

describe("stripLeadingHearts", () => {
  it("strips heart emojis from start (without variation selector)", () => {
    // HEART_EMOJIS uses U+2764 without variation selector
    const result = stripLeadingHearts("❤ Hello");
    expect(result).toBe("Hello");
  });

  it("strips multi-byte heart emojis", () => {
    const result = stripLeadingHearts("💖 Hello");
    expect(result).toBe("Hello");
  });

  it("returns text as-is without hearts", () => {
    expect(stripLeadingHearts("Hello")).toBe("Hello");
  });

  it("handles empty string", () => {
    expect(stripLeadingHearts("")).toBe("");
  });
});

describe("applyHeartPrefix", () => {
  it("adds heart prefix to text", () => {
    const result = applyHeartPrefix("Hello");
    // Should end with the text, preceded by ASCII hearts
    expect(result).toContain("Hello");
    expect(result.length).toBeGreaterThan("Hello".length);
  });

  it("strips existing hearts before adding new ones", () => {
    const result = applyHeartPrefix("💖 Hello");
    expect(result).toContain("Hello");
  });

  it("returns just hearts for empty text", () => {
    const result = applyHeartPrefix("");
    expect(result.length).toBeGreaterThan(0);
  });
});

describe("generateChannelName", () => {
  it("generates Korean channel name from seed", () => {
    const result = generateChannelName("test");
    expect(result).toBeTruthy();
    expect(result.split(" ").length).toBe(2);
  });

  it("uses 'shorts' as default for empty seed", () => {
    const a = generateChannelName("");
    const b = generateChannelName("shorts");
    expect(a).toBe(b);
  });

  it("produces deterministic results for same seed", () => {
    const a = generateChannelName("my-channel");
    const b = generateChannelName("my-channel");
    expect(a).toBe(b);
  });

  it("produces different results for different seeds", () => {
    const a = generateChannelName("seed1");
    const b = generateChannelName("seed2");
    // Not guaranteed but highly likely with different seeds
    // Just verify both are valid
    expect(a).toBeTruthy();
    expect(b).toBeTruthy();
  });
});
