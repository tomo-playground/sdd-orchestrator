"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Scene } from "../../types";
import { API_BASE } from "../../constants";
import { useContextStore } from "../../store/useContextStore";
import useTagValidationDebounced from "../../hooks/useTagValidationDebounced";
import CopyButton from "../ui/CopyButton";
import TagAutocomplete from "../ui/TagAutocomplete";
import ComposedPromptPreview, { type NegativeSourceInfo } from "../prompt/ComposedPromptPreview";
import TagValidationWarning from "../prompt/TagValidationWarning";
import PromptTranslateDiff from "../prompt/PromptTranslateDiff";
import NegativePromptToggle from "./NegativePromptToggle";

type ScenePromptFieldsProps = {
  scene: Scene;
  loraTriggerWords?: string[];
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
  characterLoras,
  promptMode,
  selectedCharacterId,
  basePromptA,
  onUpdateScene,
}: ScenePromptFieldsProps) {
  const storyboardId = useContextStore((s) => s.storyboardId);

  // Composed negative state
  const [composedNegative, setComposedNegative] = useState<string>("");
  const [negativeSources, setNegativeSources] = useState<NegativeSourceInfo[]>([]);

  const handleNegativeComposed = useCallback((negative: string, sources: NegativeSourceInfo[]) => {
    setComposedNegative(negative);
    setNegativeSources(sources);
  }, []);

  // Independent negative preview fetch (works even without characterId)
  // Skip if characterId exists + image_prompt exists — compose API handles negative in that case
  const composeHandlesNegative = !!selectedCharacterId && !!scene.image_prompt;
  const negFetchRef = useRef<string>("");
  useEffect(() => {
    if (composeHandlesNegative) return;
    const key = `${storyboardId}|${selectedCharacterId}|${scene.id}`;
    if (key === negFetchRef.current) return;
    if (!storyboardId && !selectedCharacterId) return;

    negFetchRef.current = key;
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE}/prompt/negative-preview`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            storyboard_id: storyboardId || undefined,
            character_id: selectedCharacterId || undefined,
            scene_id: scene.id || undefined,
          }),
        });
        if (!res.ok) return;
        const data = await res.json();
        setComposedNegative(data.negative_prompt ?? "");
        setNegativeSources(data.negative_sources ?? []);
      } catch {
        // Silent fail — negative preview is optional
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [storyboardId, selectedCharacterId, scene.id, composeHandlesNegative]);

  // Tag validation
  const { validationResult, handleAutoReplace, clearValidation } = useTagValidationDebounced(
    scene.image_prompt,
    (v) => onUpdateScene({ image_prompt: v })
  );

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

      {/* KO → EN 변환 diff */}
      {scene.image_prompt_ko && (
        <PromptTranslateDiff
          koText={scene.image_prompt_ko}
          currentPrompt={scene.image_prompt || ""}
          characterId={selectedCharacterId}
          onApply={(translated) => onUpdateScene({ image_prompt: translated })}
        />
      )}

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
            <ComposedPromptPreview
              tokens={scene.image_prompt
                .split(",")
                .map((t) => t.trim())
                .filter(Boolean)}
              characterId={selectedCharacterId}
              storyboardId={storyboardId}
              sceneId={scene.id}
              basePrompt={basePromptA}
              contextTags={scene.context_tags || undefined}
              backgroundId={scene.background_id || undefined}
              loras={characterLoras}
              mode={promptMode}
              useBreak={true}
              onNegativeComposed={handleNegativeComposed}
              className="mt-2 rounded-xl border border-zinc-200 bg-zinc-50/50 p-3"
            />
          </>
        )}
      </div>

      {/* Negative Prompt (collapsible) */}
      <NegativePromptToggle
        negativePrompt={scene.negative_prompt}
        onChange={(value) => onUpdateScene({ negative_prompt: value })}
        composedNegative={composedNegative}
        negativeSources={negativeSources}
      />
    </>
  );
}
