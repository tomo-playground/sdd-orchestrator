import { useCallback, useState } from "react";
import axios from "axios";
import { API_BASE } from "../constants";
import { getErrorMsg } from "../utils/error";
import type { SceneFramePreviewResponse } from "../types";

export type FramePreviewState = {
  status: "idle" | "loading" | "done" | "error";
  previewUrl: string | null;
  layoutInfo: SceneFramePreviewResponse["layout_info"] | null;
  error: string | null;
};

const IDLE_STATE: FramePreviewState = {
  status: "idle",
  previewUrl: null,
  layoutInfo: null,
  error: null,
};

export function useFramePreview() {
  const [frameStates, setFrameStates] = useState<Map<string, FramePreviewState>>(new Map());

  const updateState = useCallback((clientId: string, update: Partial<FramePreviewState>) => {
    setFrameStates((prev) => {
      const next = new Map(prev);
      const current = next.get(clientId) || { ...IDLE_STATE };
      next.set(clientId, { ...current, ...update } as FramePreviewState);
      return next;
    });
  }, []);

  const previewFrame = useCallback(
    async (
      clientId: string,
      imageUrl: string,
      script: string,
      layoutStyle: "full" | "post" = "post",
      options?: {
        channelName?: string;
        caption?: string;
        sceneTextFont?: string;
      }
    ) => {
      updateState(clientId, { status: "loading", error: null });

      try {
        const res = await axios.post<SceneFramePreviewResponse>(`${API_BASE}/preview/frame`, {
          image_url: imageUrl,
          script,
          layout_style: layoutStyle,
          include_scene_text: true,
          channel_name: options?.channelName || null,
          caption: options?.caption || null,
          scene_text_font: options?.sceneTextFont || null,
        });

        updateState(clientId, {
          status: "done",
          previewUrl: res.data.preview_url,
          layoutInfo: res.data.layout_info,
        });
      } catch (err) {
        updateState(clientId, { status: "error", error: getErrorMsg(err, "Frame preview failed") });
      }
    },
    [updateState]
  );

  const clearPreview = useCallback((clientId: string) => {
    setFrameStates((prev) => {
      const next = new Map(prev);
      next.delete(clientId);
      return next;
    });
  }, []);

  return { frameStates, previewFrame, clearPreview };
}
