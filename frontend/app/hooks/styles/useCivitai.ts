import { useState, useCallback } from "react";
import axios from "axios";
import { ADMIN_API_BASE } from "../../constants";

export type CivitaiResult = {
  civitai_id: number;
  name: string;
  type: "LORA" | "Checkpoint";
  trigger_words: string[];
  base_model: string;
  preview_image: string;
  civitai_url: string;
};

import type { UiCallbacks } from "../../types";

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
        `${ADMIN_API_BASE}/loras/search-civitai`,
        { params: { query: civitaiSearch, limit: 10 } }
      );
      setCivitaiResults(res.data.results || []);
    } catch (error) {
      const msg = axios.isAxiosError(error)
        ? (error.response?.data?.detail ?? error.message)
        : "Unknown error";
      ui.showToast(`검색 실패: ${msg}`, "error");
    } finally {
      setIsSearchingCivitai(false);
    }
  }, [civitaiSearch, ui]);

  const handleDownloadModel = useCallback(
    async (modelId: number, type: "LORA" | "Checkpoint") => {
      if (type !== "LORA") {
        ui.showToast("현재 LoRA 다운로드만 지원됩니다", "warning");
        return;
      }
      const ok = await ui.confirmDialog({
        title: "LoRA 다운로드",
        message: `이 LoRA(ID: ${modelId})를 다운로드하시겠습니까? 시간이 걸릴 수 있습니다.`,
        confirmLabel: "다운로드",
      });
      if (!ok) return;

      try {
        await axios.post(`${ADMIN_API_BASE}/loras/import-civitai/${modelId}`);
        ui.showToast("다운로드 시작됨. 나중에 데이터베이스를 확인하세요.", "success");
      } catch (error) {
        const msg = axios.isAxiosError(error)
          ? (error.response?.data?.detail ?? error.message)
          : "Unknown error";
        ui.showToast(`다운로드 실패: ${msg}`, "error");
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
