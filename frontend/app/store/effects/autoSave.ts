import { useStoryboardStore } from "../useStoryboardStore";
import { persistStoryboard } from "../actions/storyboardActions";

let debounceTimer: ReturnType<typeof setTimeout> | null = null;
let isSaving = false;
let initialized = false;
let cleanupFn: (() => void) | null = null;

function scheduleSave() {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(async () => {
    const { isDirty, scenes } = useStoryboardStore.getState();
    if (!isDirty || scenes.length === 0 || isSaving) return;

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

  const unsubscribe = useStoryboardStore.subscribe((state, prevState) => {
    if (!state.isDirty || state.isDirty === prevState.isDirty) return;
    scheduleSave();
  });

  cleanupFn = () => {
    unsubscribe();
    if (debounceTimer) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
    initialized = false;
    cleanupFn = null;
  };

  return cleanupFn;
}
