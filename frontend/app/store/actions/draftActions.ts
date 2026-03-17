import axios from "axios";
import { useContextStore } from "../useContextStore";
import { useUIStore } from "../useUIStore";
import { useChatStore } from "../useChatStore";
import { API_BASE, API_TIMEOUT } from "../../constants";

interface DraftResponse {
  storyboard_id: number;
  title: string;
  created: boolean;
}

/**
 * Ensure a draft storyboard exists before the first chat message.
 * Returns storyboard_id (existing or newly created).
 * Returns null if creation fails (missing group_id, API error).
 */
export async function ensureDraftStoryboard(): Promise<number | null> {
  const { storyboardId, groupId } = useContextStore.getState();

  // Already have a storyboard -- nothing to do
  if (storyboardId) return storyboardId;

  if (!groupId) {
    useUIStore.getState().showToast("시작하려면 시리즈를 생성하세요", "error");
    return null;
  }

  try {
    const res = await axios.post<DraftResponse>(
      `${API_BASE}/storyboards/draft`,
      { title: "Draft", group_id: groupId },
      { timeout: API_TIMEOUT.DEFAULT }
    );

    const newId = res.data.storyboard_id;

    // Sync context store
    useContextStore.getState().setContext({
      storyboardId: newId,
      storyboardTitle: res.data.title,
    });

    // Sync URL
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.delete("new");
      url.searchParams.set("id", String(newId));
      window.history.replaceState({}, "", url.toString());
    }

    // Migrate temp chat to new storyboard
    useChatStore.getState().migrateFromTemp(newId);

    return newId;
  } catch (error) {
    console.error("[ensureDraftStoryboard] Failed:", error);
    useUIStore.getState().showToast("초안 생성에 실패했습니다", "error");
    return null;
  }
}
