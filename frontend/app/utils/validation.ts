import type { Scene, SceneValidation, ValidationIssue, FixSuggestion } from "../types";
import {
  CAMERA_KEYWORDS,
  ACTION_KEYWORDS,
  BACKGROUND_KEYWORDS,
  LIGHTING_KEYWORDS,
} from "../constants";

/**
 * Check if text contains any of the keywords from the list.
 */
const hasAny = (text: string, list: string[]) =>
  list.some((keyword) => text.includes(keyword));

/**
 * Compute validation results for a list of scenes.
 * Returns validation status and issues for each scene.
 */
export const computeValidationResults = (inputScenes: Scene[]) => {
  const results: Record<number, SceneValidation> = {};
  let ok = 0;
  let warn = 0;
  let error = 0;

  inputScenes.forEach((scene) => {
    const issues: ValidationIssue[] = [];
    const script = scene.script.trim();

    // Normalize to underscore format (Danbooru standard)
    // Exception: LoRA trigger words keep original format (e.g., "flat color", "Midoriya_Izuku")
    // This validation only checks CAMERA/ACTION/BACKGROUND/LIGHTING keywords, not LoRA triggers
    const prompt = scene.image_prompt.toLowerCase().replace(/ /g, "_");
    const negative = scene.negative_prompt.toLowerCase().replace(/ /g, "_");

    if (!script) {
      issues.push({ level: "error", message: "Script is empty." });
    } else if (script.length > 40) {
      issues.push({ level: "warn", message: "Script is longer than 40 characters." });
    }

    if (scene.speaker !== "A") {
      issues.push({ level: "error", message: "Speaker must be Actor A (monologue)." });
    }

    if (!scene.image_prompt.trim()) {
      issues.push({ level: "error", message: "Positive Prompt is empty." });
    } else {
      const tokenCount = scene.image_prompt.split(",").filter(Boolean).length;
      if (tokenCount < 5) {
        issues.push({ level: "warn", message: "Prompt is too short; add more visual details." });
      }
      if (!hasAny(prompt, CAMERA_KEYWORDS)) {
        issues.push({ level: "warn", message: "Missing camera/shot keywords." });
      }
      if (!hasAny(prompt, ACTION_KEYWORDS)) {
        issues.push({ level: "warn", message: "Missing action/pose keywords." });
      }
      if (!hasAny(prompt, BACKGROUND_KEYWORDS)) {
        issues.push({ level: "warn", message: "Missing background/setting keywords." });
      }
      if (!hasAny(prompt, LIGHTING_KEYWORDS)) {
        issues.push({ level: "warn", message: "Missing lighting/mood keywords." });
      }
    }

    const forbidden = CAMERA_KEYWORDS.concat(ACTION_KEYWORDS, BACKGROUND_KEYWORDS);
    if (negative && forbidden.some((keyword) => negative.includes(keyword))) {
      issues.push({ level: "warn", message: "Negative Prompt contains scene keywords." });
    }

    const status = issues.some((item) => item.level === "error")
      ? "error"
      : issues.length
        ? "warn"
        : "ok";

    results[scene.id] = { status, issues };
    if (status === "ok") ok += 1;
    if (status === "warn") warn += 1;
    if (status === "error") error += 1;
  });

  return { results, summary: { ok, warn, error } };
};

/**
 * Get fix suggestions for a scene based on its validation results.
 * @param scene - The scene to get suggestions for
 * @param validation - The validation result for the scene
 * @param fallbackTopic - Fallback topic text for script suggestions
 */
export const getFixSuggestions = (
  scene: Scene,
  validation: SceneValidation | undefined,
  fallbackTopic: string
): FixSuggestion[] => {
  if (!validation) return [];
  const suggestions: FixSuggestion[] = [];
  const issueText = validation.issues.map((issue) => issue.message);
  const includes = (needle: string) => issueText.some((text) => text.includes(needle));
  const scriptFallback = (
    scene.image_prompt_ko ||
    scene.image_prompt ||
    fallbackTopic.trim() ||
    "오늘의 장면"
  ).slice(0, 40);

  if (includes("Script is empty")) {
    suggestions.push({
      id: "script-empty",
      message: "Add one short line of dialogue (monologue).",
      action: { type: "fill_script", value: scriptFallback },
    });
  }
  if (includes("Script is longer than 40 characters")) {
    suggestions.push({
      id: "script-long",
      message: "Shorten the script to 40 characters or fewer.",
      action: { type: "trim_script", value: scene.script.slice(0, 40) },
    });
  }
  if (includes("Speaker must be Actor A")) {
    suggestions.push({
      id: "speaker-a",
      message: "Change Speaker to Actor A for monologue mode.",
      action: { type: "set_speaker_a" },
    });
  }
  if (includes("Positive Prompt is empty")) {
    suggestions.push({
      id: "prompt-empty",
      message: "Add a Positive Prompt with subject + action + background.",
      action: {
        type: "add_positive",
        tokens: ["full body", "standing", "plain background", "soft light"],
      },
    });
  }
  if (includes("Prompt is too short")) {
    suggestions.push({
      id: "prompt-short",
      message: "Add 3-5 more visual tokens (pose, setting, lighting).",
      action: {
        type: "add_positive",
        tokens: ["full body", "standing", "plain background", "soft light", "neutral pose"],
      },
    });
  }
  if (includes("Missing camera/shot keywords")) {
    suggestions.push({
      id: "missing-camera",
      message: "Add camera keywords like: full body, wide shot, close-up, low angle.",
      action: { type: "add_positive", tokens: ["full body"] },
    });
  }
  if (includes("Missing action/pose keywords")) {
    suggestions.push({
      id: "missing-action",
      message: "Add action keywords like: standing, walking, running, holding.",
      action: { type: "add_positive", tokens: ["standing"] },
    });
  }
  if (includes("Missing background/setting keywords")) {
    suggestions.push({
      id: "missing-background",
      message: "Add background keywords like: library, room, street, cafe.",
      action: { type: "add_positive", tokens: ["library", "room", "street", "cafe"] },
    });
  }
  if (includes("Missing lighting/mood keywords")) {
    suggestions.push({
      id: "missing-lighting",
      message: "Add lighting keywords like: soft light, sunset, neon, moody.",
      action: { type: "add_positive", tokens: ["soft light"] },
    });
  }
  if (includes("Negative Prompt contains scene keywords")) {
    suggestions.push({
      id: "negative-scene-keywords",
      message: "Remove scene/location words from Negative Prompt.",
      action: { type: "remove_negative_scene" },
    });
  }

  return suggestions;
};
