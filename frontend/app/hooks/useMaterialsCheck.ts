import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { API_BASE } from "../constants";
import { useStoryboardStore } from "../store/useStoryboardStore";
import { useRenderStore } from "../store/useRenderStore";

export type MaterialStatus = {
  is_ready: boolean;
  count?: number;
  detail?: string;
};

export type MaterialsData = {
  storyboard_id: number;
  script: MaterialStatus;
  characters: MaterialStatus;
  voice: MaterialStatus;
  music: MaterialStatus;
  background: MaterialStatus;
  style?: MaterialStatus; // Frontend-only: derived from style profile
};

export function useMaterialsCheck(storyboardId: number | null) {
  const [apiData, setApiData] = useState<MaterialsData | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Local store subscriptions for client-side fallback
  const scenes = useStoryboardStore((s) => s.scenes);
  const characterId = useStoryboardStore((s) => s.selectedCharacterId);
  const stageStatus = useStoryboardStore((s) => s.stageStatus);
  const voicePresetId = useRenderStore((s) => s.voicePresetId);
  const bgmFile = useRenderStore((s) => s.bgmFile);
  const musicPresetId = useRenderStore((s) => s.musicPresetId);
  const currentStyleProfile = useRenderStore((s) => s.currentStyleProfile);

  useEffect(() => {
    if (!storyboardId) {
      setApiData(null);
      return;
    }
    setIsLoading(true);
    axios
      .get(`${API_BASE}/storyboards/${storyboardId}/materials`)
      .then((res) => setApiData(res.data))
      .catch((err) => {
        console.warn("[useMaterialsCheck] API fetch failed, using fallback:", err.message);
        setApiData(null);
      })
      .finally(() => setIsLoading(false));
  }, [storyboardId]);

  // Merge: API 우선, 없으면 로컬 fallback
  // style은 Frontend-only (Backend API에 없음) → 항상 클라이언트에서 파생
  const data: MaterialsData | null = useMemo(() => {
    const styleReady: MaterialStatus = { is_ready: currentStyleProfile?.id != null };
    if (apiData) return { ...apiData, style: styleReady };
    // Background ready: if Stage not started (null/pending) → optional (true),
    // if staging started → only ready when "staged"
    const bgReady = !stageStatus || stageStatus === "pending" || stageStatus === "staged";
    return {
      storyboard_id: 0,
      script: { is_ready: scenes.length > 0, count: scenes.length },
      characters: { is_ready: characterId !== null },
      voice: { is_ready: voicePresetId !== null },
      music: { is_ready: bgmFile !== null || musicPresetId !== null },
      background: { is_ready: bgReady, detail: stageStatus === "staged" ? "Staged" : "Optional" },
      style: styleReady,
    };
  }, [
    apiData,
    scenes.length,
    characterId,
    stageStatus,
    voicePresetId,
    bgmFile,
    musicPresetId,
    currentStyleProfile,
  ]);

  return { data, isLoading };
}
