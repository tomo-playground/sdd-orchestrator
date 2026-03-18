import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API_BASE, ADMIN_API_BASE } from "../constants";
import type { MusicPreset, RenderPreset, UiCallbacks } from "../types";

// ── Types ──────────────────────────────────────────────

export type EditingPreset = Partial<RenderPreset> & { name: string };

export const EMPTY_PRESET: EditingPreset = {
  name: "",
  description: "",
  bgm_file: null,
  bgm_mode: "manual",
  bgm_volume: 0.4,
  audio_ducking: true,
  scene_text_font: "",
  layout_style: "post",
  frame_style: "overlay_minimal.png",
  transition_type: "random",
  ken_burns_preset: "random",
  ken_burns_intensity: 1.0,
  speed_multiplier: 1.3,
  music_preset_id: null,
};

// ── Hook ───────────────────────────────────────────────

export function useRenderPresetsTab(ui: UiCallbacks) {
  const [presets, setPresets] = useState<RenderPreset[]>([]);
  const [editing, setEditing] = useState<EditingPreset | null>(null);
  const [editId, setEditId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  // Dynamic options from API
  const [fonts, setFonts] = useState<string[]>([]);
  const [overlays, setOverlays] = useState<{ id: string; name: string }[]>([]);
  const [musicPresets, setMusicPresets] = useState<MusicPreset[]>([]);

  const fetchPresets = useCallback(async () => {
    try {
      const res = await axios.get<RenderPreset[]>(`${API_BASE}/render-presets`);
      setPresets(res.data);
    } catch {
      console.error("Failed to fetch presets");
    }
  }, []);

  const fetchMusicPresets = useCallback(() => {
    void axios
      .get<MusicPreset[]>(`${API_BASE}/music-presets`)
      .then((r) => setMusicPresets(r.data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    void fetchPresets();
    fetchMusicPresets();
    // Fetch dynamic options
    void axios
      .get<{ fonts: { name: string }[] }>(`${API_BASE}/fonts/list`)
      .then((r) => setFonts(r.data.fonts.map((f) => f.name)))
      .catch(() => {});
    void axios
      .get<{ overlays: { id: string; name: string }[] }>(`${API_BASE}/overlay/list`)
      .then((r) => setOverlays(r.data.overlays))
      .catch(() => {});
  }, [fetchPresets, fetchMusicPresets]);

  const handleCreate = useCallback(() => {
    setEditId(null);
    setEditing({ ...EMPTY_PRESET });
  }, []);

  const handleEdit = useCallback((p: RenderPreset) => {
    setEditId(p.id);
    setEditing({
      name: p.name,
      description: p.description ?? "",
      bgm_file: p.bgm_file ?? "",
      bgm_mode: p.bgm_mode ?? "manual",
      bgm_volume: p.bgm_volume ?? 0.4,
      audio_ducking: p.audio_ducking ?? true,
      scene_text_font: p.scene_text_font ?? "",
      layout_style: p.layout_style ?? "post",
      frame_style: p.frame_style ?? "",
      transition_type: p.transition_type ?? "random",
      ken_burns_preset: p.ken_burns_preset ?? "random",
      ken_burns_intensity: p.ken_burns_intensity ?? 1.0,
      speed_multiplier: p.speed_multiplier ?? 1.0,
      music_preset_id: p.music_preset_id ?? null,
    });
  }, []);

  const handleDelete = useCallback(
    async (p: RenderPreset) => {
      const ok = await ui.confirmDialog({
        title: "Delete Preset",
        message: `"${p.name}" 프리셋을 삭제하시겠습니까?`,
        confirmLabel: "삭제",
        variant: "danger",
      });
      if (!ok) return;
      try {
        await axios.delete(`${ADMIN_API_BASE}/render-presets/${p.id}`);
        await fetchPresets();
      } catch (error) {
        const msg = axios.isAxiosError(error)
          ? (error.response?.data?.detail ?? error.message)
          : "Unknown error";
        ui.showToast(`프리셋 삭제 실패: ${msg}`, "error");
      }
    },
    [fetchPresets, ui]
  );

  const handleSave = useCallback(async () => {
    if (!editing?.name.trim()) return;
    setSaving(true);
    try {
      if (editId) {
        await axios.put(`${ADMIN_API_BASE}/render-presets/${editId}`, editing);
      } else {
        await axios.post(`${ADMIN_API_BASE}/render-presets`, editing);
      }
      setEditing(null);
      setEditId(null);
      await fetchPresets();
    } catch (error) {
      const msg = axios.isAxiosError(error)
        ? (error.response?.data?.detail ?? error.message)
        : "Unknown error";
      ui.showToast(`프리셋 저장 실패: ${msg}`, "error");
    } finally {
      setSaving(false);
    }
  }, [editing, editId, fetchPresets, ui]);

  const handleCancel = useCallback(() => {
    setEditing(null);
    setEditId(null);
  }, []);

  const set = useCallback(
    (key: keyof EditingPreset, value: unknown) =>
      setEditing((prev) => {
        if (!prev) return prev;
        const next = { ...prev, [key]: value };
        if (key === "bgm_mode" && value === "auto") {
          next.music_preset_id = null;
        }
        return next;
      }),
    []
  );

  return {
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
    musicPresets,
  };
}
