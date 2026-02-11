/**
 * Bridge layer: bi-directional sync between new global stores
 * (useContextStore, useUIStore) and legacy useStudioStore.
 *
 * This allows 32+ existing files to keep using useStudioStore
 * unchanged, while new pages consume the smaller stores directly.
 */

import { useContextStore } from "../useContextStore";
import { useUIStore } from "../useUIStore";
import { useStudioStore } from "../useStudioStore";
import { migrateContext } from "../migrations/contextMigration";

const SYNCED_CONTEXT_KEYS = ["projectId", "groupId", "storyboardId", "storyboardTitle"] as const;

let initialized = false;
const unsubs: (() => void)[] = [];

export function initStoreBridges(): void {
  if (initialized) return;
  if (typeof window === "undefined") return; // SSR guard
  initialized = true;

  // Run context migration before subscribing
  migrateContext();

  // NOTE: syncing flag is synchronous-only. Do NOT add async calls inside subscribers.
  let syncing = false;

  // --- Context bridge: useContextStore → useStudioStore ---
  unsubs.push(
    useContextStore.subscribe((ctx, prev) => {
      if (syncing) return;
      syncing = true;
      try {
        const patch: Record<string, unknown> = {};
        let changed = false;
        for (const key of SYNCED_CONTEXT_KEYS) {
          if (ctx[key] !== prev[key]) {
            patch[key] = ctx[key];
            changed = true;
          }
        }
        if (changed) {
          useStudioStore.getState().setMeta(patch);
        }

        // projects/groups sync
        if (ctx.projects !== prev.projects) {
          useStudioStore.getState().setProjects(ctx.projects);
        }
        if (ctx.groups !== prev.groups) {
          useStudioStore.getState().setGroups(ctx.groups);
        }
      } finally {
        syncing = false;
      }
    }),
  );

  // --- Context bridge: useStudioStore → useContextStore ---
  unsubs.push(
    useStudioStore.subscribe((studio, prev) => {
      if (syncing) return;
      syncing = true;
      try {
        const patch: Record<string, unknown> = {};
        let changed = false;
        for (const key of SYNCED_CONTEXT_KEYS) {
          if (studio[key] !== prev[key]) {
            patch[key] = studio[key];
            changed = true;
          }
        }
        if (changed) {
          useContextStore.getState().setContext(patch);
        }

        // projects/groups sync
        if (studio.projects !== prev.projects) {
          useContextStore.getState().setProjects(studio.projects);
        }
        if (studio.groups !== prev.groups) {
          useContextStore.getState().setGroups(studio.groups);
        }
      } finally {
        syncing = false;
      }
    }),
  );

  // --- UI bridge: useUIStore → useStudioStore (toast) ---
  unsubs.push(
    useUIStore.subscribe((ui, prev) => {
      if (syncing) return;
      syncing = true;
      try {
        if (ui.toast !== prev.toast) {
          useStudioStore.setState({ toast: ui.toast });
        }
      } finally {
        syncing = false;
      }
    }),
  );

  // --- UI bridge: useStudioStore → useUIStore (toast) ---
  unsubs.push(
    useStudioStore.subscribe((studio, prev) => {
      if (syncing) return;
      syncing = true;
      try {
        if (studio.toast !== prev.toast) {
          useUIStore.setState({ toast: studio.toast });
        }
      } finally {
        syncing = false;
      }
    }),
  );

  // --- Initial sync: copy current useStudioStore state → new stores ---
  const initial = useStudioStore.getState();
  const ctxState = useContextStore.getState();

  // Only seed context store if it has no projectId (fresh or first migration)
  if (ctxState.projectId === null && initial.projectId !== null) {
    syncing = true;
    try {
      useContextStore.getState().setContext({
        projectId: initial.projectId,
        groupId: initial.groupId,
        storyboardId: initial.storyboardId,
        storyboardTitle: initial.storyboardTitle,
      });
    } finally {
      syncing = false;
    }
  }
}

/** Teardown all bridge subscriptions (for test cleanup). */
export function teardownStoreBridges(): void {
  unsubs.forEach((fn) => fn());
  unsubs.length = 0;
  initialized = false;
}
