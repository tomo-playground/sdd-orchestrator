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

// Single-flight: groupId 단위 동시 호출 방어 (race condition 방지)
let _inflight: { groupId: number | null; promise: Promise<number | null> } | null = null;

/**
 * Ensure a draft storyboard exists before the first chat message.
 * Returns storyboard_id (existing or newly created).
 * Returns null if creation fails (missing group_id, API error).
 * Single-flight: 같은 groupId에 대해 동시에 여러 번 호출돼도 API는 1회만 실행.
 */
export async function ensureDraftStoryboard(): Promise<number | null> {
  const { storyboardId, groupId } = useContextStore.getState();

  // Already have a storyboard -- nothing to do
  if (storyboardId) return storyboardId;

  // 같은 groupId에 대해 이미 진행 중이면 같은 Promise 반환
  if (_inflight?.groupId === groupId) return _inflight.promise;

  const promise = _createDraft(groupId);
  _inflight = { groupId, promise };
  try {
    return await promise;
  } finally {
    if (_inflight?.promise === promise) _inflight = null;
  }
}

async function _createDraft(groupId: number | null): Promise<number | null> {
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

    // 커밋 전 재검증: await 중 다른 영상을 열었으면 덮어쓰기 방지
    const current = useContextStore.getState();
    if (!current.storyboardId && current.groupId === groupId) {
      commitDraftContext(newId, res.data.title);
    }

    return newId;
  } catch (error) {
    console.error("[ensureDraftStoryboard] Failed:", error);
    useUIStore.getState().showToast("초안 생성에 실패했습니다", "error");
    return null;
  }
}

/** Draft 생성 후 context/URL/chat 동기화 (deferred side effects) */
export function commitDraftContext(storyboardId: number, title?: string) {
  useContextStore.getState().setContext({
    storyboardId,
    storyboardTitle: title || "Draft",
  });

  if (typeof window !== "undefined") {
    const url = new URL(window.location.href);
    url.searchParams.delete("new");
    url.searchParams.set("id", String(storyboardId));
    window.history.replaceState({}, "", url.toString());
  }

  useChatStore.getState().migrateFromTemp(storyboardId);
}
