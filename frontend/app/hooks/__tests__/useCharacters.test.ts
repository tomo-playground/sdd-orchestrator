import { describe, it, expect } from "vitest";
import type { CharacterFull } from "../../types";

/**
 * Extract buildCharacterPrompt logic for pure-function testing.
 * Mirrors the implementation in useCharacters.ts.
 */
function buildCharacterPrompt(character: CharacterFull): string {
  const parts: string[] = [];

  if (character.tags?.length) {
    for (const tag of character.tags) {
      if (!tag.name) continue;
      if (tag.weight !== 1.0) {
        parts.push(`(${tag.name}:${tag.weight})`);
      } else {
        parts.push(tag.name);
      }
    }
  }

  if (character.custom_base_prompt) {
    const existing = new Set(parts.map((p) => p.replace(/[():\d.]/g, "").toLowerCase()));
    const custom = character.custom_base_prompt.split(",").map((t) => t.trim()).filter(Boolean);
    for (const token of custom) {
      const norm = token.replace(/[():\d.]/g, "").toLowerCase();
      if (!existing.has(norm)) {
        parts.push(token);
      }
    }
  }

  return parts.join(", ");
}

function buildCharacterNegative(character: CharacterFull): string {
  return character.custom_negative_prompt || "";
}

const BASE_CHARACTER: CharacterFull = {
  id: 1,
  name: "Test Character",
  description: null,
  gender: "male",
  tags: [],
  identity_tags: [],
  clothing_tags: [],
  loras: [],
  recommended_negative: [],
  custom_base_prompt: null,
  custom_negative_prompt: null,
  preview_image_url: null,
  prompt_mode: "auto",
  ip_adapter_weight: null,
  ip_adapter_model: null,
  effective_mode: "standard",
};

describe("buildCharacterPrompt", () => {
  it("returns empty string when no tags and no custom_base_prompt", () => {
    const result = buildCharacterPrompt(BASE_CHARACTER);
    expect(result).toBe("");
  });

  it("includes identity tags from character.tags", () => {
    const char: CharacterFull = {
      ...BASE_CHARACTER,
      tags: [
        { tag_id: 1, name: "solo", weight: 1.0, is_permanent: true },
        { tag_id: 2, name: "1boy", weight: 1.0, is_permanent: true },
      ],
    };
    const result = buildCharacterPrompt(char);
    expect(result).toBe("solo, 1boy");
  });

  it("includes clothing tags from character.tags", () => {
    const char: CharacterFull = {
      ...BASE_CHARACTER,
      tags: [
        { tag_id: 1, name: "solo", layer: 1, weight: 1.0, is_permanent: true },
        { tag_id: 2, name: "blue_shirt", layer: 5, weight: 1.0, is_permanent: true },
        { tag_id: 3, name: "black_pants", layer: 5, weight: 1.0, is_permanent: true },
      ],
    };
    const result = buildCharacterPrompt(char);
    expect(result).toContain("solo");
    expect(result).toContain("blue_shirt");
    expect(result).toContain("black_pants");
  });

  it("formats weighted tags with parentheses", () => {
    const char: CharacterFull = {
      ...BASE_CHARACTER,
      tags: [
        { tag_id: 1, name: "brown_hair", weight: 1.2, is_permanent: true },
        { tag_id: 2, name: "blue_eyes", weight: 0.8, is_permanent: true },
      ],
    };
    const result = buildCharacterPrompt(char);
    expect(result).toBe("(brown_hair:1.2), (blue_eyes:0.8)");
  });

  it("skips tags with empty name", () => {
    const char: CharacterFull = {
      ...BASE_CHARACTER,
      tags: [
        { tag_id: 1, name: "solo", weight: 1.0, is_permanent: true },
        { tag_id: 2, name: "", weight: 1.0, is_permanent: true },
        { tag_id: 3, name: "1boy", weight: 1.0, is_permanent: true },
      ],
    };
    const result = buildCharacterPrompt(char);
    expect(result).toBe("solo, 1boy");
  });

  it("appends custom_base_prompt tokens", () => {
    const char: CharacterFull = {
      ...BASE_CHARACTER,
      tags: [
        { tag_id: 1, name: "solo", weight: 1.0, is_permanent: true },
      ],
      custom_base_prompt: "anime_style, flat color",
    };
    const result = buildCharacterPrompt(char);
    expect(result).toBe("solo, anime_style, flat color");
  });

  it("deduplicates custom_base_prompt tokens that overlap with tags", () => {
    const char: CharacterFull = {
      ...BASE_CHARACTER,
      tags: [
        { tag_id: 1, name: "solo", weight: 1.0, is_permanent: true },
        { tag_id: 2, name: "1boy", weight: 1.0, is_permanent: true },
        { tag_id: 3, name: "blue_shirt", weight: 1.0, is_permanent: true },
      ],
      custom_base_prompt: "solo, blue_shirt, extra_tag",
    };
    const result = buildCharacterPrompt(char);
    expect(result).toBe("solo, 1boy, blue_shirt, extra_tag");
  });

  it("works with only custom_base_prompt (no tags)", () => {
    const char: CharacterFull = {
      ...BASE_CHARACTER,
      tags: [],
      custom_base_prompt: "1girl, white_dress",
    };
    const result = buildCharacterPrompt(char);
    expect(result).toBe("1girl, white_dress");
  });

  it("matches Flat Color Boy scenario (tags + empty custom_base_prompt)", () => {
    const char: CharacterFull = {
      ...BASE_CHARACTER,
      name: "Flat Color Boy",
      tags: [
        { tag_id: 6, name: "solo", layer: 1, weight: 1.0, is_permanent: true },
        { tag_id: 29, name: "1boy", layer: 1, weight: 1.0, is_permanent: true },
        { tag_id: 9102, name: "anime_style", layer: 0, weight: 1.0, is_permanent: true },
        { tag_id: 561, name: "blue_shirt", layer: 5, weight: 1.0, is_permanent: true },
      ],
      custom_base_prompt: "",
    };
    const result = buildCharacterPrompt(char);
    expect(result).toBe("solo, 1boy, anime_style, blue_shirt");
  });

  it("handles mixed weight tags", () => {
    const char: CharacterFull = {
      ...BASE_CHARACTER,
      tags: [
        { tag_id: 1, name: "solo", weight: 1.0, is_permanent: true },
        { tag_id: 2, name: "red_hair", weight: 1.3, is_permanent: true },
        { tag_id: 3, name: "school_uniform", weight: 1.0, is_permanent: true },
        { tag_id: 4, name: "smile", weight: 0.7, is_permanent: true },
      ],
    };
    const result = buildCharacterPrompt(char);
    expect(result).toBe("solo, (red_hair:1.3), school_uniform, (smile:0.7)");
  });

  it("handles undefined tags gracefully", () => {
    const char: CharacterFull = {
      ...BASE_CHARACTER,
      tags: undefined as unknown as CharacterFull["tags"],
    };
    const result = buildCharacterPrompt(char);
    expect(result).toBe("");
  });
});

describe("buildCharacterNegative", () => {
  it("returns custom_negative_prompt", () => {
    const char: CharacterFull = {
      ...BASE_CHARACTER,
      custom_negative_prompt: "easynegative, lowres",
    };
    expect(buildCharacterNegative(char)).toBe("easynegative, lowres");
  });

  it("returns empty string when null", () => {
    expect(buildCharacterNegative(BASE_CHARACTER)).toBe("");
  });
});
