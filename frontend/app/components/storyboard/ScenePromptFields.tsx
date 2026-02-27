"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Scene } from "../../types";
import { ADMIN_API_BASE } from "../../constants";
import { useContextStore } from "../../store/useContextStore";
import useTagValidationDebounced from "../../hooks/useTagValidationDebounced";
import CopyButton from "../ui/CopyButton";
import TagAutocomplete from "../ui/TagAutocomplete";
import ComposedPromptPreview, { type NegativeSourceInfo } from "../prompt/ComposedPromptPreview";
import TagValidationWarning from "../prompt/TagValidationWarning";
import PromptTranslateDiff from "../prompt/PromptTranslateDiff";

const SOURCE_COLORS: Record<string, { bg: string; text: string }> = {
  style_profile: { bg: "bg-fuchsia-50", text: "text-fuchsia-700" },
  character: { bg: "bg-blue-50", text: "text-blue-700" },
  scene: { bg: "bg-amber-50", text: "text-amber-700" },
};

function getSourceStyle(source: string) {
  if (source.startsWith("character:")) return SOURCE_COLORS.character;
  return SOURCE_COLORS[source] || SOURCE_COLORS.scene;
}

function getSourceLabel(source: string) {
  if (source === "style_profile") return "Style";
  if (source.startsWith("character:")) return source.replace("character:", "");
  if (source === "scene") return "Scene";
  return source;
}

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
  selectedCharacterId?: number | null;
  basePromptA: string;
  onUpdateScene: (updates: Partial<Scene>) => void;
};

export default function ScenePromptFields({
  scene,
  characterLoras,
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
        const res = await fetch(`${ADMIN_API_BASE}/prompt/negative-preview`, {
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

  // Tag validation — positive
  const { validationResult, handleAutoReplace, clearValidation } = useTagValidationDebounced(
    scene.image_prompt,
    (v) => onUpdateScene({ image_prompt: v })
  );

  // Tag validation — negative
  const {
    validationResult: negValidation,
    handleAutoReplace: negAutoReplace,
    clearValidation: negClearValidation,
  } = useTagValidationDebounced(scene.negative_prompt, (v) =>
    onUpdateScene({ negative_prompt: v })
  );

  const hasComposedNeg = !!composedNegative && negativeSources.length > 0;

  return (
    <div className="grid gap-6 md:grid-cols-2">
      {/* ── Left Column: Inputs ── */}
      <div className="grid content-start gap-4">
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

        {/* KO → EN diff */}
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
        </div>

        {/* Negative Prompt */}
        <div className="grid gap-2">
          <div className="flex items-center justify-between">
            <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              Negative Prompt
            </label>
            {scene.negative_prompt && <CopyButton text={scene.negative_prompt} />}
          </div>
          <TagAutocomplete
            value={scene.negative_prompt}
            onChange={(value) => onUpdateScene({ negative_prompt: value })}
            rows={2}
            placeholder="씬별 추가 네거티브 태그 (선택)"
            className="w-full rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
          />
          <TagValidationWarning
            result={negValidation}
            onAutoReplace={negAutoReplace}
            onDismiss={negClearValidation}
          />
        </div>
      </div>

      {/* ── Right Column: Outputs ── */}
      <div className="grid content-start gap-4">
        {/* Composed Positive */}
        {scene.image_prompt && (
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
            useBreak={true}
            onNegativeComposed={handleNegativeComposed}
            className="rounded-xl border border-zinc-200 bg-zinc-50/50 p-3"
          />
        )}

        {/* Composed Negative */}
        {hasComposedNeg && (
          <div className="space-y-2 rounded-xl border border-zinc-200 bg-zinc-50/50 p-3">
            <div className="flex items-center justify-between">
              <span className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                Composed Negative
              </span>
              <CopyButton text={composedNegative} variant="label" />
            </div>
            <div className="space-y-1.5">
              {negativeSources.map((src) => {
                const style = getSourceStyle(src.source);
                return (
                  <div key={src.source} className="flex items-start gap-2">
                    <span
                      className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ${style.bg} ${style.text}`}
                    >
                      {getSourceLabel(src.source)}
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {src.tokens.map((token, idx) => (
                        <span
                          key={idx}
                          className="rounded-full border border-zinc-200 bg-white px-2 py-0.5 text-[12px] text-zinc-600"
                        >
                          {token}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
