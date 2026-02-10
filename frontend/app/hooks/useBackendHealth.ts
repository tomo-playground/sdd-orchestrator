"use client";

import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { API_BASE } from "../constants";

const POLL_INTERVAL = 10_000;
const FAILURE_THRESHOLD = 3;

export type ConnectionStatus = "connected" | "disconnected";

export function useBackendHealth(): ConnectionStatus {
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const failCount = useRef(0);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;

    const check = async () => {
      try {
        await axios.get(`${API_BASE}/health`, { timeout: 5_000 });
        failCount.current = 0;
        setStatus("connected");
      } catch {
        failCount.current += 1;
        if (failCount.current >= FAILURE_THRESHOLD) {
          setStatus("disconnected");
        }
      }
    };

    check();
    timer = setInterval(check, POLL_INTERVAL);

    return () => clearInterval(timer);
  }, []);

  return status;
}
