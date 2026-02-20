import axios from "axios";
import { API_BASE, API_TIMEOUT } from "../constants";
import type { RenderProgress } from "../types";

const MAX_RETRIES = 3;
const BACKOFF_BASE_MS = 1000;

/**
 * Trigger async video render and stream SSE progress events.
 * Resolves with the final completed event, rejects on failure.
 * Automatically reconnects on SSE errors up to MAX_RETRIES times.
 */
export async function renderWithProgress(
  payload: Record<string, unknown>,
  onProgress?: (p: RenderProgress) => void
): Promise<RenderProgress> {
  const res = await axios.post(`${API_BASE}/video/create-async`, payload, {
    timeout: API_TIMEOUT.DEFAULT,
  });
  const taskId: string = res.data.task_id;

  return new Promise((resolve, reject) => {
    let retryCount = 0;
    let settled = false;
    let timeoutId: NodeJS.Timeout | null = null;
    let es: EventSource | null = null;

    // Set overall timeout for the entire render process
    timeoutId = setTimeout(() => {
      es?.close();
      if (!settled) {
        settled = true;
        reject(new Error("Render timeout after 20 minutes"));
      }
    }, API_TIMEOUT.VIDEO_RENDER);

    function connectSSE() {
      es = new EventSource(`${API_BASE}/video/progress/${taskId}`);

      es.onmessage = (event) => {
        try {
          const data: RenderProgress = JSON.parse(event.data);
          // Reset retry count on successful message
          retryCount = 0;
          onProgress?.(data);

          if (data.stage === "completed") {
            if (timeoutId) clearTimeout(timeoutId);
            es?.close();
            settled = true;
            resolve(data);
          }
          if (data.stage === "failed") {
            if (timeoutId) clearTimeout(timeoutId);
            es?.close();
            settled = true;
            reject(new Error(data.error || "Render failed"));
          }
        } catch {
          // Ignore parse errors for keep-alive comments
        }
      };

      es.onerror = () => {
        es?.close();
        // Don't retry if already resolved/rejected (terminal event received)
        if (settled) return;
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
          if (timeoutId) clearTimeout(timeoutId);
          settled = true;
          reject(new Error("SSE connection lost after retries"));
        }
      };
    }

    connectSSE();
  });
}
