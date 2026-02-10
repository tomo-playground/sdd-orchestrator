import { useState, useCallback } from "react";
import axios from "axios";
import { API_BASE } from "../../../constants";
import type { LoRA } from "../../../types";

type UiCallbacks = {
  showToast: (message: string, type: "success" | "error" | "warning") => void;
  confirmDialog: (opts: {
    title?: string;
    message?: string;
    confirmLabel?: string;
    variant?: "default" | "danger";
  }) => Promise<boolean>;
};

export function useLoraManagement(ui: UiCallbacks) {
  const [loraEntries, setLoraEntries] = useState<LoRA[]>([]);
  const [editingLora, setEditingLora] = useState<LoRA | null>(null);
  const [isUpdatingLora, setIsUpdatingLora] = useState(false);

  const fetchPublicLoras = useCallback(async () => {
    try {
      const res = await axios.get<LoRA[]>(`${API_BASE}/loras/`);
      setLoraEntries(res.data || []);
    } catch {
      console.error("Failed to fetch public LoRAs");
    }
  }, []);

  const handleUpdateLora = useCallback(async () => {
    if (!editingLora) return;
    setIsUpdatingLora(true);
    try {
      await axios.put(`${API_BASE}/loras/${editingLora.id}`, {
        name: editingLora.name,
        trigger_words: editingLora.trigger_words,
        default_weight: editingLora.default_weight,
      });
      setEditingLora(null);
      await fetchPublicLoras();
    } catch (error) {
      const msg = axios.isAxiosError(error)
        ? (error.response?.data?.detail ?? error.message)
        : "Unknown error";
      ui.showToast(`LoRA update failed: ${msg}`, "error");
    } finally {
      setIsUpdatingLora(false);
    }
  }, [editingLora, fetchPublicLoras]);

  const handleDeleteLora = useCallback(
    async (id: number) => {
      const ok = await ui.confirmDialog({
        title: "Delete LoRA",
        message: "Delete this LoRA registration? (File may remain on disk, this removes DB entry)",
        confirmLabel: "Delete",
        variant: "danger",
      });
      if (!ok) return;
      try {
        await axios.delete(`${API_BASE}/loras/${id}`);
        await fetchPublicLoras();
      } catch (error) {
        const msg = axios.isAxiosError(error)
          ? (error.response?.data?.detail ?? error.message)
          : "Unknown error";
        ui.showToast(`LoRA delete failed: ${msg}`, "error");
      }
    },
    [fetchPublicLoras, ui]
  );

  return {
    loraEntries,
    editingLora,
    setEditingLora,
    isUpdatingLora,
    fetchPublicLoras,
    handleUpdateLora,
    handleDeleteLora,
  };
}
