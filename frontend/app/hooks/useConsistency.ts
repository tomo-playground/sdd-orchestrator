"use client";

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { API_BASE } from "../constants";
import type { ConsistencyResponse } from "../types";

export function useConsistency(storyboardId: number | null) {
  const [data, setData] = useState<ConsistencyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    if (!storyboardId) return;
    setLoading(true);
    setError("");
    try {
      const res = await axios.get<ConsistencyResponse>(
        `${API_BASE}/quality/consistency/${storyboardId}`
      );
      setData(res.data);
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail || err.message || "Failed to load consistency data");
      } else {
        setError("Failed to load consistency data");
      }
    } finally {
      setLoading(false);
    }
  }, [storyboardId]);

  useEffect(() => {
    if (storyboardId) {
      refresh();
    } else {
      setData(null);
      setError("");
    }
  }, [storyboardId, refresh]);

  return { data, loading, error, refresh };
}
