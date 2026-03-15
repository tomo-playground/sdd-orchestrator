import { useContextStore } from "./useContextStore";
import { useStoryboardStore, STORYBOARD_STORE_KEY } from "./useStoryboardStore";
import { useRenderStore, RENDER_STORE_KEY } from "./useRenderStore";
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

  // Clear localStorage to prevent rehydration of old data
  if (typeof window !== "undefined") {
    localStorage.removeItem(STORYBOARD_STORE_KEY);
    localStorage.removeItem(RENDER_STORE_KEY);
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
