"use client";

import { useEffect, useRef } from "react";
import type { Scene } from "../../types";
import { useContextStore } from "../../store/useContextStore";
import useTagValidation from "../../hooks/useTagValidation";
import CopyButton from "../ui/CopyButton";
import TagAutocomplete from "../ui/TagAutocomplete";
import PromptTokenPreview from "../prompt/PromptTokenPreview";
import ComposedPromptPreview from "../prompt/ComposedPromptPreview";
import TagValidationWarning from "../prompt/TagValidationWarning";
import NegativePromptToggle from "./NegativePromptToggle";

type ScenePromptFieldsProps = {
  scene: Scene;
  loraTriggerWords: string[];
  characterLoras: Array<{
    name: string;
    weight?: number;
    trigger_words?: string[];
    lora_type?: string;
    optimal_weight?: number;
  }>;
  promptMode: "auto" | "standard" | "lora";
  selectedCharacterId?: number | null;
  basePromptA: string;
  onUpdateScene: (updates: Partial<Scene>) => void;
};

export default function ScenePromptFields({
  scene,
  loraTriggerWords,
  characterLoras,
  promptMode,
  selectedCharacterId,
  basePromptA,
  onUpdateScene,
}: ScenePromptFieldsProps) {
  const storyboardId = useContextStore((s) => s.storyboardId);

  // Tag validation
  const { validationResult, validateTags, autoReplaceTags, clearValidation } = useTagValidation();
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const prompt = scene.image_prompt;
    if (!prompt || !prompt.trim()) {
      clearValidation();
      return;
    }
    debounceRef.current = setTimeout(() => {
      const tags = prompt
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      if (tags.length > 0) validateTags(tags);
    }, 800);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [scene.image_prompt, validateTags, clearValidation]);

  const handleAutoReplace = async () => {
    const prompt = scene.image_prompt;
    if (!prompt) return;
    const tags = prompt
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    const replaced = await autoReplaceTags(tags);
    if (replaced) {
      onUpdateScene({ image_prompt: replaced.join(", ") });
    }
  };

  return (
    <>
      {/* Prompt (KO) */}
      <div className="grid gap-2">
        <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Prompt (KO)
        </label>
        <TagAutocomplete
          value={scene.image_prompt_ko}
          onChange={(value) => onUpdateScene({ image_prompt_ko: value })}
          rows={2}
          className="w-full rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
        />
      </div>

      {/* Positive Prompt */}
      <div className="grid gap-2">
        <div className="flex items-center justify-between">
          <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Positive Prompt
          </label>
          {scene.image_prompt && <CopyButton text={scene.image_prompt} />}
        </div>
        <TagAutocomplete
          value={scene.image_prompt}
          onChange={(value) => onUpdateScene({ image_prompt: value })}
          rows={2}
          className="w-full rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
        />
        <TagValidationWarning
          result={validationResult}
          onAutoReplace={handleAutoReplace}
          onDismiss={clearValidation}
        />
        {scene.image_prompt && (
          <>
            <PromptTokenPreview prompt={scene.image_prompt} triggerWords={loraTriggerWords} />
            <ComposedPromptPreview
              tokens={scene.image_prompt
                .split(",")
                .map((t) => t.trim())
                .filter(Boolean)}
              characterId={selectedCharacterId}
              storyboardId={storyboardId}
              basePrompt={basePromptA}
              contextTags={scene.context_tags || undefined}
              loras={characterLoras}
              mode={promptMode}
              useBreak={true}
              className="mt-2 rounded-xl border border-zinc-200 bg-zinc-50/50 p-3"
            />
          </>
        )}
      </div>

      {/* Negative Prompt (collapsible) */}
      <NegativePromptToggle
        negativePrompt={scene.negative_prompt}
        onChange={(value) => onUpdateScene({ negative_prompt: value })}
      />
    </>
  );
}
