import React from "react";
import type { ActorGender, PromptMode, LoRA, VoicePreset } from "../../../types";

// --- Basic Info ---
export function BasicInfoSection({
  name,
  setName,
  gender,
  setGender,
  description,
  setDescription,
}: {
  name: string;
  setName: (v: string) => void;
  gender: ActorGender;
  setGender: (v: ActorGender) => void;
  description: string;
  setDescription: (v: string) => void;
}) {
  return (
    <>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
            Name
          </label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
            Gender
          </label>
          <select
            value={gender || "female"}
            onChange={(e) => setGender(e.target.value as ActorGender)}
            className="w-full rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
          >
            <option value="female">Female</option>
            <option value="male">Male</option>
          </select>
        </div>
      </div>
      <div>
        <label className="mb-1 block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
          Description
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          className="w-full resize-none rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400"
        />
      </div>
    </>
  );
}

// --- Prompt Mode ---
export function PromptModeSection({
  promptMode,
  setPromptMode,
}: {
  promptMode: PromptMode;
  setPromptMode: (v: PromptMode) => void;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
        Prompt Mode
      </label>
      <select
        value={promptMode}
        onChange={(e) => setPromptMode(e.target.value as PromptMode)}
        className="w-full rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
      >
        <option value="auto">Auto (Smart Compose)</option>
        <option value="standard">Standard (No LoRA)</option>
        <option value="lora">LoRA Only</option>
      </select>
      <p className="mt-1 text-[11px] text-zinc-400">
        Auto: Smart compose. Standard: No LoRA. LoRA: Forces character LoRAs.
      </p>
    </div>
  );
}

// --- IP-Adapter ---
export function IpAdapterSection({
  ipAdapterWeight,
  setIpAdapterWeight,
  ipAdapterModel,
  setIpAdapterModel,
}: {
  ipAdapterWeight: number;
  setIpAdapterWeight: (v: number) => void;
  ipAdapterModel: string;
  setIpAdapterModel: (v: string) => void;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
        IP-Adapter Settings
      </label>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="mb-1 block text-[11px] text-zinc-400">Weight ({ipAdapterWeight})</label>
          <input
            type="range"
            min="0"
            max="1.5"
            step="0.05"
            value={ipAdapterWeight}
            onChange={(e) => setIpAdapterWeight(Number(e.target.value))}
            className="w-full"
          />
        </div>
        <div>
          <label className="mb-1 block text-[11px] text-zinc-400">Model</label>
          <select
            value={ipAdapterModel}
            onChange={(e) => setIpAdapterModel(e.target.value)}
            className="w-full rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
          >
            <option value="clip_face">clip_face (Standard)</option>
            <option value="clip">clip (Style/Chibi)</option>
            <option value="faceid">faceid (Realistic)</option>
          </select>
        </div>
      </div>
    </div>
  );
}

// --- Scene Identity ---
export function SceneIdentitySection({
  isCreateMode,
  customBasePrompt,
  setCustomBasePrompt,
  customNegativePrompt,
  setCustomNegativePrompt,
  onCopyToReference,
  sceneIdentityWarning,
}: {
  isCreateMode: boolean;
  customBasePrompt: string;
  setCustomBasePrompt: React.Dispatch<React.SetStateAction<string>>;
  customNegativePrompt: string;
  setCustomNegativePrompt: (v: string) => void;
  onCopyToReference?: (type: "base" | "negative") => void;
  sceneIdentityWarning: string | null;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div>
        <div className="mb-1 flex items-center justify-between">
          <label className="block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
            Scene Identity (Fixed Appearance)
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() =>
                setCustomBasePrompt((prev) => {
                  const base = "masterpiece, best_quality";
                  if (!prev.includes(base)) return `${base}, ${prev}`.trim().replace(/^,\s+/, "");
                  return prev;
                })
              }
              className="rounded bg-zinc-100 px-1.5 py-0.5 text-[11px] font-bold text-zinc-500 transition-colors hover:bg-zinc-200 hover:text-zinc-700"
            >
              + QUALITY
            </button>
            {!isCreateMode && onCopyToReference && (
              <button
                type="button"
                onClick={() => onCopyToReference("base")}
                className="text-[11px] text-zinc-500 hover:underline"
              >
                Copy to Ref.
              </button>
            )}
          </div>
        </div>
        <textarea
          value={customBasePrompt}
          onChange={(e) => setCustomBasePrompt(e.target.value)}
          rows={3}
          placeholder="Tags that define character's core look (e.g. hair style, eye color, unique traits). NO BACKGROUND TAGS."
          className={`w-full rounded-xl border ${sceneIdentityWarning ? "border-amber-400" : "border-zinc-200"} resize-none px-3 py-2 font-mono text-sm outline-none focus:border-zinc-400`}
        />
        {sceneIdentityWarning && (
          <p className="mt-1 text-[11px] font-medium text-amber-600 italic">
            {sceneIdentityWarning}
          </p>
        )}
      </div>
      <div>
        <div className="mb-1 flex items-center justify-between">
          <label className="block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
            Common Negative (Scene)
          </label>
          {!isCreateMode && onCopyToReference && (
            <button
              type="button"
              onClick={() => onCopyToReference("negative")}
              className="text-[11px] text-zinc-500 hover:underline"
            >
              Copy to Ref.
            </button>
          )}
        </div>
        <textarea
          value={customNegativePrompt}
          onChange={(e) => setCustomNegativePrompt(e.target.value)}
          rows={3}
          placeholder="Additional negative tags..."
          className="w-full resize-none rounded-xl border border-zinc-200 px-3 py-2 font-mono text-sm outline-none focus:border-zinc-400"
        />
      </div>
    </div>
  );
}

