import { describe, it, expect } from "vitest";
import { findDuplicateTokens } from "../promptDuplicateCheck";

describe("findDuplicateTokens", () => {
  it("returns empty for empty prompt", () => {
    expect(findDuplicateTokens("", ["brown_hair"])).toEqual([]);
    expect(findDuplicateTokens("  ", ["brown_hair"])).toEqual([]);
  });

  it("returns empty for empty tag list", () => {
    expect(findDuplicateTokens("brown hair, long hair", [])).toEqual([]);
  });

  it("detects exact match (space form in prompt, underscore in tags)", () => {
    const result = findDuplicateTokens("brown hair, long hair", [
      "brown_hair",
      "blue_eyes",
    ]);
    expect(result).toEqual(["brown_hair"]);
  });

  it("detects exact match (underscore form in prompt)", () => {
    const result = findDuplicateTokens("brown_hair, long_hair", [
      "brown_hair",
      "long_hair",
    ]);
    expect(result).toEqual(["brown_hair", "long_hair"]);
  });

  it("is case-insensitive", () => {
    const result = findDuplicateTokens("Brown Hair", ["brown_hair"]);
    expect(result).toEqual(["brown_hair"]);
  });

  it("does not duplicate when same token appears twice in prompt", () => {
    const result = findDuplicateTokens("brown hair, brown hair", [
      "brown_hair",
    ]);
    expect(result).toEqual(["brown_hair"]);
  });

  it("returns original tag name (underscore form)", () => {
    const result = findDuplicateTokens("school uniform", [
      "school_uniform",
    ]);
    expect(result).toEqual(["school_uniform"]);
  });

  it("handles whitespace around tokens", () => {
    const result = findDuplicateTokens("  brown hair , long hair ", [
      "brown_hair",
    ]);
    expect(result).toEqual(["brown_hair"]);
  });

  it("returns empty when no overlap", () => {
    const result = findDuplicateTokens("masterpiece, best quality", [
      "brown_hair",
      "blue_eyes",
    ]);
    expect(result).toEqual([]);
  });
});
