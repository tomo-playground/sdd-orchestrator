import { describe, it, expect } from "vitest";
import { isMultiCharStructure } from "../structure";

describe("isMultiCharStructure", () => {
  it("returns true for normalized dialogue/narrated_dialogue", () => {
    expect(isMultiCharStructure("dialogue")).toBe(true);
    expect(isMultiCharStructure("narrated_dialogue")).toBe(true);
  });

  it("returns false for non-normalized Title Case inputs (strict comparison)", () => {
    expect(isMultiCharStructure("Dialogue")).toBe(false);
    expect(isMultiCharStructure("DIALOGUE")).toBe(false);
    expect(isMultiCharStructure("Narrated Dialogue")).toBe(false);
    expect(isMultiCharStructure("narrated dialogue")).toBe(false);
  });

  it("returns false for monologue", () => {
    expect(isMultiCharStructure("monologue")).toBe(false);
    expect(isMultiCharStructure("Monologue")).toBe(false);
  });

  it("returns false for Narration", () => {
    expect(isMultiCharStructure("Narration")).toBe(false);
  });

  it("returns false for empty string", () => {
    expect(isMultiCharStructure("")).toBe(false);
  });
});
