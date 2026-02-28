"use client";

import { useEffect, useRef } from "react";
import { useUIStore } from "../store/useUIStore";
import { useStoryboardStore } from "../store/useStoryboardStore";
import { useRenderStore } from "../store/useRenderStore";
import { runPreflight, buildPreflightInput } from "../utils/preflight";
import { runAutoRunFromStep } from "../store/actions/autopilotActions";
import { initAutoSave } from "../store/effects/autoSave";
import type { UseAutopilotReturn } from "./useAutopilot";

/**
 * Studio 페이지의 lifecycle useEffect 로직을 캡슐화.
 * - autoSave 초기화
 * - isNewMode 시 Script 탭 활성화
 * - storyboardId 변경 시 autopilot 리셋
 * - pendingAutoRun 처리
 * - beforeunload 가드
 */
export function useStudioLifecycle(opts: {
  isNewMode: boolean;
  storyboardId: string | null;
  autopilot: UseAutopilotReturn;
}) {
  const { isNewMode, storyboardId, autopilot } = opts;
  const setActiveTab = useUIStore((s) => s.setActiveTab);
  const setUI = useUIStore((s) => s.set);
  const pendingAutoRun = useUIStore((s) => s.pendingAutoRun);
  const isDirty = useStoryboardStore((s) => s.isDirty);
  const isGenerating = useStoryboardStore((s) => Object.keys(s.imageGenProgress).length > 0);
  const isRendering = useRenderStore((s) => s.isRendering);

  // Auto-save: isDirty subscribe -> 2s debounce -> persistStoryboard
  useEffect(() => {
    const cleanup = initAutoSave();
    return cleanup;
  }, []);

  // Auto-activate Script tab for new storyboards
  useEffect(() => {
    if (isNewMode) setActiveTab("script");
  }, [isNewMode, setActiveTab]);

  // Reset autopilot when storyboard changes (only if not currently running)
  const isAutoRunningRef = useRef(false);
  isAutoRunningRef.current = autopilot.isAutoRunning;
  useEffect(() => {
    if (!isAutoRunningRef.current) {
      autopilot.reset();
    }
    // autopilot.reset is stable (useCallback), storyboardId is the trigger
  }, [storyboardId, autopilot.reset]);

  // Script -> AutoRun chain: pendingAutoRun signal
  useEffect(() => {
    if (!pendingAutoRun) return;
    useUIStore.getState().setPendingAutoRun(false);
    const preflight = runPreflight(buildPreflightInput());
    if (preflight.errors.length > 0) {
      setUI({ showPreflightModal: true });
    } else {
      const currentScenes = useStoryboardStore.getState().scenes;
      const needsStage = currentScenes.some((s) => !s.background_id);
      const startStep = needsStage ? "stage" : "images";
      runAutoRunFromStep(startStep, autopilot);
    }
  }, [pendingAutoRun, autopilot, setUI]);

  // Warn before refresh/close during render, autopilot, unsaved changes, or image generation
  useEffect(() => {
    if (!isRendering && !autopilot.isAutoRunning && !isDirty && !isGenerating) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isRendering, autopilot.isAutoRunning, isDirty, isGenerating]);
}
