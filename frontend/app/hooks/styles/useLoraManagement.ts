import { useState, useCallback } from "react";
import axios from "axios";
import { API_BASE, ADMIN_API_BASE } from "../../constants";
import type { LoRA } from "../../types";
import type { UiCallbacks } from "../../types";

export function useLoraManagement(ui: UiCallbacks) {
  const [loraEntries, setLoraEntries] = useState<LoRA[]>([]);
  const [editingLora, setEditingLora] = useState<LoRA | null>(null);
  const [isUpdatingLora, setIsUpdatingLora] = useState(false);

  const fetchPublicLoras = useCallback(async () => {
    try {
      const res = await axios.get<LoRA[]>(`${API_BASE}/loras`);
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
      ui.showToast(`LoRA 업데이트 실패: ${msg}`, "error");
    } finally {
      setIsUpdatingLora(false);
    }
  }, [editingLora, fetchPublicLoras]);

  const handleDeleteLora = useCallback(
    async (id: number) => {
      const ok = await ui.confirmDialog({
        title: "LoRA 삭제",
        message: "이 LoRA 등록을 삭제하시겠습니까? (파일은 디스크에 남을 수 있으며, DB 항목만 제거됩니다)",
        confirmLabel: "삭제",
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
        ui.showToast(`LoRA 삭제 실패: ${msg}`, "error");
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
