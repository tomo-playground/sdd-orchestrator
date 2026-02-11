"use client";

import { useState, useMemo } from "react";
import { Image } from "lucide-react";
import { useStudioStore } from "../../store/useStudioStore";
import { useBackgrounds } from "../../hooks/useBackgrounds";
import BackgroundCard from "./BackgroundCard";
import Button from "../../components/ui/Button";
import ConfirmDialog, { useConfirm } from "../../components/ui/ConfirmDialog";
import EmptyState from "../../components/ui/EmptyState";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import {
  CONTAINER_CLASSES,
  PAGE_TITLE_CLASSES,
  SEARCH_INPUT_CLASSES,
} from "../../components/ui/variants";

export default function BackgroundsPage() {
  const showToast = useStudioStore((s) => s.showToast);
  const { confirm, dialogProps } = useConfirm();
  const {
    backgrounds,
    categories,
    isLoading,
    editing,
    editId,
    saving,
    uploading,
    handleCreate,
    handleEdit,
    handleDelete,
    handleSave,
    handleCancel,
    handleUploadImage,
    set,
  } = useBackgrounds({ showToast, confirmDialog: confirm });

  const [search, setSearch] = useState("");
  const [filterCategory, setFilterCategory] = useState("");

  const filtered = useMemo(() => {
    let list = backgrounds;
    if (filterCategory) {
      list = list.filter((bg) => bg.category === filterCategory);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (bg) =>
          bg.name.toLowerCase().includes(q) ||
          bg.description?.toLowerCase().includes(q) ||
          bg.tags?.some((t) => t.toLowerCase().includes(q))
      );
    }
    return list;
  }, [backgrounds, search, filterCategory]);

  const inputCls =
    "w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-800 focus:border-zinc-400 focus:outline-none";
  const labelCls = "text-[10px] font-semibold uppercase tracking-wider text-zinc-400";

  return (
    <div className={`${CONTAINER_CLASSES} py-8`}>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className={PAGE_TITLE_CLASSES}>
          Backgrounds
          {backgrounds.length > 0 ? ` (${backgrounds.length})` : ""}
        </h1>
        <Button size="sm" onClick={handleCreate}>
          + Add Background
        </Button>
      </div>

      {/* Filters */}
      <div className="mb-6 flex gap-3">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search backgrounds..."
          className={`${SEARCH_INPUT_CLASSES} max-w-sm`}
        />
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-700 outline-none focus:border-zinc-400"
        >
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      {/* Inline Form */}
      {editing && (
        <div className="mb-6 space-y-4 rounded-2xl border border-zinc-200/60 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-sm font-bold text-zinc-700">
              {editId ? "Edit Background" : "New Background"}
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
                placeholder="Background name"
              />
            </div>
            <div className="col-span-2">
              <label className={labelCls}>Description</label>
              <input
                value={editing.description}
                onChange={(e) => set("description", e.target.value)}
                className={inputCls}
                placeholder="Optional description"
              />
            </div>
            <div>
              <label className={labelCls}>Category</label>
              <input
                value={editing.category}
                onChange={(e) => set("category", e.target.value)}
                className={inputCls}
                placeholder="e.g. indoor, outdoor, school"
              />
            </div>
            <div>
              <label className={labelCls}>Weight ({editing.weight.toFixed(2)})</label>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={editing.weight}
                onChange={(e) => set("weight", parseFloat(e.target.value))}
                className="mt-1 w-full"
              />
            </div>
            <div className="col-span-2">
              <label className={labelCls}>Tags (comma separated)</label>
              <input
                value={editing.tags}
                onChange={(e) => set("tags", e.target.value)}
                className={inputCls}
                placeholder="classroom, desk, window"
              />
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
        <div className="flex justify-center py-16">
          <LoadingSpinner size="md" />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Image}
          title={
            backgrounds.length === 0 ? "No backgrounds yet" : "No backgrounds match your filters"
          }
          description={
            backgrounds.length === 0
              ? "Add a background reference image to get started"
              : "Try different search or category"
          }
          action={
            backgrounds.length === 0 ? (
              <Button size="sm" onClick={handleCreate}>
                + Add Background
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((bg) => (
            <BackgroundCard
              key={bg.id}
              background={bg}
              uploading={uploading === bg.id}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onUpload={handleUploadImage}
            />
          ))}
        </div>
      )}

      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
