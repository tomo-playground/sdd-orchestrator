"use client";

import type { Scene, Tag, Background } from "../../types";
import { isMultiCharStructure } from "../../utils/structure";
import { useContextStore } from "../../store/useContextStore";
import CopyButton from "../ui/CopyButton";
import TagAutocomplete from "../ui/TagAutocomplete";
import PromptTokenPreview from "../prompt/PromptTokenPreview";
import ComposedPromptPreview from "../prompt/ComposedPromptPreview";
import SceneContextTags from "../prompt/SceneContextTags";
import SceneCharacterActions from "./SceneCharacterActions";
import NegativePromptToggle from "./NegativePromptToggle";

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
  structure?: string;
  tagsByGroup: Record<string, Tag[]>;
  sceneTagGroups: string[];
  isExclusiveGroup: (groupName: string) => boolean;
  onUpdateScene: (updates: Partial<Scene>) => void;
  onSpeakerChange: (speaker: Scene["speaker"]) => void;
  onImageUpload: (file: File | undefined) => void;
  // Multi-character props
  characterAName?: string | null;
  characterBName?: string | null;
  selectedCharacterBId?: number | null;
  // Background picker
  backgrounds?: Background[];
};

export default function SceneFormFields({
  scene,
  loraTriggerWords,
  characterLoras,
  promptMode,
  selectedCharacterId,
  basePromptA,
  structure,
  tagsByGroup,
  sceneTagGroups,
  isExclusiveGroup,
  onUpdateScene,
  onSpeakerChange,
  onImageUpload,
  characterAName,
  characterBName,
  selectedCharacterBId,
  backgrounds = [],
}: SceneFormFieldsProps) {
  const storyboardId = useContextStore((s) => s.storyboardId);
  const hasMultipleSpeakers = isMultiCharStructure(structure ?? "");
  const isNarratedDialogue = structure?.toLowerCase() === "narrated dialogue";
  const selectedBackground = backgrounds.find((bg) => bg.id === scene.background_id);

  return (
    <>
      {/* Script */}
      <div className="grid gap-2">
        <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
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
          <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Speaker
          </label>
          <select
            value={scene.speaker}
            onChange={(e) => onSpeakerChange(e.target.value as Scene["speaker"])}
            className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
          >
            {isNarratedDialogue && <option value="Narrator">Narrator</option>}
            <option value="A">Actor A</option>
            {hasMultipleSpeakers && <option value="B">Actor B</option>}
          </select>
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
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
          <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Image
          </label>
          <label className="flex h-10 cursor-pointer items-center justify-center rounded-2xl border border-dashed border-zinc-300 bg-white/80 text-[12px] font-semibold tracking-[0.2em] text-zinc-600 uppercase">
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

      {/* Background Picker */}
      {backgrounds.length > 0 && (
        <div className="grid gap-2">
          <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Background
          </label>
          <select
            value={scene.background_id ?? ""}
            onChange={(e) => {
              const val = e.target.value;
              onUpdateScene({ background_id: val ? Number(val) : null });
            }}
            className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
          >
            <option value="">None</option>
            {backgrounds.map((bg) => (
              <option key={bg.id} value={bg.id}>
                {bg.name}{bg.category ? ` (${bg.category})` : ""}
              </option>
            ))}
          </select>
          {selectedBackground?.tags && selectedBackground.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {selectedBackground.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Prompt (KO) — always visible */}
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

      {/* Scene Context Tags */}
      <SceneContextTags
        contextTags={scene.context_tags}
        tagsByGroup={tagsByGroup}
        sceneTagGroups={sceneTagGroups}
        isExclusiveGroup={isExclusiveGroup}
        onUpdate={(tags) => onUpdateScene({ context_tags: tags })}
      />

      {/* Scene Character Actions (Dialogue/Narrated Dialogue only) */}
      {hasMultipleSpeakers && (
        <SceneCharacterActions
          characterActions={scene.character_actions || []}
          characterAName={characterAName}
          characterBName={characterBName}
          characterAId={selectedCharacterId}
          characterBId={selectedCharacterBId}
          onUpdate={(actions) => onUpdateScene({ character_actions: actions })}
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
