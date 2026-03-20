"use client";

import { useSyncExternalStore } from "react";
import axios from "axios";
import { API_ROOT } from "../constants";

const POLL_INTERVAL = 10_000;
const FAILURE_THRESHOLD = 3;

export type ConnectionStatus = "connected" | "disconnected";

// ── Module-level singleton ───────────────────────────────
// Survives component remounts — no more "disconnected" flash on page navigation.

let currentStatus: ConnectionStatus = "connected";
let failCount = 0;
let timer: ReturnType<typeof setInterval> | null = null;
let pollingSession = 0;
const listeners = new Set<() => void>();

function notify() {
  for (const l of listeners) l();
}

function setStatus(next: ConnectionStatus) {
  if (currentStatus !== next) {
    currentStatus = next;
    notify();
  }
}

async function check(session: number) {
  try {
    await axios.get(`${API_ROOT}/health`, { timeout: 5_000 });
    if (session !== pollingSession) return;
    failCount = 0;
    setStatus("connected");
  } catch {
    if (session !== pollingSession) return;
    failCount += 1;
    if (failCount >= FAILURE_THRESHOLD) {
      setStatus("disconnected");
    }
  }
}

function startPolling() {
  if (timer !== null) return;
  pollingSession += 1;
  const session = pollingSession;
  check(session);
  timer = setInterval(() => check(session), POLL_INTERVAL);
}

function stopPolling() {
  pollingSession += 1;
  failCount = 0;
  if (timer !== null) {
    clearInterval(timer);
    timer = null;
  }
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  if (listeners.size === 1) {
    startPolling();
  }
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) {
      stopPolling();
    }
  };
}

function getSnapshot(): ConnectionStatus {
  return currentStatus;
}

function getServerSnapshot(): ConnectionStatus {
  return "connected";
}

export function useBackendHealth(): ConnectionStatus {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
