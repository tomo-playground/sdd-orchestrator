"use client";

import { useState, useEffect, useMemo } from "react";
import axios from "axios";
import { useStudioStore } from "../../store/useStudioStore";
import { useVoicePresets } from "../../hooks/useVoicePresets";
import { API_BASE } from "../../constants";
import VoiceCard from "./VoiceCard";
import Button from "../../components/ui/Button";
import ConfirmDialog, { useConfirm } from "../../components/ui/ConfirmDialog";
import { CONTAINER_CLASSES } from "../../components/ui/variants";

export default function VoicesPage() {
  const showToast = useStudioStore((s) => s.showToast);
  const { confirm, dialogProps } = useConfirm();
  const {
    presets,
    isLoading,
    editing,
    editId,
    saving,
    previewing,
    previewUrl,
    handleCreate,
    handleEdit,
    handleDelete,
    handlePreview,
    handleSave,
    handleCancel,
    playAudio,
    set,
  } = useVoicePresets({ showToast, confirmDialog: confirm });

  const [search, setSearch] = useState("");
  const [languages, setLanguages] = useState<{ value: string; label: string }[]>([]);

  useEffect(() => {
    axios
      .get(`${API_BASE}/presets`)
      .then((res) => {
        if (Array.isArray(res.data?.languages)) setLanguages(res.data.languages);
      })
      .catch(() => {});
  }, []);

  const filtered = useMemo(() => {
    if (!search.trim()) return presets;
    const q = search.toLowerCase();
    return presets.filter(
      (p) => p.name.toLowerCase().includes(q) || p.description?.toLowerCase().includes(q)
    );
  }, [presets, search]);

  const inputCls =
    "w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-800 focus:border-zinc-400 focus:outline-none";
  const labelCls = "text-[10px] font-semibold uppercase tracking-wider text-zinc-400";

  return (
    <div className={`${CONTAINER_CLASSES} py-8`}>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-lg font-bold text-zinc-900">
          Voices{presets.length > 0 ? ` (${presets.length})` : ""}
        </h1>
        <Button size="sm" onClick={handleCreate}>
          + Generate Voice
        </Button>
      </div>

      {/* Search */}
      <div className="mb-6">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search voices..."
          className="w-full max-w-sm rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
        />
      </div>

      {/* Inline Form */}
      {editing && (
        <div className="mb-6 space-y-4 rounded-2xl border border-zinc-200/60 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-sm font-bold text-zinc-700">
              {editId ? "Edit Voice Preset" : "Generate Voice Preset"}
            </span>
            <button onClick={handleCancel} className="text-xs text-zinc-400 hover:text-zinc-600">
              Cancel
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className={labelCls}>Name *</label>
              <input
                value={editing.name}
                onChange={(e) => set("name", e.target.value)}
                className={inputCls}
                placeholder="Preset name"
              />
            </div>
            <div className="col-span-2">
              <label className={labelCls}>Description</label>
              <input
                value={editing.description}
                onChange={(e) => set("description", e.target.value)}
                className={inputCls}
                placeholder="Optional"
              />
            </div>
            {!editId && (
              <>
                <div className="col-span-2">
                  <label className={labelCls}>Voice Design Prompt *</label>
                  <input
                    value={editing.voice_design_prompt}
                    onChange={(e) => set("voice_design_prompt", e.target.value)}
                    className={inputCls}
                    placeholder="e.g. calm 40s female narrator"
                  />
                </div>
                <div className="col-span-2">
                  <label className={labelCls}>Sample Text</label>
                  <input
                    value={editing.sample_text}
                    onChange={(e) => set("sample_text", e.target.value)}
                    className={inputCls}
                    placeholder="Text to preview the voice with"
                  />
                </div>
                <div>
                  <label className={labelCls}>Language</label>
                  <select
                    value={editing.language}
                    onChange={(e) => set("language", e.target.value)}
                    className={inputCls}
                  >
                    {languages.map((l) => (
                      <option key={l.value} value={l.value}>
                        {l.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex items-end gap-2">
                  <Button
                    size="sm"
                    variant="gradient"
                    onClick={handlePreview}
                    disabled={previewing || !editing.voice_design_prompt?.trim()}
                    loading={previewing}
                  >
                    Preview
                  </Button>
                  {previewUrl && (
                    <Button size="sm" variant="outline" onClick={() => playAudio(previewUrl)}>
                      Play Preview
                    </Button>
                  )}
                </div>
              </>
            )}
          </div>

          <div className="flex justify-end pt-2">
            <Button
              size="sm"
              onClick={handleSave}
              disabled={saving || !editing.name.trim()}
              loading={saving}
            >
              {editId ? "Save" : "Create"}
            </Button>
          </div>
        </div>
      )}

      {/* Card grid */}
      {isLoading ? (
        <div className="py-16 text-center text-sm text-zinc-400">Loading voices...</div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center gap-4 py-16 text-center">
          <p className="text-sm font-medium text-zinc-500">
            {presets.length === 0 ? "No voice presets yet" : "No voices match your search"}
          </p>
          <p className="text-xs text-zinc-400">
            {presets.length === 0
              ? "Generate a voice preset to get started"
              : "Try a different search term"}
          </p>
          {presets.length === 0 && (
            <Button size="sm" onClick={handleCreate}>
              + Generate Voice
            </Button>
          )}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((p) => (
            <VoiceCard
              key={p.id}
              preset={p}
              onPlay={playAudio}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
