"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import axios from "axios";
import { API_BASE } from "../constants";
import type { TimelineResponse, TTSPreviewState } from "../types";
import { formatMmSs } from "../utils/format";

type UseTimelineParams = {
  scenes: Array<{ client_id: string; script: string; duration: number }>;
  ttsStates: Map<string, TTSPreviewState>;
  speedMultiplier: number;
  transitionType: string;
};

type UseTimelineReturn = {
  timeline: TimelineResponse | null;
  isLoading: boolean;
  refresh: () => void;
  totalFormatted: string;
};

export function useTimeline({
  scenes,
  ttsStates,
  speedMultiplier,
  transitionType,
}: UseTimelineParams): UseTimelineReturn {
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const ttsStatesRef = useRef(ttsStates);
  ttsStatesRef.current = ttsStates;

  const fetchTimeline = useCallback(async () => {
    if (scenes.length === 0) {
      setTimeline(null);
      return;
    }

    const payload = {
      scenes: scenes.map((s) => ({
        script: s.script,
        duration: s.duration,
        tts_duration: ttsStatesRef.current.get(s.client_id)?.duration ?? null,
      })),
      speed_multiplier: speedMultiplier,
      transition_type: transitionType,
    };

    setIsLoading(true);
    try {
      const { data } = await axios.post<TimelineResponse>(`${API_BASE}/preview/timeline`, payload);
      setTimeline(data);
    } catch {
      // API 에러 시 null 유지 → TimelineBar는 클라이언트 폴백
    } finally {
      setIsLoading(false);
    }
  }, [scenes, speedMultiplier, transitionType]);

  // Stable trigger: only re-fetch when cached TTS count changes (not every Map ref)
  const cachedCount = [...ttsStates.values()].filter((s) => s.duration != null).length;

  // Debounce 300ms on dependency changes
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(fetchTimeline, 300);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchTimeline, cachedCount]);

  const totalFormatted = timeline ? formatMmSs(timeline.total_duration) : "0:00";

  return { timeline, isLoading, refresh: fetchTimeline, totalFormatted };
}
