import axios from "axios";
import { API_BASE, API_TIMEOUT } from "../constants";
import type { ImageGenProgress } from "../types";

const MAX_RETRIES = 3;
const BACKOFF_BASE_MS = 1000;

/**
 * Trigger async image generation and stream SSE progress events.
 * Resolves with the final completed event, rejects on failure.
 * Automatically reconnects on SSE errors up to MAX_RETRIES times.
 */
export async function generateWithProgress(
  payload: Record<string, unknown>,
  onProgress?: (p: ImageGenProgress) => void,
  signal?: AbortSignal
): Promise<ImageGenProgress> {
  const res = await axios.post(`${API_BASE}/scene/generate-async`, payload, {
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
    signal?.addEventListener("abort", () => {
      cleanup();
      if (!settled) {
        settled = true;
        reject(new DOMException("Aborted", "AbortError"));
      }
    });

    timeoutId = setTimeout(() => {
      cleanup();
      if (!settled) {
        settled = true;
        reject(new Error("Image generation timeout"));
      }
    }, API_TIMEOUT.IMAGE_GENERATION);

    function connectSSE() {
      if (signal?.aborted || settled) return;
      es = new EventSource(`${API_BASE}/scene/progress/${taskId}`);

      es.onmessage = (event) => {
        try {
          const data: ImageGenProgress = JSON.parse(event.data);
          retryCount = 0;
          onProgress?.(data);

          if (data.stage === "completed") {
            cleanup();
            settled = true;
            resolve(data);
          }
          if (data.stage === "failed") {
            cleanup();
            settled = true;
            reject(new Error(data.error || "Image generation failed"));
          }
        } catch {
          // Ignore parse errors for keep-alive comments
        }
      };

      es.onerror = () => {
        es?.close();
        if (settled || signal?.aborted) return;
        if (retryCount < MAX_RETRIES) {
          retryCount++;
          const delay = BACKOFF_BASE_MS * Math.pow(2, retryCount - 1);
          onProgress?.({
            task_id: taskId,
            stage: "queued",
            percent: 0,
            message: `재연결 중... (${retryCount}/${MAX_RETRIES})`,
          });
          setTimeout(connectSSE, delay);
        } else {
          cleanup();
          settled = true;
          reject(new Error("SSE connection lost after retries"));
        }
      };
    }

    connectSSE();
  });
}
