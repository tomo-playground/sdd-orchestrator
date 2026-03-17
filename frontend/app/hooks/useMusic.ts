import { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import { API_BASE, ADMIN_API_BASE } from "../constants";
import type { MusicPreset } from "../types";
import type { UiCallbacks } from "../types";

// ── Types ──────────────────────────────────────────────

export type EditingMusic = {
  name: string;
  description: string;
  prompt: string;
  duration: number;
  seed: number | null;
};

export const EMPTY_MUSIC: EditingMusic = {
  name: "",
  description: "",
  prompt: "",
  duration: 30.0,
  seed: null,
};

// ── Hook ───────────────────────────────────────────────

export function useMusic(ui: UiCallbacks) {
  const [presets, setPresets] = useState<MusicPreset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [editing, setEditing] = useState<EditingMusic | null>(null);
  const [editId, setEditId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewAssetId, setPreviewAssetId] = useState<number | null>(null);
  const [previewSeed, setPreviewSeed] = useState<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [previewingId, setPreviewingId] = useState<number | null>(null);
  const [playingId, setPlayingId] = useState<number | null>(null);

  const fetchPresets = useCallback(async () => {
    try {
      const res = await axios.get<MusicPreset[]>(`${API_BASE}/music-presets`);
      setPresets(res.data);
    } catch {
      console.error("Failed to fetch music presets");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchPresets();
  }, [fetchPresets]);

  const handleCreate = useCallback(() => {
    setEditId(null);
    setEditing({ ...EMPTY_MUSIC });
    setPreviewUrl(null);
    setPreviewAssetId(null);
    setPreviewSeed(null);
  }, []);

  const handleEdit = useCallback((p: MusicPreset) => {
    setEditId(p.id);
    setEditing({
      name: p.name,
      description: p.description ?? "",
      prompt: p.prompt ?? "",
      duration: p.duration ?? 30.0,
      seed: p.seed ?? null,
    });
    setPreviewUrl(p.audio_url);
    setPreviewAssetId(null);
  }, []);

  const handleDelete = useCallback(
    async (p: MusicPreset) => {
      const ok = await ui.confirmDialog({
        title: "BGM 프리셋 삭제",
        message: `"${p.name}"을(를) 삭제하시겠습니까?`,
        confirmLabel: "삭제",
        variant: "danger",
      });
      if (!ok) return;
      try {
        await axios.delete(`${ADMIN_API_BASE}/music-presets/${p.id}`);
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
    if (!editing?.prompt?.trim()) return;
    setPreviewing(true);
    try {
      const res = await axios.post(`${ADMIN_API_BASE}/music-presets/preview`, {
        prompt: editing.prompt,
        duration: editing.duration,
        seed: editing.seed ?? -1,
      });
      setPreviewUrl(res.data.audio_url);
      setPreviewAssetId(res.data.temp_asset_id);
      setPreviewSeed(res.data.seed ?? null);
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
        await axios.put(`${ADMIN_API_BASE}/music-presets/${editId}`, {
          name: editing.name,
          description: editing.description,
          prompt: editing.prompt,
          duration: editing.duration,
          seed: editing.seed,
        });
      } else {
        const res = await axios.post(`${ADMIN_API_BASE}/music-presets`, {
          name: editing.name,
          description: editing.description,
          prompt: editing.prompt,
          duration: editing.duration,
          seed: previewSeed,
        });
        if (previewAssetId && res.data.id) {
          await axios.post(`${ADMIN_API_BASE}/music-presets/${res.data.id}/attach-preview`, null, {
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

  const stopAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setPlayingId(null);
  }, []);

  const playAudio = useCallback(
    (url: string, presetId?: number) => {
      stopAudio();
      const audio = new Audio(url);
      audioRef.current = audio;
      if (presetId != null) setPlayingId(presetId);
      audio.onended = () => setPlayingId(null);
      audio.play().catch(() => setPlayingId(null));
    },
    [stopAudio]
  );

  const previewPreset = useCallback(
    async (p: MusicPreset) => {
      if (p.audio_url) {
        if (playingId === p.id) {
          stopAudio();
        } else {
          playAudio(p.audio_url, p.id);
        }
        return;
      }
      if (!p.prompt?.trim()) return;
      setPreviewingId(p.id);
      try {
        const res = await axios.post(`${ADMIN_API_BASE}/music-presets/preview`, {
          prompt: p.prompt,
          duration: p.duration ?? 30.0,
          seed: p.seed ?? -1,
        });
        const url = res.data.audio_url as string;
        const tempId = res.data.temp_asset_id as number;
        const seed = res.data.seed as number | undefined;
        playAudio(url, p.id);
        await axios.post(`${ADMIN_API_BASE}/music-presets/${p.id}/attach-preview`, null, {
          params: { temp_asset_id: tempId },
        });
        if (seed != null) {
          await axios.put(`${ADMIN_API_BASE}/music-presets/${p.id}`, { seed });
        }
        await fetchPresets();
      } catch (error) {
        const msg = axios.isAxiosError(error)
          ? (error.response?.data?.detail ?? error.message)
          : "Unknown error";
        ui.showToast(`프리뷰 생성 실패: ${msg}`, "error");
      } finally {
        setPreviewingId(null);
      }
    },
    [fetchPresets, playAudio, playingId, stopAudio, ui]
  );

  const set = useCallback(
    <K extends keyof EditingMusic>(key: K, value: EditingMusic[K]) =>
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
  };
}
