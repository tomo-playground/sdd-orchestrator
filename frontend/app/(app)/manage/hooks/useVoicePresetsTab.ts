import { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import { API_BASE } from "../../../constants";
import type { VoicePreset } from "../../../types";

import type { UiCallbacks } from "./types";

// ── Types ──────────────────────────────────────────────

export type EditingPreset = {
  name: string;
  description: string;
  voice_design_prompt: string;
  sample_text: string;
  language: string;
  voice_seed: number | null;
};

export const EMPTY_PRESET: EditingPreset = {
  name: "",
  description: "",
  voice_design_prompt: "",
  sample_text: "Hello, this is a test voice.",
  language: "korean",
  voice_seed: null,
};

// ── Hook ───────────────────────────────────────────────

export function useVoicePresetsTab(ui: UiCallbacks) {
  const [presets, setPresets] = useState<VoicePreset[]>([]);
  const [editing, setEditing] = useState<EditingPreset | null>(null);
  const [editId, setEditId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewAssetId, setPreviewAssetId] = useState<number | null>(null);
  const [previewSeed, setPreviewSeed] = useState<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const fetchPresets = useCallback(async () => {
    try {
      const res = await axios.get<VoicePreset[]>(`${API_BASE}/voice-presets`);
      setPresets(res.data);
    } catch {
      console.error("Failed to fetch voice presets");
    }
  }, []);

  useEffect(() => {
    void fetchPresets();
  }, [fetchPresets]);

  const handleCreate = useCallback(() => {
    setEditId(null);
    setEditing({ ...EMPTY_PRESET });
    setPreviewUrl(null);
    setPreviewAssetId(null);
    setPreviewSeed(null);
  }, []);

  const handleEdit = useCallback((p: VoicePreset) => {
    setEditId(p.id);
    setEditing({
      name: p.name,
      description: p.description ?? "",
      voice_design_prompt: p.voice_design_prompt ?? "",
      sample_text: p.sample_text ?? "",
      language: p.language,
      voice_seed: p.voice_seed ?? null,
    });
    setPreviewUrl(p.audio_url);
    setPreviewAssetId(null);
  }, []);

  const handleDelete = useCallback(
    async (p: VoicePreset) => {
      const ok = await ui.confirmDialog({
        title: "Delete Voice Preset",
        message: `Delete "${p.name}"?`,
        confirmLabel: "Delete",
        variant: "danger",
      });
      if (!ok) return;
      try {
        await axios.delete(`${API_BASE}/voice-presets/${p.id}`);
        await fetchPresets();
      } catch (error) {
        const msg = axios.isAxiosError(error)
          ? (error.response?.data?.detail ?? error.message)
          : "Unknown error";
        ui.showToast(`Delete failed: ${msg}`, "error");
      }
    },
    [fetchPresets, ui]
  );

  const handlePreview = useCallback(async () => {
    if (!editing?.voice_design_prompt?.trim()) return;
    setPreviewing(true);
    try {
      const res = await axios.post(`${API_BASE}/voice-presets/preview`, {
        voice_design_prompt: editing.voice_design_prompt,
        sample_text: editing.sample_text || "Hello, this is a test.",
        language: editing.language,
      });
      setPreviewUrl(res.data.audio_url);
      setPreviewAssetId(res.data.temp_asset_id);
      setPreviewSeed(res.data.voice_seed ?? null);
    } catch (error) {
      const msg = axios.isAxiosError(error)
        ? (error.response?.data?.detail ?? error.message)
        : "Unknown error";
      ui.showToast(`Preview generation failed: ${msg}`, "error");
    } finally {
      setPreviewing(false);
    }
  }, [editing, ui]);

  const handleSave = useCallback(async () => {
    if (!editing?.name.trim()) return;
    setSaving(true);
    try {
      if (editId) {
        await axios.put(`${API_BASE}/voice-presets/${editId}`, {
          name: editing.name,
          description: editing.description,
        });
      } else {
        const res = await axios.post(`${API_BASE}/voice-presets`, {
          name: editing.name,
          description: editing.description,
          source_type: "generated",
          voice_design_prompt: editing.voice_design_prompt,
          voice_seed: previewSeed,
          language: editing.language,
          sample_text: editing.sample_text,
        });
        // Attach preview audio if available
        if (previewAssetId && res.data.id) {
          await axios.post(`${API_BASE}/voice-presets/${res.data.id}/attach-preview`, null, {
            params: { temp_asset_id: previewAssetId },
          });
        }
      }
      setEditing(null);
      setEditId(null);
      setPreviewUrl(null);
      setPreviewAssetId(null);
      setPreviewSeed(null);
      await fetchPresets();
    } catch (error) {
      const msg = axios.isAxiosError(error)
        ? (error.response?.data?.detail ?? error.message)
        : "Unknown error";
      ui.showToast(`Save failed: ${msg}`, "error");
    } finally {
      setSaving(false);
    }
  }, [editing, editId, previewSeed, previewAssetId, fetchPresets, ui]);

  const handleCancel = useCallback(() => {
    setEditing(null);
    setEditId(null);
    setPreviewUrl(null);
    setPreviewAssetId(null);
    setPreviewSeed(null);
  }, []);

  const playAudio = useCallback((url: string) => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    const audio = new Audio(url);
    audioRef.current = audio;
    audio.play().catch(() => {});
  }, []);

  const set = useCallback(
    (key: keyof EditingPreset, value: unknown) =>
      setEditing((prev) => (prev ? { ...prev, [key]: value } : prev)),
    []
  );

  return {
    presets,
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
  };
}
