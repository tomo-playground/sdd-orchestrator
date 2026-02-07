import { useState, useCallback } from "react";
import axios from "axios";
import { API_BASE } from "../../../constants";
import type { LoRA } from "../../../types";

export function useLoraManagement() {
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
    } catch {
      alert("Failed to update LoRA");
    } finally {
      setIsUpdatingLora(false);
    }
  }, [editingLora, fetchPublicLoras]);

  const handleDeleteLora = useCallback(
    async (id: number) => {
      if (
        !confirm(
          "Delete this LoRA registration? (File/Weights might remain on disk, this removes DB entry)",
        )
      )
        return;
      try {
        await axios.delete(`${API_BASE}/loras/${id}`);
        await fetchPublicLoras();
      } catch {
        alert("Failed to delete LoRA");
      }
    },
    [fetchPublicLoras],
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
