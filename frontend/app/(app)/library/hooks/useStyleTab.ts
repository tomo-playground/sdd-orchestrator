import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API_BASE } from "../../../constants";
import type { StyleProfile, StyleProfileFull, SDModelEntry, Embedding } from "../../../types";
import { useCivitai } from "./useCivitai";
import { useLoraManagement } from "./useLoraManagement";

// Re-export for consumers that import CivitaiResult from useStyleTab
export type { CivitaiResult } from "./useCivitai";

import type { UiCallbacksWithPrompt } from "../../../types";

// ── Hook ───────────────────────────────────────────────

export function useStyleTab(ui: UiCallbacksWithPrompt) {
  const [styleProfiles, setStyleProfiles] = useState<StyleProfile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<StyleProfileFull | null>(null);
  const [isStyleLoading, setIsStyleLoading] = useState(false);

  const [sdModels, setSdModels] = useState<SDModelEntry[]>([]);
  const [embeddings, setEmbeddings] = useState<Embedding[]>([]);

  const civitai = useCivitai(ui);
  const lora = useLoraManagement(ui);

  // ── Fetchers ───────────────────────────────────────

  const fetchStyles = useCallback(async () => {
    setIsStyleLoading(true);
    try {
      const res = await axios.get<StyleProfile[]>(`${API_BASE}/style-profiles/`);
      setStyleProfiles(res.data || []);
    } catch {
      console.error("Failed to fetch styles");
    } finally {
      setIsStyleLoading(false);
    }
  }, []);

  const fetchSdModels = useCallback(async () => {
    try {
      const res = await axios.get<SDModelEntry[]>(`${API_BASE}/sd-models`);
      setSdModels(res.data || []);
    } catch {
      console.error("Failed to fetch SD models");
    }
  }, []);

  const fetchEmbeddings = useCallback(async () => {
    try {
      const res = await axios.get<Embedding[]>(`${API_BASE}/embeddings`);
      setEmbeddings(res.data || []);
    } catch {
      console.error("Failed to fetch embeddings");
    }
  }, []);

  // ── Style CRUD ─────────────────────────────────────

  const handleCreateStyle = useCallback(async () => {
    const result = await ui.promptDialog({
      title: "New Style",
      message: "Enter a name for the new style profile:",
      inputField: { label: "Name", placeholder: "Enter style name..." },
    });
    if (result === false) return;
    const name = result as string;
    if (!name.trim()) return;
    try {
      await axios.post(`${API_BASE}/style-profiles/`, { name });
      await fetchStyles();
    } catch (error) {
      const msg = axios.isAxiosError(error)
        ? (error.response?.data?.detail ?? error.message)
        : "Unknown error";
      ui.showToast(`Style create failed: ${msg}`, "error");
    }
  }, [fetchStyles, ui]);

  const handleDeleteStyle = useCallback(
    async (id: number) => {
      const ok = await ui.confirmDialog({
        title: "Delete Style",
        message: "Delete this style profile?",
        confirmLabel: "Delete",
        variant: "danger",
      });
      if (!ok) return;
      try {
        await axios.delete(`${API_BASE}/style-profiles/${id}`);
        setSelectedProfile((prev) => (prev?.id === id ? null : prev));
        await fetchStyles();
      } catch (error) {
        const msg = axios.isAxiosError(error)
          ? (error.response?.data?.detail ?? error.message)
          : "Unknown error";
        ui.showToast(`Style delete failed: ${msg}`, "error");
      }
    },
    [fetchStyles, ui]
  );

  const handleUpdateStyle = useCallback(
    async (id: number, data: Partial<StyleProfile>) => {
      try {
        await axios.put(`${API_BASE}/style-profiles/${id}`, data);
        await fetchStyles();
        setSelectedProfile((prev) => {
          if (prev && prev.id === id) {
            void axios
              .get<StyleProfileFull>(`${API_BASE}/style-profiles/${id}/full`)
              .then((res) => setSelectedProfile(res.data));
          }
          return prev;
        });
      } catch (error) {
        const msg = axios.isAxiosError(error)
          ? (error.response?.data?.detail ?? error.message)
          : "Unknown error";
        ui.showToast(`Style update failed: ${msg}`, "error");
      }
    },
    [fetchStyles, ui]
  );

  const handleDuplicateStyle = useCallback(
    async (id: number) => {
      const original = styleProfiles.find((s) => s.id === id);
      if (!original) return;
      const newName = `${original.name} (Copy)`;
      const ok = await ui.confirmDialog({
        title: "Duplicate Style",
        message: `Duplicate style as "${newName}"?`,
        confirmLabel: "Duplicate",
      });
      if (!ok) return;

      try {
        const createRes = await axios.post<{ id: number; name: string }>(
          `${API_BASE}/style-profiles/`,
          { name: newName }
        );
        const newId = createRes.data.id;
        const detailRes = await axios.get<StyleProfileFull>(
          `${API_BASE}/style-profiles/${id}/full`
        );
        const fullOriginal = detailRes.data;

        await axios.put(`${API_BASE}/style-profiles/${newId}`, {
          default_positive: fullOriginal.default_positive,
          default_negative: fullOriginal.default_negative,
          sd_model_id: fullOriginal.sd_model?.id ?? null,
          loras: fullOriginal.loras?.map((l) => ({ lora_id: l.id, weight: l.weight })) ?? [],
          negative_embeddings: fullOriginal.negative_embeddings?.map((e) => e.id) ?? [],
          positive_embeddings: fullOriginal.positive_embeddings?.map((e) => e.id) ?? [],
        });
        await fetchStyles();
      } catch (error) {
        const msg = axios.isAxiosError(error)
          ? (error.response?.data?.detail ?? error.message)
          : "Unknown error";
        ui.showToast(`Style duplicate failed: ${msg}`, "error");
      }
    },
    [fetchStyles, styleProfiles, ui]
  );

  const handleLoadProfile = useCallback(
    async (id: number) => {
      try {
        const res = await axios.get<StyleProfileFull>(`${API_BASE}/style-profiles/${id}/full`);
        setSelectedProfile(res.data);
      } catch (error) {
        const msg = axios.isAxiosError(error)
          ? (error.response?.data?.detail ?? error.message)
          : "Unknown error";
        ui.showToast(`Failed to load style details: ${msg}`, "error");
      }
    },
    [ui]
  );

  // ── Profile Asset Handlers ────────────────────────

  const handleSetProfileModel = useCallback(
    async (profileId: number, modelId: number | null) => {
      await handleUpdateStyle(profileId, { sd_model_id: modelId } as Partial<StyleProfile>);
    },
    [handleUpdateStyle]
  );

  const handleToggleProfileLora = useCallback(
    async (profileId: number, loraId: number, weight?: number) => {
      if (!selectedProfile || selectedProfile.id !== profileId) return;
      const current = selectedProfile.loras ?? [];
      const exists = current.find((l) => l.id === loraId);
      let updated: { lora_id: number; weight: number }[];
      if (exists) {
        if (weight !== undefined && weight !== exists.weight) {
          updated = current.map((l) =>
            l.id === loraId
              ? { lora_id: l.id, weight: weight }
              : { lora_id: l.id, weight: l.weight }
          );
        } else {
          updated = current
            .filter((l) => l.id !== loraId)
            .map((l) => ({ lora_id: l.id, weight: l.weight }));
        }
      } else {
        const defaultWeight =
          weight ?? lora.loraEntries.find((l) => l.id === loraId)?.default_weight ?? 0.7;
        updated = [
          ...current.map((l) => ({ lora_id: l.id, weight: l.weight })),
          { lora_id: loraId, weight: defaultWeight },
        ];
      }
      await handleUpdateStyle(profileId, { loras: updated } as Partial<StyleProfile>);
    },
    [handleUpdateStyle, selectedProfile, lora.loraEntries]
  );

  const handleToggleProfileEmbedding = useCallback(
    async (profileId: number, embeddingId: number, type: "positive" | "negative") => {
      if (!selectedProfile || selectedProfile.id !== profileId) return;
      const key = type === "positive" ? "positive_embeddings" : "negative_embeddings";
      const current = selectedProfile[key] ?? [];
      const ids = current.map((e) => e.id);
      const updated = ids.includes(embeddingId)
        ? ids.filter((id) => id !== embeddingId)
        : [...ids, embeddingId];
      await handleUpdateStyle(profileId, { [key]: updated } as Partial<StyleProfile>);
    },
    [handleUpdateStyle, selectedProfile]
  );

  // ── Effects ────────────────────────────────────────

  useEffect(() => {
    void fetchStyles();
    void fetchSdModels();
    void fetchEmbeddings();
    void lora.fetchPublicLoras();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    // Styles
    styleProfiles,
    selectedProfile,
    setSelectedProfile,
    isStyleLoading,
    handleCreateStyle,
    handleDeleteStyle,
    handleUpdateStyle,
    handleDuplicateStyle,
    handleLoadProfile,
    // Models & Embeddings
    sdModels,
    embeddings,
    loraEntries: lora.loraEntries,
    // Profile asset handlers
    handleSetProfileModel,
    handleToggleProfileLora,
    handleToggleProfileEmbedding,
    // LoRA editing
    editingLora: lora.editingLora,
    setEditingLora: lora.setEditingLora,
    isUpdatingLora: lora.isUpdatingLora,
    handleUpdateLora: lora.handleUpdateLora,
    handleDeleteLora: lora.handleDeleteLora,
    // Civitai
    civitaiSearch: civitai.civitaiSearch,
    setCivitaiSearch: civitai.setCivitaiSearch,
    civitaiResults: civitai.civitaiResults,
    isSearchingCivitai: civitai.isSearchingCivitai,
    handleCivitaiSearch: civitai.handleCivitaiSearch,
    handleDownloadModel: civitai.handleDownloadModel,
  };
}
