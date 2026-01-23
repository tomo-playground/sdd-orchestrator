import type { Scene, SceneValidation, ValidationIssue } from "../types";
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
    const prompt = scene.image_prompt.toLowerCase();
    const negative = scene.negative_prompt.toLowerCase();

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
