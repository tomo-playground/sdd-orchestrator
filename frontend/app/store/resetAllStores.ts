import { useContextStore } from "./useContextStore";
import { useStoryboardStore, getStoryboardPersistKey } from "./useStoryboardStore";
import { useRenderStore, getRenderPersistKey } from "./useRenderStore";
import { useUIStore } from "./useUIStore";
import { useChatStore } from "./useChatStore";

/**
 * Reset Storyboard + Render + UI stores without touching ContextStore.
 * Use when switching context (project/group change, dismiss, delete)
 * where ContextStore is managed separately by the caller.
 */
export function resetTransientStores() {
  useStoryboardStore.getState().reset();
  useRenderStore.getState().reset();
  useUIStore.getState().resetUI();
}

/**
 * Reset all stores to initial state.
 * Call when creating a new storyboard to clear previous data.
 *
 * Preserves projectId/groupId so the user stays in context.
 * Optionally reloads group defaults (bgmFile, speedMultiplier, etc.)
 */
export async function resetAllStores(options?: { reloadGroupDefaults?: boolean }) {
  const { reloadGroupDefaults = true } = options ?? {};
  const ctxState = useContextStore.getState();

  // Preserve context before reset
  const preserved = {
    projectId: ctxState.projectId,
    groupId: ctxState.groupId,
  };

  // Clear per-storyboard localStorage keys to prevent rehydration of old data
  // getStoryboardPersistKey / getRenderPersistKey use the CURRENT storyboardId before reset
  if (typeof window !== "undefined") {
    localStorage.removeItem(getStoryboardPersistKey());
    localStorage.removeItem(getRenderPersistKey());
  }

  // Reset all stores (including chat temporary key)
  ctxState.resetContext();
  useStoryboardStore.getState().reset();
  useRenderStore.getState().reset();
  const prevToken = useUIStore.getState().chatResetToken ?? 0;
  useUIStore.getState().resetUI();
  useChatStore.getState().clearMessages(null);

  // Bump reset token AFTER resetUI (which resets to initialState)
  // so hooks detect null→null storyboardId resets
  useUIStore.getState().set({ chatResetToken: prevToken + 1 });

  // Restore preserved context
  useContextStore.getState().setContext({
    projectId: preserved.projectId,
    groupId: preserved.groupId,
  });

  // Reload group defaults to restore render preset values
  if (reloadGroupDefaults && preserved.groupId !== null) {
    const { loadGroupDefaults } = await import("./actions/groupActions");
    await loadGroupDefaults(preserved.groupId);
  }
}
