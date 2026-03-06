import { useStoryboardStore } from "../useStoryboardStore";
import { useUIStore } from "../useUIStore";
import { persistStoryboard } from "../actions/storyboardActions";

let debounceTimer: ReturnType<typeof setTimeout> | null = null;
let isSaving = false;
let initialized = false;
let cleanupFn: (() => void) | null = null;

/** Cancel any pending debounced save. Call on context switch (group/project change). */
export function cancelPendingSave() {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
    debounceTimer = null;
  }
}

function scheduleSave() {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(async () => {
    const { isDirty, scenes, isScriptGenerating } = useStoryboardStore.getState();
    const { isAutoRunning } = useUIStore.getState();
    // Skip save during autoRun — it manages its own persist calls
    // Skip save during script generation — casting data not yet available (race condition)
    const hasGeneratingScene = scenes.some((s) => s.isGenerating);
    if (!isDirty || scenes.length === 0 || isSaving || isAutoRunning || hasGeneratingScene || isScriptGenerating) {
      // Re-schedule: generation will finish → updateScene sets isDirty → retry
      if ((hasGeneratingScene || isScriptGenerating) && isDirty) scheduleSave();
      return;
    }

    isSaving = true;
    try {
      await persistStoryboard();
    } finally {
      isSaving = false;
      // Re-check: if new changes arrived during save, schedule another save
      const { isDirty: stillDirty } = useStoryboardStore.getState();
      if (stillDirty) scheduleSave();
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
    scheduleSave();
  });

  // When autopilot ends (isAutoRunning true→false), flush any pending dirty state.
  // The storyboard subscribe above only fires on isDirty changes, so if isDirty
  // was already true during autopilot it would never trigger a save.
  const unsubscribeUi = useUIStore.subscribe((state, prevState) => {
    if (prevState.isAutoRunning && !state.isAutoRunning) {
      const { isDirty } = useStoryboardStore.getState();
      if (isDirty) scheduleSave();
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
