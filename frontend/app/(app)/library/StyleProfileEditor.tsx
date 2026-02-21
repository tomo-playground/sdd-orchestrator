"use client";

import {
  useState,
  useEffect,
  useRef,
  type InputHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import Link from "next/link";
import type { StyleProfileFull, SDModelEntry, LoRA, Embedding, Character } from "../../types";
import { FORM_LABEL_COMPACT_CLASSES, ERROR_TEXT } from "../../components/ui/variants";

const DEBOUNCE_MS = 400;

/** Input that keeps local state and debounces onChange calls. */
function DebouncedInput({
  value: externalValue,
  onDebouncedChange,
  ...props
}: Omit<InputHTMLAttributes<HTMLInputElement>, "onChange"> & {
  value: string;
  onDebouncedChange: (v: string) => void;
}) {
  const [local, setLocal] = useState(externalValue);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => {
    setLocal(externalValue);
  }, [externalValue]);
  useEffect(() => () => clearTimeout(timerRef.current), []);
  return (
    <input
      {...props}
      value={local}
      onChange={(e) => {
        setLocal(e.target.value);
        clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => onDebouncedChange(e.target.value), DEBOUNCE_MS);
      }}
    />
  );
}

/** Textarea that keeps local state and debounces onChange calls. */
function DebouncedTextarea({
  value: externalValue,
  onDebouncedChange,
  ...props
}: Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "onChange"> & {
  value: string;
  onDebouncedChange: (v: string) => void;
}) {
  const [local, setLocal] = useState(externalValue);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => {
    setLocal(externalValue);
  }, [externalValue]);
  useEffect(() => () => clearTimeout(timerRef.current), []);
  return (
    <textarea
      {...props}
      value={local}
      onChange={(e) => {
        setLocal(e.target.value);
        clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => onDebouncedChange(e.target.value), DEBOUNCE_MS);
      }}
    />
  );
}

type Props = {
  profile: StyleProfileFull;
  sdModels: SDModelEntry[];
  loraEntries: LoRA[];
  embeddings: Embedding[];
  linkedCharacters: Character[];
  selectedBaseModel?: string | null;
  onUpdateStyle: (id: number, data: Record<string, unknown>) => void;
  onSetModel: (profileId: number, modelId: number | null) => void;
  onToggleLora: (profileId: number, loraId: number, weight?: number) => void;
  onToggleEmbedding: (
    profileId: number,
    embeddingId: number,
    type: "positive" | "negative"
  ) => void;
  onClose: () => void;
};

const labelCls = FORM_LABEL_COMPACT_CLASSES;

