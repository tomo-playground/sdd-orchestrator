"use client";

import type { ActorGender, PromptMode } from "../../../types";
import Input from "../../../components/ui/Input";
import Textarea from "../../../components/ui/Textarea";

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
};

type FormOnChange = <K extends keyof CharacterFormData>(
  key: K,
  value: CharacterFormData[K]
) => void;

// ── Section card wrapper ────────────────────────────────────
function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-zinc-200/60 bg-white p-5">
      <p className="mb-4 text-[12px] font-semibold tracking-wider text-zinc-500 uppercase">
        {title}
      </p>
      {children}
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

// ── Prompts (editable) ───────────────────────────────────────
type PromptsProps = { form: CharacterFormData; onChange: FormOnChange };

// ── Shared prompt pair ────────────────────────────────────────
type PromptFormKey =
  | "custom_base_prompt"
  | "custom_negative_prompt"
  | "reference_base_prompt"
  | "reference_negative_prompt";

function PromptPair({
  label,
  positiveKey,
  negativeKey,
  positiveValue,
  negativeValue,
  onChange,
  positivePlaceholder,
  negativePlaceholder,
}: {
  label?: string;
  positiveKey: PromptFormKey;
  negativeKey: PromptFormKey;
  positiveValue: string;
  negativeValue: string;
  onChange: FormOnChange;
  positivePlaceholder: string;
  negativePlaceholder: string;
}) {
  return (
    <div className="space-y-3">
      {label && <p className="text-[11px] font-medium text-zinc-400">{label}</p>}
      <div>
        <label className="mb-1 block text-xs font-medium text-zinc-500">Positive Prompt</label>
        <Textarea
          value={positiveValue}
          onChange={(e) => onChange(positiveKey, e.target.value)}
          placeholder={positivePlaceholder}
          rows={3}
        />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-zinc-500">Negative Prompt</label>
        <Textarea
          value={negativeValue}
          onChange={(e) => onChange(negativeKey, e.target.value)}
          placeholder={negativePlaceholder}
          rows={3}
        />
      </div>
    </div>
  );
}

export function PromptsSection({ form, onChange }: PromptsProps) {
  return (
    <SectionCard title="Prompts">
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
          positiveKey="custom_base_prompt"
          negativeKey="custom_negative_prompt"
          positiveValue={form.custom_base_prompt}
          negativeValue={form.custom_negative_prompt}
          onChange={onChange}
          positivePlaceholder="e.g. masterpiece, best quality, ..."
          negativePlaceholder="e.g. lowres, bad anatomy, ..."
        />
        <hr className="border-zinc-100" />
        <PromptPair
          label="Reference (IP-Adapter 레퍼런스 이미지 생성용)"
          positiveKey="reference_base_prompt"
          negativeKey="reference_negative_prompt"
          positiveValue={form.reference_base_prompt}
          negativeValue={form.reference_negative_prompt}
          onChange={onChange}
          positivePlaceholder="e.g. masterpiece, best quality, anime portrait, looking at viewer, clean background"
          negativePlaceholder="e.g. lowres, bad anatomy, multiple views, ..."
        />
      </div>
    </SectionCard>
  );
}
