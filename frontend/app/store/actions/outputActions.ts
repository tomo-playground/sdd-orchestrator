import axios from "axios";
import { useStudioStore } from "../useStudioStore";
import { API_BASE } from "../../constants";
import { updateStoryboardMetadata } from "./storyboardActions";

/**
 * Initialize video metadata (caption + likes) in store.
 * Called after storyboard load/create so values are ready
 * before OutputTab mounts or render executes.
 */
export async function initializeVideoMetadata(topic: string): Promise<void> {
  const store = useStudioStore.getState();
  if (store.videoCaption && store.videoLikesCount) return;

  // Caption: extract hashtags from topic, fallback to topic itself
  if (!store.videoCaption && topic) {
    try {
      const res = await axios.post(`${API_BASE}/video/extract-hashtags`, {
        text: topic,
      });
      if (res.data.caption) {
        useStudioStore.getState().setOutput({ videoCaption: res.data.caption });
        updateStoryboardMetadata({ default_caption: res.data.caption });
      }
    } catch {
      useStudioStore.getState().setOutput({ videoCaption: topic });
    }
  }

  // Likes: random generation
  if (!useStudioStore.getState().videoLikesCount) {
    useStudioStore.getState().setOutput({
      videoLikesCount: generateRandomLikes(),
    });
  }
}

export function generateRandomLikes(): string {
  return `${Math.floor(Math.random() * 50 + 10)}K`;
}
