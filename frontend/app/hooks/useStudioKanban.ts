import { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { API_BASE } from "../constants";
import { useContextStore } from "../store/useContextStore";

export type StoryboardListItem = {
  id: number;
  title: string;
  description: string | null;
  scene_count: number;
  image_count: number;
  cast: Array<{
    id: number;
    name: string;
    speaker: string;
    reference_url: string | null;
  }>;
  kanban_status: "draft" | "in_prod" | "rendered" | "published";
  stage_status: "pending" | "staging" | "staged" | "failed" | null;
  created_at: string | null;
  updated_at: string | null;
};

type KanbanColumns = Record<string, StoryboardListItem[]>;

const COLUMN_ORDER = ["draft", "in_prod", "rendered", "published"] as const;

export function useStudioKanban() {
  const projectId = useContextStore((s) => s.projectId);
  const groupId = useContextStore((s) => s.groupId);
  const [items, setItems] = useState<StoryboardListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetch = useCallback(async () => {
    if (!projectId) return;
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("project_id", String(projectId));
      if (groupId && groupId > 0) params.set("group_id", String(groupId));
      const res = await axios.get<{ items: StoryboardListItem[] }>(
        `${API_BASE}/storyboards?${params}`
      );
      setItems(res.data.items ?? []);
    } catch {
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  }, [projectId, groupId]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const columns: KanbanColumns = {};
  for (const col of COLUMN_ORDER) {
    columns[col] = items.filter((i) => i.kanban_status === col);
  }

  return { columns, isLoading, refresh: fetch, total: items.length };
}
