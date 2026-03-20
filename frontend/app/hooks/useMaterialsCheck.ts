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
  style?: MaterialStatus; // Frontend-only: derived from style profile
};

/** Map API item { is_ready } → MaterialStatus { ready } */
function mapApiStatus(raw: unknown): MaterialStatus {
  const item = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>;
  return {
    ...item,
    ready: Boolean(item.is_ready ?? item.ready),
    ...(typeof item.count === "number" && { count: item.count }),
    ...(typeof item.detail === "string" && { detail: item.detail }),
  };
}

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
      .then((res) => {
        const d = res.data;
        setApiData({
          ...d,
          script: mapApiStatus(d.script),
          characters: mapApiStatus(d.characters),
          voice: mapApiStatus(d.voice),
          music: mapApiStatus(d.music),
          background: mapApiStatus(d.background),
        });
      })
      .catch((err) => {
        console.warn("[useMaterialsCheck] API fetch failed, using fallback:", err.message);
        setApiData(null);
      })
      .finally(() => setIsLoading(false));
  }, [storyboardId]);

  // Merge: API 우선, 없으면 로컬 fallback
  // style은 Frontend-only (Backend API에 없음) → 항상 클라이언트에서 파생
  const data: MaterialsData | null = useMemo(() => {
    const styleReady: MaterialStatus = { ready: currentStyleProfile?.id != null };
    if (apiData) return { ...apiData, style: styleReady };
    // Background ready: if Stage not started (null/pending) → optional (true),
    // if staging started → only ready when "staged"
    const bgReady = !stageStatus || stageStatus === "pending" || stageStatus === "staged";
    return {
      storyboard_id: 0,
      script: { ready: scenes.length > 0, count: scenes.length },
      characters: { ready: characterId !== null },
      voice: { ready: voicePresetId !== null },
      music: { ready: bgmFile !== null || musicPresetId !== null },
      background: { ready: bgReady, detail: stageStatus === "staged" ? "Staged" : "Optional" },
      style: styleReady,
    };
  }, [apiData, scenes.length, characterId, stageStatus, voicePresetId, bgmFile, musicPresetId, currentStyleProfile]);

  return { data, isLoading };
}