export default function StyleProfileEditor({
  profile,
  sdModels,
  loraEntries,
  embeddings,
  linkedCharacters,
  selectedBaseModel,
  onUpdateStyle,
  onSetModel,
  onToggleLora,
  onToggleEmbedding,
  onClose,
}: Props) {
  const activeLoraIds = new Set(profile.loras?.map((l) => l.id) ?? []);
  const posEmbIds = new Set(profile.positive_embeddings?.map((e) => e.id) ?? []);
  const negEmbIds = new Set(profile.negative_embeddings?.map((e) => e.id) ?? []);

  return (
    <div className="rounded-2xl border border-indigo-200 bg-white p-6 shadow-sm ring-4 ring-indigo-50/50">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between border-b border-indigo-50 pb-4">
        <div>
          <DebouncedInput
            type="text"
            value={profile.name}
            onDebouncedChange={(v) => onUpdateStyle(profile.id, { name: v })}
            className="bg-transparent text-lg font-black text-indigo-900 focus:outline-none"
          />
          <p className="mt-1 text-[12px] font-bold tracking-widest text-indigo-400 uppercase">
            Editing Style ID #{profile.id}
          </p>
        </div>
        <button
          onClick={onClose}
          className="rounded-full bg-indigo-50 px-4 py-1.5 text-[12px] font-bold text-indigo-500 hover:bg-indigo-100"
        >
          Done
        </button>
      </div>

      {/* Metadata: display_name, description, is_default */}
      <div className="mb-6 grid gap-4 md:grid-cols-[1fr_1fr_auto]">
        <div className="space-y-1">
          <label className={labelCls}>Display Name</label>
          <DebouncedInput
            type="text"
            value={profile.display_name || ""}
            onDebouncedChange={(v) => onUpdateStyle(profile.id, { display_name: v || null })}
            placeholder="Optional display name"
            className="w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-700 outline-none focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100"
          />
        </div>
        <div className="space-y-1">
          <label className={labelCls}>Description</label>
          <DebouncedInput
            type="text"
            value={profile.description || ""}
            onDebouncedChange={(v) => onUpdateStyle(profile.id, { description: v || null })}
            placeholder="Short description"
            className="w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-700 outline-none focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100"
          />
        </div>
        <div className="flex items-end pb-0.5">
          <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2">
            <input
              type="checkbox"
              checked={profile.is_default}
              onChange={(e) => onUpdateStyle(profile.id, { is_default: e.target.checked })}
              className="h-3.5 w-3.5 rounded accent-indigo-600"
            />
            <span className="text-xs font-bold text-zinc-600">Default</span>
          </label>
        </div>
      </div>

      {/* Prompts */}
      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-2">
          <label className={labelCls}>Positive Prompt</label>
          <DebouncedTextarea
            value={profile.default_positive || ""}
            onDebouncedChange={(v) => onUpdateStyle(profile.id, { default_positive: v })}
            className="h-40 w-full rounded-xl border border-zinc-200 bg-zinc-50 p-3 text-xs leading-relaxed text-zinc-700 outline-none focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100"
            placeholder="Describe the style..."
          />
        </div>
        <div className="space-y-2">
          <label className={labelCls}>Negative Prompt</label>
          <DebouncedTextarea
            value={profile.default_negative || ""}
            onDebouncedChange={(v) => onUpdateStyle(profile.id, { default_negative: v })}
            className="h-40 w-full rounded-xl border border-zinc-200 bg-zinc-50 p-3 text-xs leading-relaxed text-zinc-700 outline-none focus:border-rose-300 focus:ring-2 focus:ring-rose-100"
            placeholder="What to avoid..."
          />
        </div>
      </div>

      {/* SD Model */}
      <div className="mt-6 space-y-2">
        <label className={labelCls}>SD Model (Checkpoint)</label>
        <select
          value={profile.sd_model?.id ?? ""}
          onChange={(e) => {
            const v = e.target.value;
            onSetModel(profile.id, v ? Number(v) : null);
          }}
          className="w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-700 outline-none focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100"
        >
          <option value="">-- None --</option>
          {sdModels.map((m) => (
            <option key={m.id} value={m.id}>
              {m.display_name || m.name}
            </option>
          ))}
        </select>
      </div>

      {/* LoRAs */}
      <div className="mt-6 space-y-2">
        <div>
          <label className={labelCls}>LoRAs</label>
          {selectedBaseModel && (
            <p className="text-[11px] text-zinc-400">
              Filtered by {selectedBaseModel} · style only
            </p>
          )}
        </div>
        <div className="custom-scrollbar max-h-48 overflow-y-auto rounded-xl border border-zinc-200 bg-zinc-50 p-3">
          {loraEntries.length === 0 && (
            <p className="text-[12px] text-zinc-400">No LoRAs registered</p>
          )}
          {loraEntries.map((lora) => {
            const active = activeLoraIds.has(lora.id!);
            const linked = profile.loras?.find((l) => l.id === lora.id);
            return (
              <div
                key={lora.id}
                className="flex items-center gap-3 rounded-lg p-1.5 transition hover:bg-white"
              >
                <input
                  type="checkbox"
                  checked={active}
                  onChange={() => onToggleLora(profile.id, lora.id!)}
                  className="h-3.5 w-3.5 rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="min-w-0 flex-1 truncate text-xs font-medium text-zinc-700">
                  {lora.display_name || lora.name}
                </span>
                {active && (
                  <input
                    type="number"
                    step="0.1"
                    min="0.1"
                    max="2.0"
                    value={linked?.weight ?? lora.default_weight}
                    onChange={(e) => {
                      const w = parseFloat(e.target.value);
                      if (!isNaN(w)) onToggleLora(profile.id, lora.id!, w);
                    }}
                    className="w-16 rounded-lg border border-zinc-200 bg-white px-2 py-1 text-center text-[12px] font-bold text-zinc-600 outline-none focus:border-indigo-300"
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Embeddings */}
      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <div className="space-y-2">
          <div>
            <label className={labelCls}>Positive Embeddings</label>
            {selectedBaseModel && (
              <p className="text-[11px] text-zinc-400">Filtered by {selectedBaseModel}</p>
            )}
          </div>
          <div className="custom-scrollbar max-h-40 overflow-y-auto rounded-xl border border-zinc-200 bg-zinc-50 p-3">
            {embeddings.length === 0 && (
              <p className="text-[12px] text-zinc-400">No embeddings registered</p>
            )}
            {embeddings.map((emb) => (
              <label
                key={emb.id}
                className="flex cursor-pointer items-center gap-2 rounded-lg p-1.5 transition hover:bg-white"
              >
                <input
                  type="checkbox"
                  checked={posEmbIds.has(emb.id)}
                  onChange={() => onToggleEmbedding(profile.id, emb.id, "positive")}
                  className="h-3.5 w-3.5 rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="text-xs text-zinc-700">{emb.display_name || emb.name}</span>
              </label>
            ))}
          </div>
        </div>
        <div className="space-y-2">
          <div>
            <label className={labelCls}>Negative Embeddings</label>
            {selectedBaseModel && (
              <p className="text-[11px] text-zinc-400">Filtered by {selectedBaseModel}</p>
            )}
          </div>
          <div className="custom-scrollbar max-h-40 overflow-y-auto rounded-xl border border-zinc-200 bg-zinc-50 p-3">
            {embeddings.length === 0 && (
              <p className="text-[12px] text-zinc-400">No embeddings registered</p>
            )}
            {embeddings.map((emb) => (
              <label
                key={emb.id}
                className="flex cursor-pointer items-center gap-2 rounded-lg p-1.5 transition hover:bg-white"
              >
                <input
                  type="checkbox"
                  checked={negEmbIds.has(emb.id)}
                  onChange={() => onToggleEmbedding(profile.id, emb.id, "negative")}
                  className={`h-3.5 w-3.5 rounded border-zinc-300 ${ERROR_TEXT} focus:ring-red-500`}
                />
                <span className="text-xs text-zinc-700">{emb.display_name || emb.name}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Linked Characters */}
      <div className="mt-6 space-y-2">
        <label className={labelCls}>Linked Characters</label>
        {linkedCharacters.length === 0 ? (
          <p className="text-[12px] text-zinc-400">No characters linked to this style</p>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {linkedCharacters.map((ch) => (
              <Link
                key={ch.id}
                href={`/characters/${ch.id}`}
                className="flex items-center gap-3 rounded-xl border border-zinc-200 bg-zinc-50 p-2.5 transition hover:border-indigo-200 hover:bg-white"
              >
                {ch.preview_image_url ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={ch.preview_image_url}
                    alt={ch.name}
                    className="h-8 w-8 shrink-0 rounded-lg object-cover"
                  />
                ) : (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-zinc-200 text-[11px] font-bold text-zinc-500">
                    {ch.name.charAt(0).toUpperCase()}
                  </div>
                )}
                <span className="min-w-0 truncate text-xs font-bold text-zinc-700">{ch.name}</span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
