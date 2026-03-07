"use client";

import { useState, useMemo } from "react";
import { ChevronDown, ChevronRight, FolderOpen, Palette } from "lucide-react";
import type { ActorGender, GroupItem } from "../../../../types";
import Input from "../../../../components/ui/Input";
import Textarea from "../../../../components/ui/Textarea";
import { findDuplicateTokens } from "../shared/promptDuplicateCheck";
import { formatTagName } from "../shared/formatTag";
import PromptPair from "../shared/PromptPair";
import VoicePresetSelector from "../../../../components/voice/VoicePresetSelector";

// ── Shared form type ─────────────────────────────────────────
export type CharacterFormData = {
  name: string;
  description: string;
  gender: ActorGender | null;
  group_id: number | null;
  positive_prompt: string;
  negative_prompt: string;
  voice_preset_id: number | null;
  ip_adapter_weight: number;
  ip_adapter_model: string;
  ip_adapter_guidance_start: number | null;
  ip_adapter_guidance_end: number | null;
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
type BasicInfoProps = {
  form: CharacterFormData;
  onChange: FormOnChange;
  groups: GroupItem[];
  onGroupChange: (groupId: number) => void;
  currentStyleName?: string | null;
};

export function BasicInfoSection({
  form,
  onChange,
  groups,
  onGroupChange,
  currentStyleName,
}: BasicInfoProps) {
  return (
    <SectionCard title="Basic Info">
      <div className="space-y-3">
        {/* Series select */}
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-500">소속 시리즈</label>
          <div className="flex items-center gap-2">
            {groups.length > 0 ? (
              <select
                value={form.group_id ?? ""}
                onChange={(e) => {
                  const id = Number(e.target.value);
                  if (id) onGroupChange(id);
                }}
                className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs text-zinc-600 transition hover:border-zinc-300 focus:border-zinc-400 focus:outline-none"
              >
                {groups.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name}
                  </option>
                ))}
              </select>
            ) : (
              <span className="flex items-center gap-1.5 rounded-full bg-zinc-100 px-3 py-1.5 text-xs font-medium text-zinc-600">
                <FolderOpen className="h-3 w-3" />
                Loading...
              </span>
            )}
            {currentStyleName && (
              <span className="flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-600">
                <Palette className="h-3 w-3" />
                {currentStyleName}
              </span>
            )}
          </div>
        </div>
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

type IpAdapterProps = {
  form: CharacterFormData;
  onChange: FormOnChange;
  characterName?: string;
  onUploadPhoto?: (file: File) => void;
};

export function IpAdapterSection({ form, onChange, onUploadPhoto }: IpAdapterProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && onUploadPhoto) onUploadPhoto(file);
    e.target.value = "";
  };

  return (
    <div className="space-y-4">
      {/* Weight */}
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

      {/* Model */}
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

      {/* Upload Photo */}
      {onUploadPhoto && (
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-500">Photo Reference</label>
          <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-xs text-zinc-600 transition hover:bg-zinc-100">
            <span>Upload Photo</span>
            <input type="file" accept="image/*" className="hidden" onChange={handlePhotoSelect} />
          </label>
          <p className="mt-1 text-[11px] text-zinc-400">
            실사 사진 업로드 시 얼굴 자동 크롭 + 512x512 리사이즈
          </p>
        </div>
      )}

      {/* Advanced: Guidance */}
      <button
        onClick={() => setShowAdvanced((v) => !v)}
        className="flex items-center gap-1 text-[11px] text-zinc-400 hover:text-zinc-600"
      >
        {showAdvanced ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        Advanced
      </button>
      {showAdvanced && (
        <div className="space-y-3 rounded-lg border border-zinc-100 bg-zinc-50/50 p-3">
          <div>
            <label className="mb-1 block text-[11px] font-medium text-zinc-400">
              Guidance Start ({(form.ip_adapter_guidance_start ?? 0).toFixed(2)})
            </label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={form.ip_adapter_guidance_start ?? 0}
              onChange={(e) => onChange("ip_adapter_guidance_start", parseFloat(e.target.value))}
              className="w-full accent-zinc-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-medium text-zinc-400">
              Guidance End (
              {(
                form.ip_adapter_guidance_end ?? (form.ip_adapter_model === "faceid" ? 0.85 : 1.0)
              ).toFixed(2)}
              )
            </label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={
                form.ip_adapter_guidance_end ?? (form.ip_adapter_model === "faceid" ? 0.85 : 1.0)
              }
              onChange={(e) => onChange("ip_adapter_guidance_end", parseFloat(e.target.value))}
              className="w-full accent-zinc-500"
            />
          </div>
          <p className="text-[11px] text-zinc-400">
            FaceID 기본: 0.85 / CLIP 기본: 1.0 — 낮출수록 프롬프트 우선
          </p>
        </div>
      )}
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
    () => findDuplicateTokens(form.positive_prompt, selectedTagNames),
    [form.positive_prompt, selectedTagNames]
  );

  return (
    <div className="space-y-5">
      <PromptPair
        label="캐릭터 프롬프트 (씬·레퍼런스 공통 적용)"
        positiveValue={form.positive_prompt}
        negativeValue={form.negative_prompt}
        onPositiveChange={(v) => onChange("positive_prompt", v)}
        onNegativeChange={(v) => onChange("negative_prompt", v)}
        positivePlaceholder="DB 태그에 없는 추가 보정 태그 (선택사항)"
        negativePlaceholder="e.g. (red_sweater:1.3), (wings:1.3), very_long_hair, ..."
      />
      {duplicates.length > 0 && (
        <p className="text-[11px] text-amber-600">
          {duplicates.length} tag{duplicates.length > 1 ? "s" : ""} already in Appearance:{" "}
          {duplicates.map((d) => formatTagName(d)).join(", ")}
        </p>
      )}
    </div>
  );
}
