import axios from "axios";
import { API_BASE, API_TIMEOUT } from "../constants";
import type { RenderProgress } from "../types";

const MAX_RETRIES = 3;
const BACKOFF_BASE_MS = 1000;
const POLL_INTERVAL_MS = 3000;

/**
 * Trigger async video render and stream SSE progress events.
 * Resolves with the final completed event, rejects on failure.
 * Automatically reconnects on SSE errors up to MAX_RETRIES times.
 */
export async function renderWithProgress(
  payload: Record<string, unknown>,
  onProgress?: (p: RenderProgress) => void,
  signal?: AbortSignal
): Promise<RenderProgress> {
  const res = await axios.post(`${API_BASE}/video/create-async`, payload, {
    timeout: API_TIMEOUT.DEFAULT,
    signal,
  });
  const taskId: string = res.data.task_id;

  return new Promise((resolve, reject) => {
    let retryCount = 0;
    let settled = false;
    let timeoutId: NodeJS.Timeout | null = null;
    let es: EventSource | null = null;

    function cleanup() {
      es?.close();
      if (timeoutId) clearTimeout(timeoutId);
    }

    // External abort support
    const onAbort = () => {
      cleanup();
      if (!settled) {
        settled = true;
        reject(new DOMException("Aborted", "AbortError"));
      }
    };
    signal?.addEventListener("abort", onAbort);

    function settle(action: () => void) {
      cleanup();
      signal?.removeEventListener("abort", onAbort);
      settled = true;
      action();
    }

    // Set overall timeout for the entire render process
    timeoutId = setTimeout(() => {
      if (!settled) {
        settle(() => reject(new Error("Render timeout after 20 minutes")));
      }
    }, API_TIMEOUT.VIDEO_RENDER);

    function connectSSE() {
      if (signal?.aborted || settled) return;
      es = new EventSource(`${API_BASE}/video/progress/${taskId}`);

      es.onmessage = (event) => {
        try {
          const data: RenderProgress = JSON.parse(event.data);
          // Reset retry count on successful message
          retryCount = 0;
          onProgress?.(data);

          if (data.stage === "completed") {
            settle(() => resolve(data));
          }
          if (data.stage === "failed") {
            settle(() => reject(new Error(data.error || "Render failed")));
          }
        } catch {
          // Ignore parse errors for keep-alive comments
        }
      };

      es.onerror = () => {
        es?.close();
        // Don't retry if already resolved/rejected (terminal event received)
        if (settled || signal?.aborted) return;
        if (retryCount < MAX_RETRIES) {
          retryCount++;
          const delay = BACKOFF_BASE_MS * Math.pow(2, retryCount - 1);
          onProgress?.({
            task_id: taskId,
            stage: "queued",
            percent: 0,
            message: `재연결 중... (${retryCount}/${MAX_RETRIES})`,
            encode_percent: 0,
            current_scene: 0,
            total_scenes: 0,
          });
          setTimeout(connectSSE, delay);
        } else {
          // SSE 재연결 실패 → polling 폴백
          console.warn("[Render] SSE failed after retries, switching to polling");
          startPolling();
        }
      };
    }

    async function startPolling() {
      while (!settled && !signal?.aborted) {
        try {
          const pollRes = await axios.get<RenderProgress>(
            `${API_BASE}/video/progress-poll/${taskId}`,
            { timeout: 10_000, signal }
          );
          const data = pollRes.data;
          onProgress?.(data);
          if (data.stage === "completed") {
            settle(() => resolve(data));
            return;
          }
          if (data.stage === "failed") {
            settle(() => reject(new Error(data.error || "Render failed")));
            return;
          }
        } catch {
          // polling 실패 시 다음 주기 재시도
        }
        await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
      }
    }

    connectSSE();
  });
}
