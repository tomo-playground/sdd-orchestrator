"use client";

import { useState, useEffect, useMemo } from "react";
import axios from "axios";
import { Mic } from "lucide-react";
import { useUIStore } from "../../store/useUIStore";
import { useVoicePresets } from "../../hooks/useVoicePresets";
import { API_BASE } from "../../constants";
import VoiceCard from "./VoiceCard";
import Button from "../../components/ui/Button";
import ConfirmDialog, { useConfirm } from "../../components/ui/ConfirmDialog";
import EmptyState from "../../components/ui/EmptyState";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import {
  CONTAINER_CLASSES,
  PAGE_TITLE_CLASSES,
  SEARCH_INPUT_CLASSES,
  FORM_INPUT_COMPACT_CLASSES,
  FORM_LABEL_COMPACT_CLASSES,
} from "../../components/ui/variants";

export default function VoicesPage() {
  const showToast = useUIStore((s) => s.showToast);
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

  const inputCls = FORM_INPUT_COMPACT_CLASSES;
  const labelCls = FORM_LABEL_COMPACT_CLASSES;

  return (
    <div className={`${CONTAINER_CLASSES} py-8`}>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className={PAGE_TITLE_CLASSES}>
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
          className={SEARCH_INPUT_CLASSES}
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
        <div className="flex justify-center py-16">
          <LoadingSpinner size="md" />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Mic}
          title={presets.length === 0 ? "No voice presets yet" : "No voices match your search"}
          description={
            presets.length === 0
              ? "Generate a voice preset to get started"
              : "Try a different search term"
          }
          action={
            presets.length === 0 ? (
              <Button size="sm" onClick={handleCreate}>
                + Generate Voice
              </Button>
            ) : undefined
          }
        />
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
