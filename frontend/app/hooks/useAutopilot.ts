"use client";

import { useState, useRef, useMemo, useCallback } from "react";
import { AutoRunStepId } from "../types";
import { AUTO_RUN_STEPS } from "../constants";

export interface AutoRunState {
  status: "idle" | "running" | "done" | "error";
  step: AutoRunStepId | "idle";
  message: string;
  error?: string;
}

const INITIAL_STATE: AutoRunState = {
  status: "idle",
  step: "idle",
  message: "",
};

const MAX_LOG_LINES = 100;

export function useAutopilot() {
  const [autoRunState, setAutoRunState] = useState<AutoRunState>(INITIAL_STATE);
  const [autoRunLog, setAutoRunLog] = useState<string[]>([]);
  const cancelRef = useRef(false);

  const isAutoRunning = autoRunState.status === "running";

  const pushLog = useCallback((message: string) => {
    setAutoRunLog((prev) => {
      const next = [...prev, message];
      return next.length > MAX_LOG_LINES ? next.slice(-MAX_LOG_LINES) : next;
    });
  }, []);

  const setStep = useCallback((step: AutoRunStepId, message: string) => {
    setAutoRunState({ status: "running", step, message });
  }, []);

  const setError = useCallback((step: AutoRunStepId | "idle", error: string) => {
    const failedMessage = error === "Autopilot cancelled" ? "Autopilot cancelled." : "Autopilot failed.";
    setAutoRunState({
      status: "error",
      step,
      message: failedMessage,
      error,
    });
  }, []);

  const setDone = useCallback(() => {
    setAutoRunState({ status: "done", step: "render", message: "Autopilot complete." });
  }, []);

  const checkCancelled = useCallback(() => {
    if (cancelRef.current) {
      throw new Error("Autopilot cancelled");
    }
  }, []);

  const cancel = useCallback(() => {
    if (isAutoRunning) {
      cancelRef.current = true;
      pushLog("Autopilot cancel requested");
    }
  }, [isAutoRunning, pushLog]);

  const reset = useCallback(() => {
    setAutoRunState(INITIAL_STATE);
    setAutoRunLog([]);
    cancelRef.current = false;
  }, []);

  const startRun = useCallback(() => {
    cancelRef.current = false;
    setAutoRunLog([]);
  }, []);

  const autoRunProgress = useMemo(() => {
    if (autoRunState.status === "done") return 100;
    if (autoRunState.step === "idle") return 0;
    const index = AUTO_RUN_STEPS.findIndex((step) => step.id === autoRunState.step);
    return index >= 0 ? Math.round(((index + 1) / AUTO_RUN_STEPS.length) * 100) : 0;
  }, [autoRunState.status, autoRunState.step]);

  return {
    // State
    autoRunState,
    autoRunLog,
    isAutoRunning,
    autoRunProgress,
    // Actions
    pushLog,
    setStep,
    setError,
    setDone,
    checkCancelled,
    cancel,
    reset,
    startRun,
  };
}

export type UseAutopilotReturn = ReturnType<typeof useAutopilot>;
