/**
 * Migrate context fields from "shorts-producer:studio:v1"
 * to the new "shorts-producer:context:v1" store.
 *
 * Copies projectId/groupId/storyboardId/storyboardTitle.
 * Does NOT delete the source key (useStudioStore still uses it).
 * Runs once per session.
 */

const STUDIO_KEY = "shorts-producer:studio:v1";
const CONTEXT_KEY = "shorts-producer:context:v1";

let migrated = false;

export function migrateContext(): void {
  if (migrated) return;
  migrated = true;

  if (typeof window === "undefined") return;

  try {
    const existing = window.localStorage.getItem(CONTEXT_KEY);
    if (existing) return; // Already has context data

    const raw = window.localStorage.getItem(STUDIO_KEY);
    if (!raw) return;

    const parsed = JSON.parse(raw);
    const state = parsed?.state;
    if (!state || typeof state !== "object") return;

    const contextState: Record<string, unknown> = {
      state: {
        projectId: state.projectId ?? null,
        groupId: state.groupId ?? null,
        storyboardId: state.storyboardId ?? null,
        storyboardTitle: state.storyboardTitle ?? "",
      },
      version: 0,
    };

    window.localStorage.setItem(CONTEXT_KEY, JSON.stringify(contextState));
  } catch {
    // Migration failed — user starts fresh
  }
}
