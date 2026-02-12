import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { API_BASE } from "../constants";
import { useStoryboardStore } from "../store/useStoryboardStore";
import { useRenderStore } from "../store/useRenderStore";

export type MaterialStatus = {
  ready: boolean;
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
};

export function useMaterialsCheck(storyboardId: number | null) {
  const [apiData, setApiData] = useState<MaterialsData | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Local store subscriptions for client-side fallback
  const scenes = useStoryboardStore((s) => s.scenes);
  const characterId = useStoryboardStore((s) => s.selectedCharacterId);
  const voicePresetId = useRenderStore((s) => s.voicePresetId);
  const bgmFile = useRenderStore((s) => s.bgmFile);
  const musicPresetId = useRenderStore((s) => s.musicPresetId);

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
  const data: MaterialsData | null = useMemo(() => {
    if (apiData) return apiData;
    return {
      storyboard_id: 0,
      script: { ready: scenes.length > 0, count: scenes.length },
      characters: { ready: characterId !== null },
      voice: { ready: voicePresetId !== null },
      music: { ready: bgmFile !== null || musicPresetId !== null },
      background: { ready: true, detail: "Optional" },
    };
  }, [apiData, scenes.length, characterId, voicePresetId, bgmFile, musicPresetId]);

  return { data, isLoading };
}
