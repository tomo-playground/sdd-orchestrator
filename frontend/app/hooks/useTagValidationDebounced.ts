/**
 * Wrapper hook: useTagValidation + debounce + auto-replace
 *
 * Encapsulates the repeated pattern of debounced tag validation
 * used across ScenePromptFields, PromptPair, StyleProfileEditor,
 * NegativePromptToggle, and SceneClothingModal.
 */

import { useEffect, useRef } from "react";
import useTagValidation from "./useTagValidation";

function parseTags(prompt: string): string[] {
  return prompt
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
}

export default function useTagValidationDebounced(
  prompt: string | null | undefined,
  onReplace: (replaced: string) => void,
  options?: { debounceMs?: number; enabled?: boolean }
) {
  const { debounceMs = 800, enabled = true } = options ?? {};
  const { validationResult, validateTags, autoReplaceTags, clearValidation } =
    useTagValidation();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    clearTimeout(debounceRef.current);
    if (!enabled || !prompt?.trim()) {
      clearValidation();
      return;
    }
    debounceRef.current = setTimeout(() => {
      const tags = parseTags(prompt);
      if (tags.length > 0) validateTags(tags);
    }, debounceMs);
    return () => clearTimeout(debounceRef.current);
  }, [prompt, enabled, debounceMs, validateTags, clearValidation]);

  const handleAutoReplace = async () => {
    if (!prompt) return;
    const replaced = await autoReplaceTags(parseTags(prompt));
    if (replaced) onReplace(replaced.join(", "));
  };

  return { validationResult, handleAutoReplace, clearValidation };
}
