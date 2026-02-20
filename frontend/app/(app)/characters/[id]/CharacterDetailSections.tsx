"use client";

import { useState, useMemo } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { ActorGender, PromptMode } from "../../../types";
import Input from "../../../components/ui/Input";
import Textarea from "../../../components/ui/Textarea";
import { findDuplicateTokens } from "../shared/promptDuplicateCheck";
import { formatTagName } from "../shared/formatTag";
import PromptPair from "../shared/PromptPair";
import VoicePresetSelector from "../../../components/voice/VoicePresetSelector";

// ── Shared form type ─────────────────────────────────────────
export type CharacterFormData = {
  name: string;
  description: string;
  gender: ActorGender | null;
  prompt_mode: PromptMode;
  custom_base_prompt: string;
  custom_negative_prompt: string;
  reference_base_prompt: string;
  reference_negative_prompt: string;
  voice_preset_id: number | null;
  ip_adapter_weight: number;
  ip_adapter_model: string;
};

type FormOnChange = <K extends keyof CharacterFormData>(
  key: K,
  value: CharacterFormData[K]
) => void;

// ── Section card wrapper ────────────────────────────────────
type SectionCardProps = {
  title: string;
  children: React.ReactNode;
  collapsible?: boolean;
  defaultOpen?: boolean;
  summary?: React.ReactNode;
};

export function SectionCard({
  title,
  children,
  collapsible = false,
  defaultOpen = true,
  summary,
}: SectionCardProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="rounded-2xl border border-zinc-200/60 bg-white p-5">
      {collapsible ? (
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-center gap-2 text-left"
        >
          {open ? (
            <ChevronDown className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
          )}
          <p className="text-[12px] font-semibold tracking-wider text-zinc-500 uppercase">
            {title}
          </p>
          {!open && summary && (
            <span className="ml-auto truncate text-xs text-zinc-400">{summary}</span>
          )}
        </button>
      ) : (
        <p className="mb-4 text-[12px] font-semibold tracking-wider text-zinc-500 uppercase">
          {title}
        </p>
      )}
      {(!collapsible || open) && <div className={collapsible ? "mt-4" : ""}>{children}</div>}
    </div>
  );
}

// ── Basic Info ───────────────────────────────────────────────
type BasicInfoProps = { form: CharacterFormData; onChange: FormOnChange };

export function BasicInfoSection({ form, onChange }: BasicInfoProps) {
  return (
    <SectionCard title="Basic Info">
      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-500">Name</label>
          <Input
            value={form.name}
            onChange={(e) => onChange("name", e.target.value)}
            placeholder="Character name"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-500">Description</label>
          <Textarea
            value={form.description}
            onChange={(e) => onChange("description", e.target.value)}
            placeholder="Short description..."
            rows={2}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-500">Gender</label>
          <div className="flex gap-2">
            {(["female", "male"] as ActorGender[]).map((g) => (
              <button
                key={g}
                onClick={() => onChange("gender", g)}
                className={`rounded-full px-4 py-1.5 text-xs font-medium transition ${
                  form.gender === g
                    ? "bg-zinc-900 text-white"
                    : "bg-zinc-100 text-zinc-500 hover:bg-zinc-200"
                }`}
              >
                {g === "female" ? "Female" : "Male"}
              </button>
            ))}
          </div>
        </div>
      </div>
    </SectionCard>
  );
}

// ── Voice Preset ────────────────────────────────────────────
type VoicePresetProps = { form: CharacterFormData; onChange: FormOnChange };

export function VoicePresetSection({ form, onChange }: VoicePresetProps) {
  return (
    <VoicePresetSelector
      value={form.voice_preset_id}
      onChange={(id) => onChange("voice_preset_id", id)}
      label="Voice Preset"
    />
  );
}

// ── IP-Adapter ──────────────────────────────────────────────
const IP_ADAPTER_MODELS = ["clip_face", "clip", "faceid"] as const;

type IpAdapterProps = { form: CharacterFormData; onChange: FormOnChange };

export function IpAdapterSection({ form, onChange }: IpAdapterProps) {
  return (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-xs font-medium text-zinc-500">
          Weight ({form.ip_adapter_weight.toFixed(2)})
        </label>
        <input
          type="range"
          min={0}
          max={1.5}
          step={0.05}
          value={form.ip_adapter_weight}
          onChange={(e) => onChange("ip_adapter_weight", parseFloat(e.target.value))}
          className="w-full accent-zinc-700"
        />
        <div className="mt-0.5 flex justify-between text-[11px] text-zinc-400">
          <span>0</span>
          <span>1.5</span>
        </div>
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-zinc-500">Model</label>
        <div className="flex gap-2">
          {IP_ADAPTER_MODELS.map((m) => (
            <button
              key={m}
              onClick={() => onChange("ip_adapter_model", m)}
              className={`rounded-full px-4 py-1.5 text-xs font-medium transition ${
                form.ip_adapter_model === m
                  ? "bg-zinc-900 text-white"
                  : "bg-zinc-100 text-zinc-500 hover:bg-zinc-200"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Prompts (editable) ───────────────────────────────────────
type PromptsProps = {
  form: CharacterFormData;
  onChange: FormOnChange;
  selectedTagNames?: string[];
};

export function PromptsSection({ form, onChange, selectedTagNames = [] }: PromptsProps) {
  const duplicates = useMemo(
    () => findDuplicateTokens(form.custom_base_prompt, selectedTagNames),
    [form.custom_base_prompt, selectedTagNames]
  );

  return (
    <div className="space-y-5">
      <div>
        <label className="mb-1 block text-xs font-medium text-zinc-500">Prompt Mode</label>
        <div className="flex gap-2">
          {(["auto", "standard", "lora"] as PromptMode[]).map((m) => (
            <button
              key={m}
              onClick={() => onChange("prompt_mode", m)}
              className={`rounded-full px-4 py-1.5 text-xs font-medium capitalize transition ${
                form.prompt_mode === m
                  ? "bg-zinc-900 text-white"
                  : "bg-zinc-100 text-zinc-500 hover:bg-zinc-200"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>
      <hr className="border-zinc-100" />
      <PromptPair
        label="Custom (appended to auto-generated tags)"
        positiveValue={form.custom_base_prompt}
        negativeValue={form.custom_negative_prompt}
        onPositiveChange={(v) => onChange("custom_base_prompt", v)}
        onNegativeChange={(v) => onChange("custom_negative_prompt", v)}
        positivePlaceholder="e.g. masterpiece, best quality, ..."
        negativePlaceholder="e.g. lowres, bad anatomy, ..."
      />
      {duplicates.length > 0 && (
        <p className="text-[11px] text-amber-600">
          {duplicates.length} tag{duplicates.length > 1 ? "s" : ""} already in Appearance:{" "}
          {duplicates.map((d) => formatTagName(d)).join(", ")}
        </p>
      )}
      <hr className="border-zinc-100" />
      <PromptPair
        label="Reference (IP-Adapter 레퍼런스 이미지 생성용)"
        positiveValue={form.reference_base_prompt}
        negativeValue={form.reference_negative_prompt}
        onPositiveChange={(v) => onChange("reference_base_prompt", v)}
        onNegativeChange={(v) => onChange("reference_negative_prompt", v)}
        positivePlaceholder="e.g. masterpiece, best quality, anime portrait, looking at viewer, clean background"
        negativePlaceholder="e.g. lowres, bad anatomy, multiple views, ..."
      />
    </div>
  );
}
