/**
 * Bridge layer: bi-directional sync between new global stores
 * (useContextStore, useUIStore, useStoryboardStore, useRenderStore)
 * and legacy useStudioStore.
 *
 * This allows 52+ existing files to keep using useStudioStore
 * unchanged, while new pages consume the smaller stores directly.
 */

import { useContextStore } from "../useContextStore";
import { useUIStore } from "../useUIStore";
import { useStudioStore } from "../useStudioStore";
import { useStoryboardStore } from "../useStoryboardStore";
import { useRenderStore } from "../useRenderStore";
import { migrateContext } from "../migrations/contextMigration";

const SYNCED_CONTEXT_KEYS = ["projectId", "groupId", "storyboardId", "storyboardTitle"] as const;

/** Storyboard store ↔ useStudioStore sync keys (identity + image plan + scenes). */
const SYNCED_STORYBOARD_KEYS = [
  "storyboardId",
  "storyboardTitle",
  // Image plan fields
  "selectedCharacterId",
  "selectedCharacterName",
  "selectedCharacterBId",
  "selectedCharacterBName",
  "characterPromptMode",
  "loraTriggerWords",
  "characterLoras",
  "characterBLoras",
  "basePromptA",
  "baseNegativePromptA",
  "basePromptB",
  "baseNegativePromptB",
  "autoComposePrompt",
  "autoRewritePrompt",
  "autoReplaceRiskyTags",
  "hiResEnabled",
  "veoEnabled",
  "useControlnet",
  "controlnetWeight",
  "useIpAdapter",
  "ipAdapterReference",
  "ipAdapterWeight",
  "ipAdapterReferenceB",
  "ipAdapterWeightB",
  // Scenes
  "scenes",
  "currentSceneIndex",
  "isGenerating",
  "multiGenEnabled",
  "referenceImages",
  "validationResults",
  "validationSummary",
  "imageValidationResults",
] as const;

/** Render store ↔ useStudioStore sync keys (output slice fields). */
const SYNCED_RENDER_KEYS = [
  "currentStyleProfile",
  "layoutStyle",
  "frameStyle",
  "kenBurnsPreset",
  "kenBurnsIntensity",
  "transitionType",
  "isRendering",
  "includeSceneText",
  "bgmFile",
  "audioDucking",
  "bgmVolume",
  "speedMultiplier",
  "sceneTextFont",
  "ttsEngine",
  "voiceDesignPrompt",
  "voicePresetId",
  "bgmMode",
  "musicPresetId",
  "videoCaption",
  "videoLikesCount",
  "overlaySettings",
  "postCardSettings",
  "videoUrl",
  "videoUrlFull",
  "videoUrlPost",
  "recentVideos",
  "renderProgress",
] as const;

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

  // --- Storyboard bridge: useStoryboardStore → useStudioStore ---
  unsubs.push(
    useStoryboardStore.subscribe((sb, prev) => {
      if (syncing) return;
      syncing = true;
      try {
        const metaPatch: Record<string, unknown> = {};
        const planPatch: Record<string, unknown> = {};
        const scenesPatch: Record<string, unknown> = {};
        let metaChanged = false;
        let planChanged = false;
        let scenesChanged = false;

        for (const key of SYNCED_STORYBOARD_KEYS) {
          if (sb[key] === prev[key]) continue;
          if (key === "storyboardId" || key === "storyboardTitle") {
            metaPatch[key] = sb[key];
            metaChanged = true;
          } else if (key === "scenes" || key === "currentSceneIndex" || key === "isGenerating" || key === "multiGenEnabled" || key === "referenceImages" || key === "validationResults" || key === "validationSummary" || key === "imageValidationResults") {
            scenesPatch[key] = sb[key];
            scenesChanged = true;
          } else {
            planPatch[key] = sb[key];
            planChanged = true;
          }
        }
        if (metaChanged) useStudioStore.getState().setMeta(metaPatch);
        if (planChanged) useStudioStore.getState().setPlan(planPatch);
        if (scenesChanged) useStudioStore.getState().setScenesState(scenesPatch);
      } finally {
        syncing = false;
      }
    }),
  );

  // --- Storyboard bridge: useStudioStore → useStoryboardStore ---
  unsubs.push(
    useStudioStore.subscribe((studio, prev) => {
      if (syncing) return;
      syncing = true;
      try {
        const s = studio as unknown as Record<string, unknown>;
        const p = prev as unknown as Record<string, unknown>;
        const patch: Record<string, unknown> = {};
        let changed = false;
        for (const key of SYNCED_STORYBOARD_KEYS) {
          if (s[key] !== p[key]) {
            patch[key] = s[key];
            changed = true;
          }
        }
        if (changed) useStoryboardStore.getState().set(patch);
      } finally {
        syncing = false;
      }
    }),
  );

  // --- Render bridge: useRenderStore → useStudioStore ---
  unsubs.push(
    useRenderStore.subscribe((render, prev) => {
      if (syncing) return;
      syncing = true;
      try {
        const patch: Record<string, unknown> = {};
        let changed = false;
        for (const key of SYNCED_RENDER_KEYS) {
          if (render[key] !== prev[key]) {
            patch[key] = render[key];
            changed = true;
          }
        }
        if (changed) useStudioStore.getState().setOutput(patch);
      } finally {
        syncing = false;
      }
    }),
  );

  // --- Render bridge: useStudioStore → useRenderStore ---
  unsubs.push(
    useStudioStore.subscribe((studio, prev) => {
      if (syncing) return;
      syncing = true;
      try {
        const s = studio as unknown as Record<string, unknown>;
        const p = prev as unknown as Record<string, unknown>;
        const patch: Record<string, unknown> = {};
        let changed = false;
        for (const key of SYNCED_RENDER_KEYS) {
          if (s[key] !== p[key]) {
            patch[key] = s[key];
            changed = true;
          }
        }
        if (changed) useRenderStore.getState().set(patch);
      } finally {
        syncing = false;
      }
    }),
  );

  // --- Initial sync: seed new stores from useStudioStore ---
  const initial = useStudioStore.getState();
  const ctxState = useContextStore.getState();

  // Context store seeding (existing)
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

  // Storyboard store seeding
  const sbState = useStoryboardStore.getState();
  if (sbState.storyboardId === null && initial.storyboardId !== null) {
    syncing = true;
    try {
      const src = initial as unknown as Record<string, unknown>;
      const seed: Record<string, unknown> = {};
      for (const key of SYNCED_STORYBOARD_KEYS) {
        seed[key] = src[key];
      }
      useStoryboardStore.getState().set(seed);
    } finally {
      syncing = false;
    }
  }

  // Render store seeding
  const renderState = useRenderStore.getState();
  if (renderState.currentStyleProfile === null && initial.currentStyleProfile !== null) {
    syncing = true;
    try {
      const src = initial as unknown as Record<string, unknown>;
      const seed: Record<string, unknown> = {};
      for (const key of SYNCED_RENDER_KEYS) {
        seed[key] = src[key];
      }
      useRenderStore.getState().set(seed);
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
