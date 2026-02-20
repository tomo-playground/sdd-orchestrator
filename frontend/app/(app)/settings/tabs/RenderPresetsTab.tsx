"use client";

import ConfirmDialog, { useConfirm } from "../../../components/ui/ConfirmDialog";
import { useUIStore } from "../../../store/useUIStore";
import { useRenderPresetsTab } from "../hooks/useRenderPresetsTab";
import {
  FORM_INPUT_COMPACT_CLASSES,
  FORM_LABEL_COMPACT_CLASSES,
} from "../../../components/ui/variants";

export default function RenderPresetsTab() {
  const showToast = useUIStore((s) => s.showToast);
  const { confirm, dialogProps } = useConfirm();
  const {
    presets,
    editing,
    editId,
    saving,
    fonts,
    overlays,
    handleCreate,
    handleEdit,
    handleDelete,
    handleSave,
    handleCancel,
    set,
  } = useRenderPresetsTab({ showToast, confirmDialog: confirm });

  const inputCls = FORM_INPUT_COMPACT_CLASSES;
  const labelCls = FORM_LABEL_COMPACT_CLASSES;

  return (
    <section className="grid gap-6 rounded-2xl border border-zinc-200/60 bg-white p-8 text-xs text-zinc-600 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
        <span className="text-[12px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
          Render Presets ({presets.length})
        </span>
        <button
          onClick={handleCreate}
          className="rounded-full bg-zinc-900 px-4 py-1.5 text-[12px] font-bold text-white shadow transition hover:bg-zinc-700"
        >
          + New Preset
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
                  <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-500">
                    System
                  </span>
                )}
              </div>
              <div className="mt-0.5 truncate text-[12px] text-zinc-400">
                {[
                  p.layout_style,
                  p.bgm_mode ? `BGM: ${p.bgm_mode}` : null,
                  p.bgm_volume != null ? `vol ${p.bgm_volume}` : null,
                  p.transition_type,
                  p.speed_multiplier != null && p.speed_multiplier !== 1.0
                    ? `${p.speed_multiplier}x`
                    : null,
                  p.ken_burns_preset && p.ken_burns_preset !== "none"
                    ? `KB: ${p.ken_burns_preset}`
                    : null,
                ]
                  .filter(Boolean)
                  .join(" / ")}
              </div>
            </div>
            <div className="ml-3 flex items-center gap-2">
              <button
                onClick={() => handleEdit(p)}
                className="rounded-full border border-zinc-200 px-3 py-1 text-[12px] font-medium text-zinc-600 transition hover:bg-zinc-100"
              >
                Edit
              </button>
              <button
                onClick={() => handleDelete(p)}
                className="rounded-full border border-red-200 px-3 py-1 text-[12px] font-medium text-red-500 transition hover:bg-red-50"
              >
                Del
              </button>
            </div>
          </div>
        ))}
        {presets.length === 0 && <p className="py-8 text-center text-zinc-400">No presets found</p>}
      </div>

      {/* Edit / Create Form */}
      {editing && (
        <div className="space-y-4 rounded-xl border border-zinc-200 bg-zinc-50/50 p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-zinc-700">
              {editId ? "Edit Preset" : "New Preset"}
            </span>
            <button
              onClick={handleCancel}
              className="text-[12px] text-zinc-400 hover:text-zinc-600"
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
                placeholder="Preset name"
              />
            </div>
            <div className="col-span-2">
              <label className={labelCls}>Description</label>
              <input
                value={editing.description ?? ""}
                onChange={(e) => set("description", e.target.value)}
                className={inputCls}
                placeholder="Optional"
              />
            </div>
            <div>
              <label className={labelCls}>Layout Style</label>
              <select
                value={editing.layout_style ?? "post"}
                onChange={(e) => set("layout_style", e.target.value)}
                className={inputCls}
              >
                <option value="post">Post</option>
                <option value="full">Full</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>BGM Mode</label>
              <select
                value={editing.bgm_mode ?? "manual"}
                onChange={(e) => set("bgm_mode", e.target.value)}
                className={inputCls}
              >
                <option value="manual">Manual</option>
                <option value="auto">Auto</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>BGM Volume</label>
              <input
                type="number"
                min={0}
                max={1}
                step={0.05}
                value={editing.bgm_volume ?? 0.25}
                onChange={(e) => set("bgm_volume", +e.target.value)}
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>Audio Ducking</label>
              <select
                value={editing.audio_ducking ? "true" : "false"}
                onChange={(e) => set("audio_ducking", e.target.value === "true")}
                className={inputCls}
              >
                <option value="true">Enabled</option>
                <option value="false">Disabled</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>Scene Text Font</label>
              <select
                value={editing.scene_text_font ?? ""}
                onChange={(e) => set("scene_text_font", e.target.value)}
                className={inputCls}
              >
                <option value="">-- Default --</option>
                {fonts.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelCls}>Frame Style</label>
              <select
                value={editing.frame_style ?? ""}
                onChange={(e) => set("frame_style", e.target.value)}
                className={inputCls}
              >
                <option value="">-- None --</option>
                {overlays.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelCls}>Transition</label>
              <select
                value={editing.transition_type ?? "random"}
                onChange={(e) => set("transition_type", e.target.value)}
                className={inputCls}
              >
                {[
                  "fade",
                  "dissolve",
                  "wipeleft",
                  "wiperight",
                  "slideup",
                  "slidedown",
                  "pixelize",
                  "radial",
                  "none",
                  "random",
                ].map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelCls}>Ken Burns Preset</label>
              <select
                value={editing.ken_burns_preset ?? "random"}
                onChange={(e) => set("ken_burns_preset", e.target.value)}
                className={inputCls}
              >
                {[
                  "none",
                  "slow_zoom",
                  "zoom_in_center",
                  "zoom_out_center",
                  "pan_left",
                  "pan_right",
                  "pan_up",
                  "pan_down",
                  "random",
                ].map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelCls}>Ken Burns Intensity</label>
              <input
                type="number"
                min={0.5}
                max={2.0}
                step={0.1}
                value={editing.ken_burns_intensity ?? 1.0}
                onChange={(e) => set("ken_burns_intensity", +e.target.value)}
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>Speed Multiplier</label>
              <input
                type="number"
                min={0.5}
                max={3.0}
                step={0.1}
                value={editing.speed_multiplier ?? 1.0}
                onChange={(e) => set("speed_multiplier", +e.target.value)}
                className={inputCls}
              />
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={handleSave}
              disabled={saving || !editing.name.trim()}
              className="rounded-full bg-zinc-900 px-5 py-1.5 text-[12px] font-bold text-white shadow transition hover:bg-zinc-700 disabled:opacity-40"
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
