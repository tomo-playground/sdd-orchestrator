"use client";

import { useCallback, useEffect, useState } from "react";
import type { Tag } from "../types";

const TAG_BROWSER_GROUPS = [
  "expression",
  "pose",
  "camera",
  "clothing_top",
  "clothing_outfit",
  "hair_color",
  "hair_style",
] as const;

type TagBrowserGroup = (typeof TAG_BROWSER_GROUPS)[number];

export function useTagBrowser() {
  const [activeGroup, setActiveGroup] = useState<TagBrowserGroup>("expression");
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");

  const fetchTags = useCallback(async (group: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/tags?group_name=${group}`);
      if (res.ok) {
        const data = await res.json();
        setTags(data.tags ?? data);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTags(activeGroup);
  }, [activeGroup, fetchTags]);

  const filteredTags = search
    ? tags.filter((t) => t.name.includes(search.toLowerCase()))
    : tags;

  return {
    groups: TAG_BROWSER_GROUPS,
    activeGroup,
    setActiveGroup,
    tags: filteredTags,
    loading,
    search,
    setSearch,
  };
}
