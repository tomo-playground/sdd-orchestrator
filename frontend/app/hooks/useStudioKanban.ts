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

/**
 * 칸반 컬럼 순서 (Frontend 유지 정당성: SP-074)
 * - UI 프레젠테이션 관심사 (컬럼 표시 순서)
 * - Backend _derive_kanban_status()는 상태 계산만 담당
 * - 상태 추가 가능성 극히 낮음 (영상 라이프사이클 전체 커버)
 */
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

  if (process.env.NODE_ENV !== "production") {
    const knownStatuses = new Set(COLUMN_ORDER as readonly string[]);
    const unknown = items.filter((i) => !knownStatuses.has(i.kanban_status));
    if (unknown.length > 0) {
      console.warn("[useStudioKanban] 미지의 kanban_status 항목:", Array.from(new Set(unknown.map((i) => i.kanban_status))));
    }
  }

  return { columns, isLoading, refresh: fetch, total: items.length };
}
