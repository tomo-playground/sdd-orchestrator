"use client";

import ConfirmDialog, { useConfirm } from "../../../components/ui/ConfirmDialog";
import { useStudioStore } from "../../../store/useStudioStore";
import { useMusicPresetsTab } from "../hooks/useMusicPresetsTab";

export default function MusicPresetsTab() {
  const showToast = useStudioStore((s) => s.showToast);
  const { confirm, dialogProps } = useConfirm();
  const {
    presets,
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
  } = useMusicPresetsTab({ showToast, confirmDialog: confirm });

  const inputCls =
    "w-full rounded border border-zinc-200 bg-white px-2.5 py-1.5 text-[11px] text-zinc-800 focus:border-zinc-400 focus:outline-none";
  const labelCls = "text-[10px] font-semibold uppercase tracking-wider text-zinc-400";

  return (
    <section className="grid gap-6 rounded-2xl border border-zinc-200/60 bg-white p-8 text-xs text-zinc-600 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
        <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
          Music Presets ({presets.length})
        </span>
        <button
          onClick={handleCreate}
          className="rounded-full bg-zinc-900 px-4 py-1.5 text-[10px] font-bold text-white shadow transition hover:bg-zinc-700"
        >
          + Create
        </button>
      </div>

      {/* List */}
      <div className="grid gap-3">
        {presets.map((p) => (
          <div
            key={p.id}
            className="flex items-center justify-between rounded-xl border border-zinc-100 px-4 py-3 transition hover:bg-zinc-50/50"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-zinc-800">{p.name}</span>
                {p.is_system && (
                  <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[9px] font-medium text-indigo-500">
                    System
                  </span>
                )}
              </div>
              {p.description && (
                <div className="mt-0.5 truncate text-[10px] text-zinc-400">{p.description}</div>
              )}
              {p.prompt && (
                <div className="mt-0.5 truncate text-[10px] text-zinc-400 italic">{p.prompt}</div>
              )}
            </div>
            <div className="ml-3 flex items-center gap-2">
              <button
                onClick={() => previewPreset(p)}
                disabled={previewingId === p.id || !p.prompt?.trim()}
                className={`rounded-full border px-3 py-1 text-[10px] font-medium transition ${
                  p.audio_url
                    ? "border-zinc-200 text-zinc-600 hover:bg-zinc-100"
                    : "border-indigo-200 text-indigo-600 hover:bg-indigo-50"
                } disabled:opacity-40`}
              >
                {previewingId === p.id
                  ? "Generating..."
                  : p.audio_url
                    ? playingId === p.id
                      ? "Stop"
                      : "Play"
                    : "Generate"}
              </button>
              <button
                onClick={() => handleEdit(p)}
                className="rounded-full border border-zinc-200 px-3 py-1 text-[10px] font-medium text-zinc-600 transition hover:bg-zinc-100"
              >
                Edit
              </button>
              <button
                onClick={() => handleDelete(p)}
                className="rounded-full border border-red-200 px-3 py-1 text-[10px] font-medium text-red-500 transition hover:bg-red-50"
              >
                Del
              </button>
            </div>
          </div>
        ))}
        {presets.length === 0 && (
          <p className="py-8 text-center text-zinc-400">No music presets. Create one.</p>
        )}
      </div>

      {/* Edit / Create Form */}
      {editing && (
        <div className="space-y-4 rounded-xl border border-zinc-200 bg-zinc-50/50 p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-zinc-700">
              {editId ? "Edit Music Preset" : "Create Music Preset"}
            </span>
            <button
              onClick={handleCancel}
              className="text-[10px] text-zinc-400 hover:text-zinc-600"
            >
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
              <button
                onClick={handlePreview}
                disabled={previewing || !editing.prompt?.trim()}
                className="rounded-full bg-indigo-600 px-4 py-1.5 text-[10px] font-bold text-white shadow transition hover:bg-indigo-500 disabled:opacity-40"
              >
                {previewing ? "Generating..." : "Preview"}
              </button>
              {previewUrl && (
                <button
                  onClick={() => playAudio(previewUrl)}
                  className="rounded-full border border-indigo-200 px-3 py-1.5 text-[10px] font-medium text-indigo-600 transition hover:bg-indigo-50"
                >
                  Play Preview
                </button>
              )}
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={handleSave}
              disabled={saving || !editing.name.trim()}
              className="rounded-full bg-zinc-900 px-5 py-1.5 text-[10px] font-bold text-white shadow transition hover:bg-zinc-700 disabled:opacity-40"
            >
              {saving ? "Saving..." : editId ? "Save" : "Create"}
            </button>
          </div>
        </div>
      )}
      <ConfirmDialog {...dialogProps} />
    </section>
  );
}
