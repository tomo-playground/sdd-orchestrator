"use client";

import { useState, useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Music } from "lucide-react";
import { useUIStore } from "../../store/useUIStore";
import { useMusic } from "../../hooks/useMusic";
import MusicCard from "./MusicCard";
import MusicCardSkeleton from "./MusicCardSkeleton";
import Button from "../../components/ui/Button";
import ConfirmDialog, { useConfirm } from "../../components/ui/ConfirmDialog";
import EmptyState from "../../components/ui/EmptyState";
import { SkeletonGrid } from "../../components/ui/Skeleton";
import {
  PAGE_TITLE_CLASSES,
  SEARCH_INPUT_CLASSES,
  FORM_INPUT_COMPACT_CLASSES,
  FORM_LABEL_COMPACT_CLASSES,
} from "../../components/ui/variants";

/** Redirect /music → /library?tab=music */
export default function MusicPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/library?tab=music");
  }, [router]);
  return null;
}

export function MusicContent() {
  const showToast = useUIStore((s) => s.showToast);
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

  const inputCls = FORM_INPUT_COMPACT_CLASSES;
  const labelCls = FORM_LABEL_COMPACT_CLASSES;

  return (
    <div className="py-8">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className={PAGE_TITLE_CLASSES}>
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
          className={SEARCH_INPUT_CLASSES}
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
        <SkeletonGrid>{(i) => <MusicCardSkeleton key={i} />}</SkeletonGrid>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Music}
          title={presets.length === 0 ? "No music presets yet" : "No presets match your search"}
          description={
            presets.length === 0
              ? "Create a music preset to get started"
              : "Try a different search term"
          }
          action={
            presets.length === 0 ? (
              <Button size="sm" onClick={handleCreate}>
                + New Preset
              </Button>
            ) : undefined
          }
        />
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
