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

export function useCivitai() {
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
        { params: { query: civitaiSearch, limit: 10 } },
      );
      setCivitaiResults(res.data.results || []);
    } catch {
      alert("Search failed or no results");
    } finally {
      setIsSearchingCivitai(false);
    }
  }, [civitaiSearch]);

  const handleDownloadModel = useCallback(async (modelId: number, type: "LORA" | "Checkpoint") => {
    if (type !== "LORA") {
      alert("Only LoRA download is supported by backend for now.");
      return;
    }
    const userConfirm = confirm(`Download this LoRA (ID: ${modelId})? It may take a while.`);
    if (!userConfirm) return;

    try {
      await axios.post(`${API_BASE}/loras/import-civitai/${modelId}`);
      alert("Download started. Check database later.");
    } catch {
      alert("Download request failed");
    }
  }, []);

  return {
    civitaiSearch,
    setCivitaiSearch,
    civitaiResults,
    isSearchingCivitai,
    handleCivitaiSearch,
    handleDownloadModel,
  };
}
