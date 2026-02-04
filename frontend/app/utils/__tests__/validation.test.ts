import { describe, it, expect } from "vitest";
import { computeValidationResults, getFixSuggestions } from "../validation";
import type { Scene } from "../../types";

// Helper to create a valid base scene
const createScene = (overrides: Partial<Scene> = {}): Scene => ({
  id: 1,
  order: 0,
  script: "Test script",
  speaker: "A",
  duration: 5,
  image_prompt: "1girl, standing, full body, library, soft light",
  image_prompt_ko: "테스트",
  image_url: null,
  negative_prompt: "bad quality",
  isGenerating: false,
  debug_payload: "",
  ...overrides,
});

describe("computeValidationResults", () => {
  describe("Script Validation", () => {
    it("should pass for valid script", () => {
      const scenes = [createScene({ script: "Hello world" })];
      const { results } = computeValidationResults(scenes);

      expect(results[1].status).toBe("ok");
      expect(results[1].issues).toHaveLength(0);
    });

    it("should error on empty script", () => {
      const scenes = [createScene({ script: "" })];
      const { results } = computeValidationResults(scenes);

      expect(results[1].status).toBe("error");
      expect(results[1].issues).toContainEqual({
        level: "error",
        message: "Script is empty.",
      });
    });

    it("should warn on long script (>40 chars)", () => {
      const scenes = [
        createScene({ script: "This is a very long script that exceeds 40 characters" }),
      ];
      const { results } = computeValidationResults(scenes);

      expect(results[1].status).toBe("warn");
      expect(results[1].issues).toContainEqual({
        level: "warn",
        message: "Script is longer than 40 characters.",
      });
    });
  });

  describe("Speaker Validation", () => {
    it("should pass for Speaker A", () => {
      const scenes = [createScene({ speaker: "A" })];
      const { results } = computeValidationResults(scenes);

      expect(results[1].status).toBe("ok");
    });

    it("should error for non-A speaker", () => {
      const scenes = [createScene({ speaker: "Narrator" })];
      const { results } = computeValidationResults(scenes);

      expect(results[1].status).toBe("error");
      expect(results[1].issues).toContainEqual({
        level: "error",
        message: "Speaker must be Actor A (monologue).",
      });
    });
  });

  describe("Prompt Validation", () => {
    it("should error on empty prompt", () => {
      const scenes = [createScene({ image_prompt: "" })];
      const { results } = computeValidationResults(scenes);

      expect(results[1].status).toBe("error");
      expect(results[1].issues).toContainEqual({
        level: "error",
        message: "Positive Prompt is empty.",
      });
    });

    it("should warn on short prompt (<5 tokens)", () => {
      const scenes = [createScene({ image_prompt: "1girl, smile" })];
      const { results } = computeValidationResults(scenes);

      expect(results[1].status).toBe("warn");
      expect(results[1].issues).toContainEqual({
        level: "warn",
        message: "Prompt is too short; add more visual details.",
      });
    });

    it("should warn on missing camera keywords", () => {
      const scenes = [
        createScene({
          image_prompt: "1girl, smile, happy, cheerful, cute",
        }),
      ];
      const { results } = computeValidationResults(scenes);

      expect(results[1].issues).toContainEqual({
        level: "warn",
        message: "Missing camera/shot keywords.",
      });
    });

    it("should warn on missing action keywords", () => {
      const scenes = [
        createScene({
          image_prompt: "1girl, full body, library, soft light, smile",
        }),
      ];
      const { results } = computeValidationResults(scenes);

      expect(results[1].issues).toContainEqual({
        level: "warn",
        message: "Missing action/pose keywords.",
      });
    });

    it("should warn on missing background keywords", () => {
      const scenes = [
        createScene({
          image_prompt: "1girl, standing, full body, soft light, smile",
        }),
      ];
      const { results } = computeValidationResults(scenes);

      expect(results[1].issues).toContainEqual({
        level: "warn",
        message: "Missing background/setting keywords.",
      });
    });

    it("should warn on missing lighting keywords", () => {
      const scenes = [
        createScene({
          image_prompt: "1girl, standing, full body, library, smile",
        }),
      ];
      const { results } = computeValidationResults(scenes);

      expect(results[1].issues).toContainEqual({
        level: "warn",
        message: "Missing lighting/mood keywords.",
      });
    });

    it("should pass with complete prompt", () => {
      const scenes = [
        createScene({
          image_prompt: "1girl, standing, full body, library, soft light, smile, happy",
        }),
      ];
      const { results } = computeValidationResults(scenes);

      expect(results[1].status).toBe("ok");
      expect(results[1].issues).toHaveLength(0);
    });

    it("should pass with LoRA trigger words (space format exception)", () => {
      // LoRA triggers are NOT normalized to underscores (Civitai original format)
      const scenes = [
        createScene({
          image_prompt: "flat color, chibi, standing, full body, library, soft light",
        }),
      ];
      const { results } = computeValidationResults(scenes);

      // Should pass: "flat color" is a LoRA trigger, not a Danbooru tag
      // Validation checks CAMERA/ACTION/BACKGROUND/LIGHTING keywords only
      expect(results[1].status).toBe("ok");
      expect(results[1].issues).toHaveLength(0);
    });

    it("should pass with character trigger words (underscore format)", () => {
      // Character LoRA triggers may use underscores (e.g., Midoriya_Izuku)
      const scenes = [
        createScene({
          image_prompt: "Midoriya_Izuku, standing, full body, library, soft light",
        }),
      ];
      const { results } = computeValidationResults(scenes);

      expect(results[1].status).toBe("ok");
      expect(results[1].issues).toHaveLength(0);
    });
  });

  describe("Negative Prompt Validation", () => {
    it("should warn if negative contains scene keywords", () => {
      const scenes = [
        createScene({
          negative_prompt: "library, standing, bad quality",
        }),
      ];
      const { results } = computeValidationResults(scenes);

      expect(results[1].status).toBe("warn");
      expect(results[1].issues).toContainEqual({
        level: "warn",
        message: "Negative Prompt contains scene keywords.",
      });
    });

    it("should pass if negative only has quality keywords", () => {
      const scenes = [
        createScene({
          negative_prompt: "bad quality, low quality, worst quality",
        }),
      ];
      const { results } = computeValidationResults(scenes);

      expect(results[1].status).toBe("ok");
    });
  });

  describe("Summary Counts", () => {
    it("should count ok/warn/error correctly", () => {
      const scenes = [
        createScene({ id: 1, script: "OK scene" }),
        createScene({
          id: 2,
          script: "This is a very long script that exceeds 40 characters limit",
        }),
        createScene({ id: 3, script: "" }),
      ];
      const { summary } = computeValidationResults(scenes);

      expect(summary.ok).toBe(1);
      expect(summary.warn).toBe(1);
      expect(summary.error).toBe(1);
    });

    it("should prioritize error over warn", () => {
      const scenes = [
        createScene({
          script: "This is a very long script that exceeds 40 characters limit",
          speaker: "Narrator",
        }),
      ];
      const { results, summary } = computeValidationResults(scenes);

      expect(results[1].status).toBe("error");
      expect(summary.error).toBe(1);
      expect(summary.warn).toBe(0);
    });
  });
});

