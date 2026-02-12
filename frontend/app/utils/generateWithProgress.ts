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
  onProgress?: (p: ImageGenProgress) => void
): Promise<ImageGenProgress> {
  const res = await axios.post(`${API_BASE}/scene/generate-async`, payload, {
    timeout: API_TIMEOUT.DEFAULT,
  });
  const taskId: string = res.data.task_id;

  return new Promise((resolve, reject) => {
    let retryCount = 0;
    let timeoutId: NodeJS.Timeout | null = null;
    let es: EventSource | null = null;

    timeoutId = setTimeout(() => {
      es?.close();
      reject(new Error("Image generation timeout"));
    }, API_TIMEOUT.IMAGE_GENERATION);

    function connectSSE() {
      es = new EventSource(`${API_BASE}/scene/progress/${taskId}`);

      es.onmessage = (event) => {
        try {
          const data: ImageGenProgress = JSON.parse(event.data);
          retryCount = 0;
          onProgress?.(data);

          if (data.stage === "completed") {
            if (timeoutId) clearTimeout(timeoutId);
            es?.close();
            resolve(data);
          }
          if (data.stage === "failed") {
            if (timeoutId) clearTimeout(timeoutId);
            es?.close();
            reject(new Error(data.error || "Image generation failed"));
          }
        } catch {
          // Ignore parse errors for keep-alive comments
        }
      };

      es.onerror = () => {
        es?.close();
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
          if (timeoutId) clearTimeout(timeoutId);
          reject(new Error("SSE connection lost after retries"));
        }
      };
    }

    connectSSE();
  });
}
