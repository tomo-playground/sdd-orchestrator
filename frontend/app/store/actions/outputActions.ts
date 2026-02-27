import axios from "axios";
import { useRenderStore } from "../useRenderStore";
import { ADMIN_API_BASE } from "../../constants";
import { updateStoryboardMetadata } from "./storyboardActions";

/**
 * Initialize video metadata (caption + likes) in store.
 * Called after storyboard load/create so values are ready
 * before OutputTab mounts or render executes.
 */
export async function initializeVideoMetadata(topic: string): Promise<void> {
  const render = useRenderStore.getState();
  if (render.videoCaption && render.videoLikesCount) return;

  // Caption: extract hashtags from topic, fallback to topic itself
  if (!render.videoCaption && topic) {
    try {
      const res = await axios.post(`${ADMIN_API_BASE}/video/extract-hashtags`, {
        text: topic,
      });
      if (res.data.caption) {
        useRenderStore.getState().set({ videoCaption: res.data.caption });
        updateStoryboardMetadata({ caption: res.data.caption });
      }
    } catch {
      useRenderStore.getState().set({ videoCaption: topic });
    }
  }

  // Likes: random generation
  if (!useRenderStore.getState().videoLikesCount) {
    useRenderStore.getState().set({
      videoLikesCount: generateRandomLikes(),
    });
  }
}

export function generateRandomLikes(): string {
  return `${Math.floor(Math.random() * 50 + 10)}K`;
}