describe("getFixSuggestions", () => {
  describe("Script Fixes", () => {
    it("should suggest filling empty script", () => {
      const scene = createScene({ script: "", image_prompt_ko: "테스트 장면" });
      const validation = {
        status: "error" as const,
        issues: [{ level: "error" as const, message: "Script is empty." }],
      };

      const suggestions = getFixSuggestions(scene, validation, "Fallback");

      expect(suggestions).toContainEqual({
        id: "script-empty",
        message: "Add one short line of dialogue (monologue).",
        action: { type: "fill_script", value: "테스트 장면" },
      });
    });

    it("should suggest trimming long script", () => {
      const longScript = "This is a very long script that exceeds 40 characters";
      const scene = createScene({ script: longScript });
      const validation = {
        status: "warn" as const,
        issues: [{ level: "warn" as const, message: "Script is longer than 40 characters." }],
      };

      const suggestions = getFixSuggestions(scene, validation, "Fallback");

      expect(suggestions).toContainEqual({
        id: "script-long",
        message: "Shorten the script to 40 characters or fewer.",
        action: { type: "trim_script", value: longScript.slice(0, 40) },
      });
    });
  });

  describe("Speaker Fixes", () => {
    it("should suggest changing speaker to A", () => {
      const scene = createScene({ speaker: "Narrator" });
      const validation = {
        status: "error" as const,
        issues: [{ level: "error" as const, message: "Speaker must be Actor A (monologue)." }],
      };

      const suggestions = getFixSuggestions(scene, validation, "Fallback");

      expect(suggestions).toContainEqual({
        id: "speaker-a",
        message: "Change Speaker to Actor A for monologue mode.",
        action: { type: "set_speaker_a" },
      });
    });
  });

  describe("Prompt Fixes", () => {
    it("should suggest adding tokens for empty prompt", () => {
      const scene = createScene({ image_prompt: "" });
      const validation = {
        status: "error" as const,
        issues: [{ level: "error" as const, message: "Positive Prompt is empty." }],
      };

      const suggestions = getFixSuggestions(scene, validation, "Fallback");

      expect(suggestions).toContainEqual({
        id: "prompt-empty",
        message: "Add a Positive Prompt with subject + action + background.",
        action: {
          type: "add_positive",
          tokens: ["full body", "standing", "plain background", "soft light"],
        },
      });
    });

    it("should suggest adding tokens for short prompt", () => {
      const scene = createScene({ image_prompt: "1girl, smile" });
      const validation = {
        status: "warn" as const,
        issues: [
          { level: "warn" as const, message: "Prompt is too short; add more visual details." },
        ],
      };

      const suggestions = getFixSuggestions(scene, validation, "Fallback");

      expect(suggestions).toContainEqual({
        id: "prompt-short",
        message: "Add 3-5 more visual tokens (pose, setting, lighting).",
        action: {
          type: "add_positive",
          tokens: ["full body", "standing", "plain background", "soft light", "neutral pose"],
        },
      });
    });

    it("should suggest camera keywords", () => {
      const scene = createScene({ image_prompt: "1girl, smile, happy, cheerful, cute" });
      const validation = {
        status: "warn" as const,
        issues: [{ level: "warn" as const, message: "Missing camera/shot keywords." }],
      };

      const suggestions = getFixSuggestions(scene, validation, "Fallback");

      expect(suggestions).toContainEqual({
        id: "missing-camera",
        message: "Add camera keywords like: full body, wide shot, close-up, low angle.",
        action: { type: "add_positive", tokens: ["full body"] },
      });
    });

    it("should suggest action keywords", () => {
      const scene = createScene({ image_prompt: "1girl, full body, library, soft light, smile" });
      const validation = {
        status: "warn" as const,
        issues: [{ level: "warn" as const, message: "Missing action/pose keywords." }],
      };

      const suggestions = getFixSuggestions(scene, validation, "Fallback");

      expect(suggestions).toContainEqual({
        id: "missing-action",
        message: "Add action keywords like: standing, walking, running, holding.",
        action: { type: "add_positive", tokens: ["standing"] },
      });
    });

    it("should suggest background keywords", () => {
      const scene = createScene({ image_prompt: "1girl, standing, full body, soft light, smile" });
      const validation = {
        status: "warn" as const,
        issues: [{ level: "warn" as const, message: "Missing background/setting keywords." }],
      };

      const suggestions = getFixSuggestions(scene, validation, "Fallback");

      expect(suggestions).toContainEqual({
        id: "missing-background",
        message: "Add background keywords like: library, room, street, cafe.",
        action: { type: "add_positive", tokens: ["library", "room", "street", "cafe"] },
      });
    });

    it("should suggest lighting keywords", () => {
      const scene = createScene({ image_prompt: "1girl, standing, full body, library, smile" });
      const validation = {
        status: "warn" as const,
        issues: [{ level: "warn" as const, message: "Missing lighting/mood keywords." }],
      };

      const suggestions = getFixSuggestions(scene, validation, "Fallback");

      expect(suggestions).toContainEqual({
        id: "missing-lighting",
        message: "Add lighting keywords like: soft light, sunset, neon, moody.",
        action: { type: "add_positive", tokens: ["soft light"] },
      });
    });
  });

  describe("Negative Prompt Fixes", () => {
    it("should suggest removing scene keywords from negative", () => {
      const scene = createScene({ negative_prompt: "library, standing, bad quality" });
      const validation = {
        status: "warn" as const,
        issues: [{ level: "warn" as const, message: "Negative Prompt contains scene keywords." }],
      };

      const suggestions = getFixSuggestions(scene, validation, "Fallback");

      expect(suggestions).toContainEqual({
        id: "negative-scene-keywords",
        message: "Remove scene/location words from Negative Prompt.",
        action: { type: "remove_negative_scene" },
      });
    });
  });

  describe("Multiple Issues", () => {
    it("should provide multiple suggestions for multiple issues", () => {
      const scene = createScene({
        script: "",
        speaker: "Narrator",
        image_prompt: "",
      });
      const validation = {
        status: "error" as const,
        issues: [
          { level: "error" as const, message: "Script is empty." },
          { level: "error" as const, message: "Speaker must be Actor A (monologue)." },
          { level: "error" as const, message: "Positive Prompt is empty." },
        ],
      };

      const suggestions = getFixSuggestions(scene, validation, "Fallback");

      expect(suggestions).toHaveLength(3);
      expect(suggestions.map((s) => s.id)).toEqual(["script-empty", "speaker-a", "prompt-empty"]);
    });
  });

  describe("Edge Cases", () => {
    it("should return empty array for undefined validation", () => {
      const scene = createScene();
      const suggestions = getFixSuggestions(scene, undefined, "Fallback");

      expect(suggestions).toEqual([]);
    });

    it("should return empty array for validation with no issues", () => {
      const scene = createScene();
      const validation = { status: "ok" as const, issues: [] };
      const suggestions = getFixSuggestions(scene, validation, "Fallback");

      expect(suggestions).toEqual([]);
    });

    it("should use fallback topic when all sources are empty", () => {
      const scene = createScene({
        script: "",
        image_prompt: "",
        image_prompt_ko: "",
      });
      const validation = {
        status: "error" as const,
        issues: [{ level: "error" as const, message: "Script is empty." }],
      };

      const suggestions = getFixSuggestions(scene, validation, "My Topic");

      expect(suggestions[0].action?.value).toBe("My Topic");
    });
  });
});
