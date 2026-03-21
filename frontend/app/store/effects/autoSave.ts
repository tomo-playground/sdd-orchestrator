import { useContextStore } from "../useContextStore";
import { useStoryboardStore } from "../useStoryboardStore";
import { useUIStore } from "../useUIStore";
import { persistStoryboard } from "../actions/storyboardActions";

let debounceTimer: ReturnType<typeof setTimeout> | null = null;
let isSaving = false;
let initialized = false;
let cleanupFn: (() => void) | null = null;
let consecutiveFailures = 0;
const MAX_FAILURES = 3;

/** Cancel any pending debounced save. Call on context switch (group/project change). */
export function cancelPendingSave() {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
    debounceTimer = null;
  }
}

function scheduleSave(force = false) {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(async () => {
    const { storyboardId } = useContextStore.getState();
    const { isDirty, scenes, isScriptGenerating } = useStoryboardStore.getState();
    const { isAutoRunning } = useUIStore.getState();
    // Skip save if no storyboardId — new storyboard creation is user-explicit only
    if (!storyboardId) return;
    // Skip save during autoRun — it manages its own persist calls
    // Skip save during script generation — casting data not yet available (race condition)
    const hasGeneratingScene = scenes.some((s) => s.isGenerating);
    if (
      (!isDirty && !force) ||
      scenes.length === 0 ||
      isSaving ||
      isAutoRunning ||
      hasGeneratingScene ||
      isScriptGenerating
    ) {
      // Re-schedule: generation will finish → updateScene sets isDirty → retry
      if ((hasGeneratingScene || isScriptGenerating) && isDirty) scheduleSave();
      return;
    }

    isSaving = true;
    try {
      console.log("[AutoSave] persistStoryboard start");
      const ok = await persistStoryboard();
      console.log("[AutoSave] persistStoryboard done");
      if (ok) {
        consecutiveFailures = 0;
        useUIStore.getState().set({ autoSaveFailed: false });
      } else {
        consecutiveFailures++;
        if (consecutiveFailures >= MAX_FAILURES) {
          console.warn(
            `[AutoSave] ${MAX_FAILURES}회 연속 실패, 자동 저장 일시 중단 (수동 저장 필요)`
          );
          useUIStore.getState().set({ autoSaveFailed: true });
          return; // 무한 재시도 방지 — 다음 사용자 변경 시 재시작
        }
      }
    } finally {
      isSaving = false;
      if (consecutiveFailures < MAX_FAILURES) {
        const { isDirty: stillDirty } = useStoryboardStore.getState();
        if (stillDirty) scheduleSave();
      }
    }
  }, 2000);
}

export function initAutoSave(): () => void {
  if (typeof window === "undefined") return () => {};

  // HMR guard: clean up previous subscription before re-initializing
  if (initialized && cleanupFn) {
    cleanupFn();
  }
  initialized = true;

  const unsubscribeSb = useStoryboardStore.subscribe((state, prevState) => {
    if (!state.isDirty || state.isDirty === prevState.isDirty) return;
    consecutiveFailures = 0; // 새 변경 → 실패 카운터 리셋
    useUIStore.getState().set({ autoSaveFailed: false });
    scheduleSave();
  });

  // When autopilot ends (isAutoRunning true→false), flush any pending dirty state.
  // The storyboard subscribe above only fires on isDirty changes, so if isDirty
  // was already true during autopilot it would never trigger a save.
  const unsubscribeUi = useUIStore.subscribe((state, prevState) => {
    if (prevState.isAutoRunning && !state.isAutoRunning) {
      const { scenes, isDirty } = useStoryboardStore.getState();
      // Force save if scenes exist — don't mutate isDirty to avoid triggering
      // unsubscribeSb which would reset consecutiveFailures/autoSaveFailed
      if (scenes.length > 0 && (isDirty || scenes.some((s) => s.image_asset_id))) {
        scheduleSave(true);
      }
    }
  });

  cleanupFn = () => {
    unsubscribeSb();
    unsubscribeUi();
    if (debounceTimer) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
    initialized = false;
    cleanupFn = null;
  };

  return cleanupFn;
}
