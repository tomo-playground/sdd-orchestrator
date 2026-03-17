import { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import { API_BASE, ADMIN_API_BASE } from "../constants";
import type { VoicePreset } from "../types";
import type { UiCallbacks } from "../types";

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

export function useVoicePresets(ui: UiCallbacks) {
  const [presets, setPresets] = useState<VoicePreset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
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
    } finally {
      setIsLoading(false);
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
        confirmLabel: "삭제",
        variant: "danger",
      });
      if (!ok) return;
      try {
        await axios.delete(`${ADMIN_API_BASE}/voice-presets/${p.id}`);
        await fetchPresets();
      } catch (error) {
        const msg = axios.isAxiosError(error)
          ? (error.response?.data?.detail ?? error.message)
          : "Unknown error";
        ui.showToast(`삭제 실패: ${msg}`, "error");
      }
    },
    [fetchPresets, ui]
  );

  const handlePreview = useCallback(async () => {
    if (!editing?.voice_design_prompt?.trim()) return;
    setPreviewing(true);
    try {
      const res = await axios.post(`${ADMIN_API_BASE}/voice-presets/preview`, {
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
      ui.showToast(`프리뷰 생성 실패: ${msg}`, "error");
    } finally {
      setPreviewing(false);
    }
  }, [editing, ui]);

  const handleSave = useCallback(async () => {
    if (!editing?.name.trim()) return;
    setSaving(true);
    try {
      if (editId) {
        const updatePayload: Record<string, unknown> = {
          name: editing.name,
          description: editing.description,
          voice_design_prompt: editing.voice_design_prompt,
          sample_text: editing.sample_text,
          language: editing.language,
        };
        if (previewSeed !== null) {
          updatePayload.voice_seed = previewSeed;
        }
        await axios.put(`${ADMIN_API_BASE}/voice-presets/${editId}`, updatePayload);
        if (previewAssetId) {
          await axios.post(`${ADMIN_API_BASE}/voice-presets/${editId}/attach-preview`, null, {
            params: { temp_asset_id: previewAssetId },
          });
        }
      } else {
        const res = await axios.post(`${ADMIN_API_BASE}/voice-presets`, {
          name: editing.name,
          description: editing.description,
          source_type: "generated",
          voice_design_prompt: editing.voice_design_prompt,
          voice_seed: previewSeed,
          language: editing.language,
          sample_text: editing.sample_text,
        });
        if (previewAssetId && res.data.id) {
          await axios.post(`${ADMIN_API_BASE}/voice-presets/${res.data.id}/attach-preview`, null, {
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
      ui.showToast(`저장 실패: ${msg}`, "error");
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
    <K extends keyof EditingPreset>(key: K, value: EditingPreset[K]) =>
      setEditing((prev) => (prev ? { ...prev, [key]: value } : prev)),
    []
  );

  return {
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
  };
}
