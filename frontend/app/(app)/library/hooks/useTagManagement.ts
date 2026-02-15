import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API_BASE } from "../../../constants";

// ── Types ──────────────────────────────────────────────

export type PendingTag = {
  id: number;
  name: string;
  category: string;
  group_name: string | null;
  classification_source: string | null;
  classification_confidence: number | null;
};

import type { UiCallbacks } from "../../../types";

// ── Hook ───────────────────────────────────────────────

export function useTagManagement(fetchTagsData: () => Promise<void>, ui: UiCallbacks) {
  const [isTagsLoading, setIsTagsLoading] = useState(false);

  // Filters
  const [tagGroupFilter, setTagGroupFilter] = useState<string>("");
  const [tagCategoryFilter, setTagCategoryFilter] = useState<string>("");

  // Pending Classifications
  const [pendingTags, setPendingTags] = useState<PendingTag[]>([]);
  const [isPendingLoading, setIsPendingLoading] = useState(false);
  const [pendingGroupSelection, setPendingGroupSelection] = useState<Record<number, string>>({});
  const [pendingApproving, setPendingApproving] = useState<Record<number, boolean>>({});
  const [showPendingSection, setShowPendingSection] = useState(true);

  // ── Fetchers ───────────────────────────────────────

  const fetchPendingTags = useCallback(async () => {
    setIsPendingLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/tags/pending?limit=50`);
      setPendingTags(res.data.tags || []);
      const selections: Record<number, string> = {};
      (res.data.tags || []).forEach((tag: PendingTag) => {
        if (tag.group_name) {
          selections[tag.id] = tag.group_name;
        }
      });
      setPendingGroupSelection(selections);
    } catch {
      console.error("Failed to fetch pending tags");
    } finally {
      setIsPendingLoading(false);
    }
  }, []);

  const handleRefresh = useCallback(async () => {
    setIsTagsLoading(true);
    await fetchTagsData();
    await fetchPendingTags();
    setIsTagsLoading(false);
  }, [fetchTagsData, fetchPendingTags]);

  const handleApprovePendingTag = useCallback(
    async (tagId: number) => {
      const groupName = pendingGroupSelection[tagId];
      if (!groupName) {
        ui.showToast("Please select a group first", "warning");
        return;
      }
      setPendingApproving((prev) => ({ ...prev, [tagId]: true }));
      try {
        await axios.post(`${API_BASE}/tags/approve-classification`, {
          tag_id: tagId,
          group_name: groupName,
        });
        setPendingTags((prev) => prev.filter((t) => t.id !== tagId));
        setPendingGroupSelection((prev) => {
          const next = { ...prev };
          delete next[tagId];
          return next;
        });
      } catch (error) {
        const msg = axios.isAxiosError(error)
          ? (error.response?.data?.detail ?? error.message)
          : "Unknown error";
        ui.showToast(`Tag approve failed: ${msg}`, "error");
      } finally {
        setPendingApproving((prev) => ({ ...prev, [tagId]: false }));
      }
    },
    [pendingGroupSelection, ui]
  );

  // ── Effects ────────────────────────────────────────

  useEffect(() => {
    void fetchPendingTags();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    isTagsLoading,
    tagGroupFilter,
    setTagGroupFilter,
    tagCategoryFilter,
    setTagCategoryFilter,
    pendingTags,
    isPendingLoading,
    pendingGroupSelection,
    setPendingGroupSelection,
    pendingApproving,
    showPendingSection,
    setShowPendingSection,
    handleRefresh,
    fetchPendingTags,
    handleApprovePendingTag,
  };
}
