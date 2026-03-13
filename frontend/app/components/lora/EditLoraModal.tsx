"use client";

import type { ActorGender, LoRA } from "../../types";

type Props = {
  lora: LoRA;
  onChange: (lora: LoRA) => void;
  onSave: () => void;
  onClose: () => void;
  isSaving: boolean;
};

export default function EditLoraModal({ lora, onChange, onSave, onClose, isSaving }: Props) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-lora-title"
      className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
    >
      <div className="w-full max-w-sm rounded-3xl bg-white p-6 shadow-2xl">
        <h3 id="edit-lora-title" className="mb-4 text-center text-sm font-black text-zinc-800">
          Edit LoRA
        </h3>
        <div className="grid gap-4">
          <div>
            <label className="mb-1 block text-[13px] font-bold tracking-wider text-zinc-500 uppercase">
              Name
            </label>
            <input
              value={lora.name}
              onChange={(e) => onChange({ ...lora, name: e.target.value })}
              className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-xs font-bold text-zinc-700 outline-none focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-[13px] font-bold tracking-wider text-zinc-500 uppercase">
              Trigger Word (Optional)
            </label>
            <input
              value={lora.trigger_words?.join(", ") || ""}
              onChange={(e) =>
                onChange({
                  ...lora,
                  trigger_words: e.target.value.split(",").map((s) => s.trim()),
                })
              }
              className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-xs font-bold text-zinc-700 outline-none focus:border-indigo-500"
              placeholder="e.g. style-pixel"
            />
          </div>
          <div>
            <label className="mb-1 block text-[13px] font-bold tracking-wider text-zinc-500 uppercase">
              Default Weight: {lora.default_weight.toFixed(1)}
            </label>
            <input
              type="range"
              min="0.1"
              max="2.0"
              step="0.1"
              value={lora.default_weight ?? 1.0}
              onChange={(e) => onChange({ ...lora, default_weight: parseFloat(e.target.value) })}
              className="w-full"
            />
          </div>
          <div>
            <label className="mb-1 block text-[13px] font-bold tracking-wider text-zinc-500 uppercase">
              Gender Lock
            </label>
            <select
              value={lora.gender_locked ?? ""}
              onChange={(e) =>
                onChange({
                  ...lora,
                  gender_locked: (e.target.value as ActorGender) || null,
                })
              }
              className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-xs font-bold text-zinc-700 outline-none focus:border-indigo-500"
            >
              <option value="">Any</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
            </select>
          </div>
          {/* Multi-Character Support */}
          <div className="rounded-xl border border-zinc-100 bg-zinc-50/50 p-3">
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={lora.is_multi_character_capable ?? false}
                onChange={(e) =>
                  onChange({ ...lora, is_multi_character_capable: e.target.checked })
                }
                className="h-3.5 w-3.5 rounded accent-emerald-600"
              />
              <span className="text-[13px] font-bold text-zinc-600">Multi-Character Capable</span>
            </label>
            {lora.is_multi_character_capable && (
              <div className="mt-3 grid gap-3">
                <div>
                  <label className="mb-1 block text-[13px] font-bold tracking-wider text-zinc-500 uppercase">
                    Weight Scale: {(lora.multi_char_weight_scale ?? 0.75).toFixed(2)}
                  </label>
                  <input
                    type="range"
                    min="0.3"
                    max="1.0"
                    step="0.05"
                    value={lora.multi_char_weight_scale ?? 0.75}
                    onChange={(e) =>
                      onChange({
                        ...lora,
                        multi_char_weight_scale: parseFloat(e.target.value),
                      })
                    }
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-[13px] font-bold tracking-wider text-zinc-500 uppercase">
                    Trigger Prompt
                  </label>
                  <input
                    value={lora.multi_char_trigger_prompt ?? ""}
                    onChange={(e) =>
                      onChange({
                        ...lora,
                        multi_char_trigger_prompt: e.target.value || null,
                      })
                    }
                    className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-xs text-zinc-700 outline-none focus:border-emerald-500"
                    placeholder="e.g. a boy and a girl"
                  />
                </div>
              </div>
            )}
          </div>
          <div className="flex gap-2 pt-2">
            <button
              type="button"
              aria-label="Close dialog"
              onClick={onClose}
              className="flex-1 rounded-xl border border-zinc-200 py-2.5 text-[13px] font-bold text-zinc-500 hover:bg-zinc-50"
            >
              Cancel
            </button>
            <button
              onClick={onSave}
              disabled={isSaving}
              className="flex-1 rounded-xl bg-indigo-600 py-2.5 text-[13px] font-bold text-white shadow-lg shadow-indigo-200 hover:bg-indigo-700 disabled:opacity-50"
            >
              {isSaving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
