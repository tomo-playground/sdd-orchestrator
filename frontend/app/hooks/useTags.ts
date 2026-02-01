"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import axios from "axios";
import type { Tag } from "../types";
import { API_BASE } from "../constants";

export type TagGroup = {
  category: string;
  group_name: string;
  count: number;
};

type UseTagsResult = {
  tags: Tag[];
  tagsByGroup: Record<string, Tag[]>;
  sceneTagGroups: string[];
  isLoading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  getTagsByGroup: (groupName: string) => Tag[];
  isExclusiveGroup: (groupName: string) => boolean;
};

const SCENE_TAG_GROUPS = ["expression", "gaze", "pose", "action", "camera", "environment", "mood"];

/**
 * Hook to load and manage tags for scene context.
 */
export function useTags(category: string | null = "scene"): UseTagsResult {
  const [tags, setTags] = useState<Tag[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTags = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: any = {};
      if (category) {
        params.category = category;
      }
      const res = await axios.get(`${API_BASE}/tags`, {
        params,
      });
      setTags(res.data || []);
    } catch {
      setError("Failed to load tags");
      setTags([]);
    } finally {
      setIsLoading(false);
    }
  }, [category]);

  useEffect(() => {
    void loadTags();
  }, [loadTags]);

  const tagsByGroup = useMemo(() => {
    const grouped: Record<string, Tag[]> = {};
    for (const tag of tags) {
      const group = tag.group_name || "other";
      if (!grouped[group]) {
        grouped[group] = [];
      }
      grouped[group].push(tag);
    }
    return grouped;
  }, [tags]);

  const sceneTagGroups = useMemo(() => {
    return SCENE_TAG_GROUPS.filter((group) => tagsByGroup[group]?.length > 0);
  }, [tagsByGroup]);

  const getTagsByGroup = useCallback(
    (groupName: string): Tag[] => {
      return tagsByGroup[groupName] || [];
    },
    [tagsByGroup]
  );

  const isExclusiveGroup = useCallback(
    (groupName: string): boolean => {
      const groupTags = tagsByGroup[groupName];
      if (!groupTags || groupTags.length === 0) return false;
      return groupTags[0].exclusive;
    },
    [tagsByGroup]
  );

  return {
    tags,
    tagsByGroup,
    sceneTagGroups,
    isLoading,
    error,
    reload: loadTags,
    getTagsByGroup,
    isExclusiveGroup,
  };
}
