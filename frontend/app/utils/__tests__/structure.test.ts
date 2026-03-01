import { describe, it, expect } from "vitest";
import { isMultiCharStructure } from "../structure";

describe("isMultiCharStructure", () => {
  it("returns true for Dialogue", () => {
    expect(isMultiCharStructure("Dialogue")).toBe(true);
  });

  it("returns true for Narrated Dialogue", () => {
    expect(isMultiCharStructure("Narrated Dialogue")).toBe(true);
  });

  it("returns false for Monologue", () => {
    expect(isMultiCharStructure("Monologue")).toBe(false);
  });

  it("returns false for Narration", () => {
    expect(isMultiCharStructure("Narration")).toBe(false);
  });

  it("returns false for empty string", () => {
    expect(isMultiCharStructure("")).toBe(false);
  });
});
