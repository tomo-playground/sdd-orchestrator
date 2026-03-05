import { useCallback, useRef, useState } from "react";
import axios from "axios";
import { API_BASE } from "../constants";
import { useAudioPlayer } from "./useAudioPlayer";
import { useStoryboardStore } from "../store/useStoryboardStore";
import type {
  TTSPreviewState,
  SceneTTSPreviewResponse,
  BatchTTSPreviewResponse,
  Scene,
} from "../types";

const IDLE_STATE: TTSPreviewState = {
  status: "idle",
  audioUrl: null,
  duration: null,
  cacheKey: null,
  error: null,
  voiceDesign: null,
  voiceSeed: null,
};

export function useTTSPreview(storyboardId: number | null) {
  const [previewStates, setPreviewStates] = useState<Map<string, TTSPreviewState>>(new Map());
  const statesRef = useRef(previewStates);
  statesRef.current = previewStates;
  const [isPreviewingAll, setIsPreviewingAll] = useState(false);
  const audioPlayer = useAudioPlayer();
  const updateScene = useStoryboardStore((s) => s.updateScene);

  const updateState = useCallback((clientId: string, update: Partial<TTSPreviewState>) => {
    setPreviewStates((prev) => {
      const next = new Map(prev);
      const current = next.get(clientId) || { ...IDLE_STATE };
      next.set(clientId, { ...current, ...update } as TTSPreviewState);
      return next;
    });
  }, []);

  const previewScene = useCallback(
    async (scene: Scene) => {
      const clientId = scene.client_id;
      const state = statesRef.current.get(clientId);

      // If already has audio, toggle play
      if (state?.audioUrl) {
        audioPlayer.play(state.audioUrl);
        return;
      }

      updateState(clientId, { status: "loading", error: null });

      try {
        const res = await axios.post<SceneTTSPreviewResponse>(`${API_BASE}/preview/tts`, {
          script: scene.script,
          speaker: scene.speaker || "Narrator",
          storyboard_id: storyboardId,
          voice_design_prompt: scene.voice_design_prompt || null,
          language: "korean",
        });

        const data = res.data;
        updateState(clientId, {
          status: data.cached ? "cached" : "idle",
          audioUrl: data.audio_url,
          duration: data.duration,
          cacheKey: data.cache_key,
          voiceDesign: data.voice_design ?? null,
          voiceSeed: data.voice_seed ?? null,
        });
        updateScene(clientId, { tts_asset_id: data.temp_asset_id });

        // Auto-play after generation
        audioPlayer.play(data.audio_url);
      } catch (err) {
        const msg = axios.isAxiosError(err)
          ? (err.response?.data?.detail ?? err.message)
          : "TTS preview failed";
        updateState(clientId, { status: "error", error: msg });
      }
    },
    [storyboardId, audioPlayer, updateState, updateScene]
  );

  const previewAll = useCallback(
    async (scenes: Scene[]) => {
      setIsPreviewingAll(true);

      try {
        const res = await axios.post<BatchTTSPreviewResponse>(`${API_BASE}/preview/tts-batch`, {
          scenes: scenes.map((s) => ({
            script: s.script,
            speaker: s.speaker || "Narrator",
            storyboard_id: storyboardId,
            voice_design_prompt: s.voice_design_prompt || null,
            language: "korean",
          })),
          storyboard_id: storyboardId,
        });

        const data = res.data;
        for (const item of data.items) {
          const scene = scenes[item.scene_index];
          if (!scene) continue;
          if (item.status === "failed") {
            updateState(scene.client_id, {
              status: "error",
              error: item.error || "Failed",
            });
          } else {
            // Note: batch API doesn't return voiceDesign/voiceSeed per item
            updateState(scene.client_id, {
              status: item.status === "cached" ? "cached" : "idle",
              audioUrl: item.audio_url,
              duration: item.duration,
              cacheKey: item.cache_key,
            });
            if (item.temp_asset_id) {
              updateScene(scene.client_id, { tts_asset_id: item.temp_asset_id });
            }
          }
        }
      } catch {
        // Leave individual states as-is on batch error
      } finally {
        setIsPreviewingAll(false);
      }
    },
    [storyboardId, updateState, updateScene]
  );

  const regenerate = useCallback(
    async (scene: Scene) => {
      audioPlayer.stop();
      const clientId = scene.client_id;
      updateState(clientId, {
        status: "loading",
        error: null,
        audioUrl: null,
        duration: null,
        cacheKey: null,
      });

      try {
        const res = await axios.post<SceneTTSPreviewResponse>(`${API_BASE}/preview/tts`, {
          script: scene.script,
          speaker: scene.speaker || "Narrator",
          storyboard_id: storyboardId,
          voice_design_prompt: scene.voice_design_prompt || null,
          language: "korean",
          force_regenerate: true,
        });

        const data = res.data;
        updateState(clientId, {
          status: "idle",
          audioUrl: data.audio_url,
          duration: data.duration,
          cacheKey: data.cache_key,
          voiceDesign: data.voice_design ?? null,
          voiceSeed: data.voice_seed ?? null,
        });
        updateScene(clientId, { tts_asset_id: data.temp_asset_id });
        audioPlayer.play(data.audio_url);
      } catch (err) {
        const msg = axios.isAxiosError(err)
          ? (err.response?.data?.detail ?? err.message)
          : "TTS regenerate failed";
        updateState(clientId, { status: "error", error: msg });
      }
    },
    [storyboardId, audioPlayer, updateState, updateScene]
  );

  return {
    previewScene,
    previewAll,
    regenerate,
    previewStates,
    isPreviewingAll,
    audioPlayer,
  };
}
