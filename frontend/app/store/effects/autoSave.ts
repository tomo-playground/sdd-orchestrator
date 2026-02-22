import { useStoryboardStore } from "../useStoryboardStore";
import { persistStoryboard } from "../actions/storyboardActions";

let debounceTimer: ReturnType<typeof setTimeout> | null = null;
let isSaving = false;
let initialized = false;

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
  if (initialized) return () => {};
  initialized = true;

  const unsubscribe = useStoryboardStore.subscribe((state, prevState) => {
    if (!state.isDirty || state.isDirty === prevState.isDirty) return;
    scheduleSave();
  });

  return () => {
    unsubscribe();
    if (debounceTimer) clearTimeout(debounceTimer);
    initialized = false;
  };
}
