import { useState, useCallback } from "react";
import axios from "axios";
import { API_BASE } from "../../../constants";

export type CivitaiResult = {
  civitai_id: number;
  name: string;
  type: "LORA" | "Checkpoint";
  trigger_words: string[];
  base_model: string;
  preview_image: string;
  civitai_url: string;
};

import type { UiCallbacks } from "../../../types";

export function useCivitai(ui: UiCallbacks) {
  const [civitaiSearch, setCivitaiSearch] = useState("");
  const [civitaiResults, setCivitaiResults] = useState<CivitaiResult[]>([]);
  const [isSearchingCivitai, setIsSearchingCivitai] = useState(false);

  const handleCivitaiSearch = useCallback(async () => {
    if (!civitaiSearch.trim()) return;
    setIsSearchingCivitai(true);
    setCivitaiResults([]);
    try {
      const res = await axios.get<{ results: CivitaiResult[] }>(
        `${API_BASE}/loras/search-civitai`,
        { params: { query: civitaiSearch, limit: 10 } }
      );
      setCivitaiResults(res.data.results || []);
    } catch (error) {
      const msg = axios.isAxiosError(error)
        ? (error.response?.data?.detail ?? error.message)
        : "Unknown error";
      ui.showToast(`Search failed: ${msg}`, "error");
    } finally {
      setIsSearchingCivitai(false);
    }
  }, [civitaiSearch, ui]);

  const handleDownloadModel = useCallback(
    async (modelId: number, type: "LORA" | "Checkpoint") => {
      if (type !== "LORA") {
        ui.showToast("Only LoRA download is supported by backend for now.", "warning");
        return;
      }
      const ok = await ui.confirmDialog({
        title: "Download LoRA",
        message: `Download this LoRA (ID: ${modelId})? It may take a while.`,
        confirmLabel: "Download",
      });
      if (!ok) return;

      try {
        await axios.post(`${API_BASE}/loras/import-civitai/${modelId}`);
        ui.showToast("Download started. Check database later.", "success");
      } catch (error) {
        const msg = axios.isAxiosError(error)
          ? (error.response?.data?.detail ?? error.message)
          : "Unknown error";
        ui.showToast(`Download failed: ${msg}`, "error");
      }
    },
    [ui]
  );

  return {
    civitaiSearch,
    setCivitaiSearch,
    civitaiResults,
    isSearchingCivitai,
    handleCivitaiSearch,
    handleDownloadModel,
  };
}
