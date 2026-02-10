"use client";

import { Loader2, X, Check } from "lucide-react";

// ── Types ────────────────────────────────────────────────────

type PresetForm = {
  name: string;
  role_description: string;
  system_prompt: string;
  model_provider: string;
  model_name: string;
  temperature: number;
  agent_role: string;
  category: string;
};

type Props = {
  title: string;
  form: PresetForm;
  updateField: <K extends keyof PresetForm>(key: K, value: PresetForm[K]) => void;
  onSubmit: () => void;
  onCancel?: () => void;
  submitting: boolean;
  submitLabel: string;
  submitIcon?: "create" | "save";
};

// ── Component ────────────────────────────────────────────────

export default function PresetFormFields({
  title,
  form,
  updateField,
  onSubmit,
  onCancel,
  submitting,
  submitLabel,
  submitIcon = "create",
}: Props) {
  const isValid = form.name.trim() && form.role_description.trim();

  return (
    <div className="space-y-3">
      <p className="text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
        {title}
      </p>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
            Name
          </label>
          <input
            value={form.name}
            onChange={(e) => updateField("name", e.target.value)}
            placeholder="e.g. Creative Writer"
            className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
            Model Provider
          </label>
          <select
            value={form.model_provider}
            onChange={(e) => updateField("model_provider", e.target.value)}
            className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
          >
            <option value="gemini">Gemini</option>
            <option value="ollama">Ollama</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
            Model Name
          </label>
          <input
            value={form.model_name}
            onChange={(e) => updateField("model_name", e.target.value)}
            placeholder="gemini-2.0-flash"
            className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
            Temperature ({form.temperature.toFixed(2)})
          </label>
          <input
            type="range"
            min="0"
            max="2"
            step="0.05"
            value={form.temperature}
            onChange={(e) => updateField("temperature", parseFloat(e.target.value))}
            className="mt-1 w-full"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
            Agent Role
          </label>
          <input
            value={form.agent_role}
            onChange={(e) => updateField("agent_role", e.target.value)}
            placeholder="e.g. scriptwriter"
            className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
            Category
          </label>
          <select
            value={form.category}
            onChange={(e) => updateField("category", e.target.value)}
            className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
          >
            <option value="">None</option>
            <option value="v1_debate">V1 Debate</option>
            <option value="v2_concept">V2 Concept</option>
            <option value="v2_production">V2 Production</option>
          </select>
        </div>
      </div>

      <div>
        <label className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
          Role Description
        </label>
        <input
          value={form.role_description}
          onChange={(e) => updateField("role_description", e.target.value)}
          placeholder="Describe the agent's role..."
          className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
        />
      </div>

      <div>
        <label className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
          System Prompt
        </label>
        <textarea
          value={form.system_prompt}
          onChange={(e) => updateField("system_prompt", e.target.value)}
          rows={3}
          placeholder="System prompt for the agent..."
          className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
        />
      </div>

      <div className={`flex ${onCancel ? "justify-end gap-2" : "justify-end"}`}>
        {onCancel && (
          <button
            onClick={onCancel}
            className="flex items-center gap-1 rounded-lg border border-zinc-200 px-3 py-1.5 text-xs text-zinc-600 transition hover:bg-zinc-50"
          >
            <X className="h-3.5 w-3.5" /> Cancel
          </button>
        )}
        <button
          onClick={onSubmit}
          disabled={submitting || !isValid}
          className="flex items-center gap-1 rounded-lg bg-zinc-900 px-4 py-1.5 text-xs font-semibold text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
        >
          {submitting ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <>
              {submitIcon === "save" && <Check className="h-3.5 w-3.5" />}
              {submitLabel}
            </>
          )}
        </button>
      </div>
    </div>
  );
}
