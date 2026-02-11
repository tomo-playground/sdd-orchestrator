"use client";

import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import type { StoryboardListItem } from "../types";
import { API_BASE } from "../constants";

type UseStoryboardsResult = {
  storyboards: StoryboardListItem[];
  isLoading: boolean;
  reload: () => void;
  remove: (id: number) => void;
};

/**
 * Hook to load storyboard list filtered by project/group.
 * Uses local state only — does NOT modify Zustand store.
 */
export function useStoryboards(
  projectId: number | null,
  groupId: number | null
): UseStoryboardsResult {
  const [storyboards, setStoryboards] = useState<StoryboardListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const load = useCallback(async () => {
    if (projectId === null) {
      setStoryboards([]);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    try {
      const params: Record<string, unknown> = { project_id: projectId };
      if (groupId) params.group_id = groupId;
      const res = await axios.get<StoryboardListItem[]>(`${API_BASE}/storyboards`, { params });
      setStoryboards(res.data ?? []);
    } catch {
      setStoryboards([]);
    } finally {
      setIsLoading(false);
    }
  }, [projectId, groupId]);

  useEffect(() => {
    void load();
  }, [load]);

  const remove = useCallback((id: number) => {
    setStoryboards((prev) => prev.filter((s) => s.id !== id));
  }, []);

  return { storyboards, isLoading, reload: load, remove };
}
