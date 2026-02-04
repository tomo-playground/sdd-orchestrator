"use client";

import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import type { RenderPreset, VoicePreset } from "../../types";

type EditingPreset = Partial<RenderPreset> & { name: string };

const EMPTY_PRESET: EditingPreset = {
  name: "",
  description: "",
  bgm_file: "random",
  bgm_volume: 0.25,
  audio_ducking: true,
  scene_text_font: "",
  layout_style: "post",
  frame_style: "overlay_minimal.png",
  transition_type: "random",
  ken_burns_preset: "random",
  ken_burns_intensity: 1.0,
  speed_multiplier: 1.3,
  voice_preset_id: null,
};

export default function RenderPresetsTab() {
  const [presets, setPresets] = useState<RenderPreset[]>([]);
  const [editing, setEditing] = useState<EditingPreset | null>(null);
  const [editId, setEditId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  // Dynamic options from API
  const [bgmFiles, setBgmFiles] = useState<string[]>([]);
  const [fonts, setFonts] = useState<string[]>([]);
  const [overlays, setOverlays] = useState<{ id: string; name: string }[]>([]);
  const [voicePresets, setVoicePresets] = useState<VoicePreset[]>([]);

  const fetchPresets = useCallback(async () => {
    try {
      const res = await axios.get<RenderPreset[]>(`${API_BASE}/render-presets`);
      setPresets(res.data);
    } catch {
      console.error("Failed to fetch presets");
    }
  }, []);

  useEffect(() => {
    void fetchPresets();
    // Fetch dynamic options
    void axios.get<{ audios: { name: string }[] }>(`${API_BASE}/audio/list`).then(
      (r) => setBgmFiles(r.data.audios.map((a) => a.name)),
    ).catch(() => {});
    void axios.get<{ fonts: { name: string }[] }>(`${API_BASE}/fonts/list`).then(
      (r) => setFonts(r.data.fonts.map((f) => f.name)),
    ).catch(() => {});
    void axios.get<{ overlays: { id: string; name: string }[] }>(`${API_BASE}/overlay/list`).then(
      (r) => setOverlays(r.data.overlays),
    ).catch(() => {});
    void axios.get<VoicePreset[]>(`${API_BASE}/voice-presets`).then(
      (r) => setVoicePresets(r.data),
    ).catch(() => {});
  }, [fetchPresets]);

  const handleCreate = () => {
    setEditId(null);
    setEditing({ ...EMPTY_PRESET });
  };

  const handleEdit = (p: RenderPreset) => {
    setEditId(p.id);
    setEditing({
      name: p.name,
      description: p.description ?? "",
      bgm_file: p.bgm_file ?? "",
      bgm_volume: p.bgm_volume ?? 0.25,
      audio_ducking: p.audio_ducking ?? true,
      scene_text_font: p.scene_text_font ?? "",
      layout_style: p.layout_style ?? "post",
      frame_style: p.frame_style ?? "",
      transition_type: p.transition_type ?? "random",
      ken_burns_preset: p.ken_burns_preset ?? "random",
      ken_burns_intensity: p.ken_burns_intensity ?? 1.0,
      speed_multiplier: p.speed_multiplier ?? 1.0,
      voice_preset_id: p.voice_preset_id ?? null,
    });
  };

  const handleDelete = async (p: RenderPreset) => {
    if (!confirm(`"${p.name}" 프리셋을 삭제하시겠습니까?`)) return;
    try {
      await axios.delete(`${API_BASE}/render-presets/${p.id}`);
      await fetchPresets();
    } catch {
      alert("삭제 실패");
    }
  };

  const handleSave = async () => {
    if (!editing?.name.trim()) return;
    setSaving(true);
    try {
      if (editId) {
        await axios.put(`${API_BASE}/render-presets/${editId}`, editing);
      } else {
        await axios.post(`${API_BASE}/render-presets`, editing);
      }
      setEditing(null);
      setEditId(null);
      await fetchPresets();
    } catch {
      alert("저장 실패");
    } finally {
      setSaving(false);
    }
  };

  const set = (key: string, value: unknown) =>
    setEditing((prev) => (prev ? { ...prev, [key]: value } : prev));

  const inputCls =
    "w-full rounded border border-zinc-200 bg-white px-2.5 py-1.5 text-[11px] text-zinc-800 focus:border-zinc-400 focus:outline-none";
  const labelCls = "text-[10px] font-semibold uppercase tracking-wider text-zinc-400";

  return (
    <section className="grid gap-6 rounded-2xl border border-zinc-200/60 bg-white p-8 text-xs text-zinc-600 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
        <span className="text-[10px] font-bold tracking-[0.2em] uppercase text-zinc-400">
          Render Presets ({presets.length})
        </span>
        <button
          onClick={handleCreate}
          className="rounded-full bg-zinc-900 px-4 py-1.5 text-[10px] font-bold text-white shadow hover:bg-zinc-700 transition"
        >
          + New Preset
        </button>
      </div>

      {/* List */}
      <div className="grid gap-3">
        {presets.map((p) => (
          <div
            key={p.id}
            className="flex items-center justify-between rounded-xl border border-zinc-100 px-4 py-3 hover:bg-zinc-50/50 transition"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-zinc-800">{p.name}</span>
                {p.is_system && (
                  <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[9px] font-medium text-zinc-500">
                    System
                  </span>
                )}
              </div>
              <div className="mt-0.5 text-[10px] text-zinc-400 truncate">
                {[
                  p.layout_style,
                  p.bgm_file ? `BGM: ${p.bgm_file}` : null,
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
            <div className="flex items-center gap-2 ml-3">
              <button
                onClick={() => handleEdit(p)}
                className="rounded-full border border-zinc-200 px-3 py-1 text-[10px] font-medium text-zinc-600 hover:bg-zinc-100 transition"
              >
                Edit
              </button>
              <button
                onClick={() => handleDelete(p)}
                className="rounded-full border border-red-200 px-3 py-1 text-[10px] font-medium text-red-500 hover:bg-red-50 transition"
              >
                Del
              </button>
            </div>
          </div>
        ))}
        {presets.length === 0 && (
          <p className="py-8 text-center text-zinc-400">No presets found</p>
        )}
      </div>

      {/* Edit / Create Form */}
      {editing && (
        <div className="rounded-xl border border-zinc-200 bg-zinc-50/50 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-zinc-700">
              {editId ? "Edit Preset" : "New Preset"}
            </span>
            <button
              onClick={() => {
                setEditing(null);
                setEditId(null);
              }}
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
              <label className={labelCls}>Voice Preset</label>
              <select
                value={editing.voice_preset_id ?? ""}
                onChange={(e) => set("voice_preset_id", e.target.value ? Number(e.target.value) : null)}
                className={inputCls}
              >
                <option value="">-- None (auto) --</option>
                {voicePresets.map((vp) => (
                  <option key={vp.id} value={vp.id}>{vp.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelCls}>BGM File</label>
              <select
                value={editing.bgm_file ?? ""}
                onChange={(e) => set("bgm_file", e.target.value || null)}
                className={inputCls}
              >
                <option value="">-- None --</option>
                <option value="random">Random</option>
                {bgmFiles.map((name) => (
                  <option key={name} value={name}>{name.replace(/\.[^.]+$/, "")}</option>
                ))}
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
                  <option key={name} value={name}>{name}</option>
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
                  <option key={o.id} value={o.id}>{o.name}</option>
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
                {["fade", "dissolve", "wipeleft", "wiperight", "slideup", "slidedown", "pixelize", "radial", "none", "random"].map(
                  (v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ),
                )}
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
              className="rounded-full bg-zinc-900 px-5 py-1.5 text-[10px] font-bold text-white shadow hover:bg-zinc-700 disabled:opacity-40 transition"
            >
              {saving ? "Saving..." : editId ? "Save" : "Create"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