// --- LoRAs ---
export function LoRAsSection({
  selectedLoras,
  allLoras,
  onAddLora,
  onUpdateLora,
  onRemoveLora,
  onLoraTypeChange,
}: {
  selectedLoras: { lora_id: number; weight: number }[];
  allLoras: LoRA[];
  onAddLora: () => void;
  onUpdateLora: (index: number, field: "lora_id" | "weight", value: number) => void;
  onRemoveLora: (index: number) => void;
  onLoraTypeChange: (loraId: number, newType: string) => void;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <label className="block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
          LoRAs
        </label>
        <button
          onClick={onAddLora}
          className="rounded-full bg-indigo-50 px-2 py-1 text-[11px] font-semibold text-indigo-600 hover:text-indigo-700"
        >
          + Add LoRA
        </button>
      </div>
      <div className="space-y-2">
        {selectedLoras.map((lora, index) => {
          const loraInfo = allLoras.find((l) => l.id === lora.lora_id);
          return (
            <div
              key={lora.lora_id}
              className="flex items-center gap-2 rounded-xl border border-zinc-100 bg-zinc-50/50 p-2"
            >
              <select
                value={lora.lora_id}
                onChange={(e) => onUpdateLora(index, "lora_id", Number(e.target.value))}
                className="flex-1 rounded-lg border border-zinc-200 bg-white px-2 py-1.5 text-xs outline-none focus:border-zinc-400"
              >
                {allLoras.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.display_name || l.name}
                    {l.lora_type ? ` [${l.lora_type}]` : ""}
                  </option>
                ))}
              </select>
              <select
                value={loraInfo?.lora_type || "character"}
                onChange={(e) => onLoraTypeChange(lora.lora_id, e.target.value)}
                className={`w-20 rounded-lg border px-1.5 py-1.5 text-[11px] font-semibold outline-none ${
                  loraInfo?.lora_type === "style"
                    ? "border-violet-200 bg-violet-50 text-violet-600"
                    : "border-zinc-200 bg-white text-zinc-500"
                }`}
              >
                <option value="character">character</option>
                <option value="style">style</option>
                <option value="pose">pose</option>
              </select>
              <input
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={lora.weight}
                onChange={(e) => onUpdateLora(index, "weight", Number(e.target.value))}
                className="w-16 rounded-lg border border-zinc-200 px-2 py-1.5 text-center text-xs outline-none focus:border-zinc-400"
              />
              <button
                onClick={() => onRemoveLora(index)}
                className="px-1 text-rose-400 hover:text-rose-600"
              >
                x
              </button>
            </div>
          );
        })}
        {selectedLoras.length === 0 && (
          <p className="text-xs text-zinc-400 italic">No LoRAs assigned.</p>
        )}
      </div>
    </div>
  );
}

// --- Voice Preset ---
export function VoicePresetSection({
  voicePresets,
  selectedId,
  onChange,
}: {
  voicePresets: VoicePreset[];
  selectedId: number | null;
  onChange: (id: number | null) => void;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
        Default Voice Preset
      </label>
      <select
        value={selectedId ?? ""}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
        className="w-full rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
      >
        <option value="">None (use render panel default)</option>
        {voicePresets.map((vp) => (
          <option key={vp.id} value={vp.id}>
            {vp.name}
            {vp.description ? ` — ${vp.description}` : ""}
          </option>
        ))}
      </select>
      <p className="mt-1 text-[11px] text-zinc-400">
        Assigned voice for this character. Overrides the global render preset voice during TTS.
      </p>
    </div>
  );
}
