"use client";

import { useState, useMemo } from "react";
import { useStudioStore } from "../../store/useStudioStore";
import { useMusic } from "../../hooks/useMusic";
import MusicCard from "./MusicCard";
import Button from "../../components/ui/Button";
import ConfirmDialog, { useConfirm } from "../../components/ui/ConfirmDialog";
import { CONTAINER_CLASSES } from "../../components/ui/variants";

export default function MusicPage() {
  const showToast = useStudioStore((s) => s.showToast);
  const { confirm, dialogProps } = useConfirm();
  const {
    presets,
    isLoading,
    editing,
    editId,
    saving,
    previewing,
    previewingId,
    playingId,
    previewUrl,
    handleCreate,
    handleEdit,
    handleDelete,
    handlePreview,
    handleSave,
    handleCancel,
    playAudio,
    previewPreset,
    set,
  } = useMusic({ showToast, confirmDialog: confirm });

  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!search.trim()) return presets;
    const q = search.toLowerCase();
    return presets.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.description?.toLowerCase().includes(q) ||
        p.prompt?.toLowerCase().includes(q)
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
          Music Presets{presets.length > 0 ? ` (${presets.length})` : ""}
        </h1>
        <Button size="sm" onClick={handleCreate}>
          + New Preset
        </Button>
      </div>

      {/* Search */}
      <div className="mb-6">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name or prompt..."
          className="w-full max-w-sm rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
        />
      </div>

      {/* Inline Form */}
      {editing && (
        <div className="mb-6 space-y-4 rounded-2xl border border-zinc-200/60 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-sm font-bold text-zinc-700">
              {editId ? "Edit Music Preset" : "Create Music Preset"}
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
                placeholder="Preset name (e.g. Lo-fi Chill)"
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
            <div className="col-span-2">
              <label className={labelCls}>Prompt *</label>
              <input
                value={editing.prompt}
                onChange={(e) => set("prompt", e.target.value)}
                className={inputCls}
                placeholder="e.g. ambient lo-fi hip hop, soft piano, chill beats"
              />
            </div>
            <div>
              <label className={labelCls}>Duration (sec)</label>
              <input
                type="number"
                min={5}
                max={47}
                step={1}
                value={editing.duration}
                onChange={(e) => set("duration", Number(e.target.value))}
                className={inputCls}
              />
            </div>
            <div className="flex items-end gap-2">
              <Button
                size="sm"
                variant="gradient"
                onClick={handlePreview}
                disabled={previewing || !editing.prompt?.trim()}
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
        <div className="py-16 text-center text-sm text-zinc-400">Loading music presets...</div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center gap-4 py-16 text-center">
          <p className="text-sm font-medium text-zinc-500">
            {presets.length === 0 ? "No music presets yet" : "No presets match your search"}
          </p>
          <p className="text-xs text-zinc-400">
            {presets.length === 0
              ? "Create a music preset to get started"
              : "Try a different search term"}
          </p>
          {presets.length === 0 && (
            <Button size="sm" onClick={handleCreate}>
              + New Preset
            </Button>
          )}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((p) => (
            <MusicCard
              key={p.id}
              preset={p}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onPreview={previewPreset}
              isPlaying={playingId === p.id}
              isGenerating={previewingId === p.id}
            />
          ))}
        </div>
      )}

      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
