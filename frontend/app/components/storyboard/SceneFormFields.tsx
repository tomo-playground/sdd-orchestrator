"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { Scene, Tag } from "../../types";
import CopyButton from "../ui/CopyButton";
import TagAutocomplete from "../ui/TagAutocomplete";
import PromptTokenPreview from "../prompt/PromptTokenPreview";
import ComposedPromptPreview from "../prompt/ComposedPromptPreview";
import SceneContextTags from "../prompt/SceneContextTags";

type SceneFormFieldsProps = {
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
  tagsByGroup: Record<string, Tag[]>;
  sceneTagGroups: string[];
  isExclusiveGroup: (groupName: string) => boolean;
  onUpdateScene: (updates: Partial<Scene>) => void;
  onSpeakerChange: (speaker: Scene["speaker"]) => void;
  onImageUpload: (file: File | undefined) => void;
};

export default function SceneFormFields({
  scene,
  loraTriggerWords,
  characterLoras,
  promptMode,
  selectedCharacterId,
  basePromptA,
  tagsByGroup,
  sceneTagGroups,
  isExclusiveGroup,
  onUpdateScene,
  onSpeakerChange,
  onImageUpload,
}: SceneFormFieldsProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  return (
    <>
      {/* Script */}
      <div className="grid gap-2">
        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Script
        </label>
        <textarea
          value={scene.script}
          onChange={(e) => onUpdateScene({ script: e.target.value })}
          rows={3}
          className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
        />
      </div>

      {/* Speaker, Duration, Upload */}
      <div className="grid grid-cols-3 gap-3">
        <div className="flex flex-col gap-2">
          <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Speaker
          </label>
          <select
            value={scene.speaker}
            onChange={(e) => onSpeakerChange(e.target.value as Scene["speaker"])}
            className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
          >
            <option value="A">Actor A</option>
          </select>
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Duration
          </label>
          <input
            type="number"
            min={1}
            max={10}
            value={scene.duration}
            onChange={(e) => onUpdateScene({ duration: Number(e.target.value) })}
            className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
          />
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Image
          </label>
          <label className="flex h-10 cursor-pointer items-center justify-center rounded-2xl border border-dashed border-zinc-300 bg-white/80 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase">
            Upload
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => onImageUpload(e.target.files?.[0])}
            />
          </label>
        </div>
      </div>

      {/* Scene Context Tags */}
      <SceneContextTags
        contextTags={scene.context_tags}
        tagsByGroup={tagsByGroup}
        sceneTagGroups={sceneTagGroups}
        isExclusiveGroup={isExclusiveGroup}
        onUpdate={(tags) => onUpdateScene({ context_tags: tags })}
      />

      {/* Positive Prompt */}
      <div className="grid gap-2">
        <div className="flex items-center justify-between">
          <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Positive Prompt
          </label>
          {scene.image_prompt && (
            <CopyButton text={scene.image_prompt} />
          )}
        </div>
        <TagAutocomplete
          value={scene.image_prompt}
          onChange={(value) => onUpdateScene({ image_prompt: value })}
          rows={2}
          className="w-full rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
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

      {/* Prompt (KO) — always visible */}
      <div className="grid gap-2">
        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Prompt (KO)
        </label>
        <TagAutocomplete
          value={scene.image_prompt_ko}
          onChange={(value) => onUpdateScene({ image_prompt_ko: value })}
          rows={2}
          className="w-full rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
        />
      </div>

      {/* Advanced Toggle (Negative Prompt) */}
      <button
        type="button"
        onClick={() => setShowAdvanced((v) => !v)}
        className="flex items-center gap-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-400 uppercase transition hover:text-zinc-600"
      >
        <ChevronDown
          className={`h-3 w-3 transition-transform ${showAdvanced ? "rotate-180" : ""}`}
        />
        Negative
        {!showAdvanced && scene.negative_prompt && (
          <span className="ml-1 max-w-[200px] truncate text-[9px] font-normal normal-case tracking-normal text-zinc-300">
            {scene.negative_prompt.slice(0, 40)}
          </span>
        )}
      </button>

      {showAdvanced && (
        <div className="grid gap-2">
          <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Negative Prompt
          </label>
          <textarea
            value={scene.negative_prompt}
            onChange={(e) => onUpdateScene({ negative_prompt: e.target.value })}
            rows={2}
            className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
          />
        </div>
      )}
    </>
  );
}
