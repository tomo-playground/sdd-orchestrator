import axios from "axios";
import { API_BASE } from "../constants";
import type { RenderProgress } from "../types";

/**
 * Trigger async video render and stream SSE progress events.
 * Resolves with the final completed event, rejects on failure.
 */
export async function renderWithProgress(
  payload: Record<string, unknown>,
  onProgress?: (p: RenderProgress) => void
): Promise<RenderProgress> {
  const res = await axios.post(`${API_BASE}/video/create-async`, payload);
  const taskId: string = res.data.task_id;

  return new Promise((resolve, reject) => {
    const es = new EventSource(`${API_BASE}/video/progress/${taskId}`);

    es.onmessage = (event) => {
      try {
        const data: RenderProgress = JSON.parse(event.data);
        onProgress?.(data);

        if (data.stage === "completed") {
          es.close();
          resolve(data);
        }
        if (data.stage === "failed") {
          es.close();
          reject(new Error(data.error || "Render failed"));
        }
      } catch {
        // Ignore parse errors for keep-alive comments
      }
    };

    es.onerror = () => {
      es.close();
      reject(new Error("SSE connection lost"));
    };
  });
}
