import { useState, useCallback } from "react";
import axios from "axios";
import { ADMIN_API_BASE } from "../../../constants";
import type { LoRA } from "../../../types";
import type { UiCallbacks } from "../../../types";

export function useLoraManagement(ui: UiCallbacks) {
  const [loraEntries, setLoraEntries] = useState<LoRA[]>([]);
  const [editingLora, setEditingLora] = useState<LoRA | null>(null);
  const [isUpdatingLora, setIsUpdatingLora] = useState(false);

  const fetchPublicLoras = useCallback(async () => {
    try {
      const res = await axios.get<LoRA[]>(`${ADMIN_API_BASE}/loras/`);
      setLoraEntries(res.data || []);
    } catch {
      console.error("Failed to fetch public LoRAs");
    }
  }, []);

  const handleUpdateLora = useCallback(async () => {
    if (!editingLora) return;
    setIsUpdatingLora(true);
    try {
      const { id, preview_image_url, civitai_id, civitai_url, ...payload } = editingLora;
      await axios.put(`${ADMIN_API_BASE}/loras/${id}`, payload);
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
        await axios.delete(`${ADMIN_API_BASE}/loras/${id}`);
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
