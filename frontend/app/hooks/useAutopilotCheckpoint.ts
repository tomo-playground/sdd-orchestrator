"use client";

import { useState, useEffect } from "react";
import type { AutopilotCheckpoint } from "../types";
import type { UseAutopilotReturn } from "./useAutopilot";

/**
 * Persists autopilot progress to localStorage and restores it on remount.
 * Returns pending checkpoint (if interrupted) and a setter to clear it.
 */
export function useAutopilotCheckpoint(storyboardId: number | null, autopilot: UseAutopilotReturn) {
  const CKPT_KEY = storyboardId ? `autopilot_ckpt_${storyboardId}` : null;
  const [pendingCheckpoint, setPendingCheckpoint] = useState<AutopilotCheckpoint | null>(null);

  // Load checkpoint on storyboardId change
  useEffect(() => {
    if (!CKPT_KEY) {
      setPendingCheckpoint(null);
      return;
    }
    try {
      const raw = localStorage.getItem(CKPT_KEY);
      if (raw) {
        const ckpt: AutopilotCheckpoint = JSON.parse(raw);
        if (ckpt.interrupted) setPendingCheckpoint(ckpt);
      }
    } catch {
      // ignore parse errors
    }
  }, [CKPT_KEY]);

  // Save/clear checkpoint on autopilot state change
  useEffect(() => {
    if (!CKPT_KEY) return;
    const { status, step } = autopilot.autoRunState;
    if (status === "running" || status === "error") {
      const ckpt: AutopilotCheckpoint = {
        step: step as AutopilotCheckpoint["step"],
        timestamp: Date.now(),
        interrupted: status === "error" || status === "running",
      };
      localStorage.setItem(CKPT_KEY, JSON.stringify(ckpt));
    } else if (status === "done" || status === "idle") {
      localStorage.removeItem(CKPT_KEY);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [CKPT_KEY, autopilot.autoRunState.status, autopilot.autoRunState.step]);

  return { CKPT_KEY, pendingCheckpoint, setPendingCheckpoint };
}
