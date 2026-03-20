"use client";

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useUIStore } from "../../store/useUIStore";
import { useConfirm } from "../ui/ConfirmDialog";
import { API_BASE, API_TIMEOUT } from "../../constants";
import { getErrorMsg } from "../../utils/error";
import type { StageLocationStatus, StageStatusResponse, StageStatus } from "../../types";

export function useStageLocations(
  storyboardId: number,
  onStatusChange: (ready: number, total: number) => void,
) {
  const showToast = useUIStore((s) => s.showToast);
  const { confirm, dialogProps } = useConfirm();

  const [locations, setLocations] = useState<StageLocationStatus[]>([]);
  const [stageStatus, setStageStatus] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [ready, setReady] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [regeneratingKeys, setRegeneratingKeys] = useState<Set<string>>(new Set());
  const [deletingKeys, setDeletingKeys] = useState<Set<string>>(new Set());

  const fetchStatus = useCallback(async () => {
    if (!storyboardId) return;
    setIsLoading(true);
    try {
      const res = await axios.get<StageStatusResponse>(
        `${API_BASE}/storyboards/${storyboardId}/stage/status`,
        { timeout: API_TIMEOUT.DEFAULT },
      );
      setLocations(res.data.locations);
      useStoryboardStore.getState().set({ stageLocations: res.data.locations });
      setStageStatus(res.data.stage_status);
      setTotal(res.data.total);
      setReady(res.data.ready);
      onStatusChange(res.data.ready, res.data.total);

      // Sync background_id to storyboard store scenes (set + clear)
      const bgMap = new Map<number, number | null>();
      for (const loc of res.data.locations) {
        for (const sid of loc.scene_ids) {
          bgMap.set(sid, loc.background_id);
        }
      }
      const store = useStoryboardStore.getState();
      let changed = false;
      const synced = store.scenes.map((s) => {
        const bgId = bgMap.get(s.id);
        if (bgId !== undefined) {
          if (s.background_id !== bgId) {
            changed = true;
            return { ...s, background_id: bgId };
          }
          return s;
        }
        // Scene not in bgMap — clear stale background_id
        if (s.background_id != null) {
          changed = true;
          return { ...s, background_id: null };
        }
        return s;
      });
      if (changed) store.setScenes(synced);

      useStoryboardStore.getState().set({
        stageStatus: (res.data.stage_status ?? "pending") as StageStatus,
      });
    } catch {
      // Silently fail on initial load
    } finally {
      setIsLoading(false);
    }
  }, [storyboardId, onStatusChange]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleGenerate = async () => {
    if (locations.length > 0) {
      setIsGenerating(true);
      useStoryboardStore.getState().set({ stageStatus: "staging" });
      const allKeys = locations.map((l) => l.location_key);
      setRegeneratingKeys(new Set(allKeys));
      let failCount = 0;
      for (const key of allKeys) {
        try {
          await axios.post(
            `${API_BASE}/storyboards/${storyboardId}/stage/regenerate-background/${key}`,
            null,
            { timeout: API_TIMEOUT.STAGE_GENERATE },
          );
        } catch {
          failCount++;
        }
        setRegeneratingKeys((prev) => {
          const next = new Set(prev);
          next.delete(key);
          return next;
        });
      }
      try {
        await fetchStatus();
      } finally {
        setIsGenerating(false);
      }
      if (failCount > 0) {
        if (failCount === allKeys.length) {
          useStoryboardStore.getState().set({ stageStatus: "failed" });
        }
        showToast(`${failCount}개 배경 재생성 실패`, "error");
      } else {
        showToast("전체 배경 재생성 완료", "success");
      }
    } else {
      setIsGenerating(true);
      useStoryboardStore.getState().set({ stageStatus: "staging" });
      try {
        await axios.post(
          `${API_BASE}/storyboards/${storyboardId}/stage/generate-backgrounds`,
          null,
          { timeout: API_TIMEOUT.STAGE_GENERATE },
        );
        showToast("배경 생성 완료", "success");
        await fetchStatus();
      } catch (error) {
        showToast(getErrorMsg(error, "배경 생성 실패"), "error");
        useStoryboardStore.getState().set({ stageStatus: "failed" });
      } finally {
        setIsGenerating(false);
      }
    }
  };

  const handleRegenerate = async (locationKey: string, tags?: string[]) => {
    setRegeneratingKeys((prev) => new Set(prev).add(locationKey));
    try {
      const body = tags ? { tags } : null;
      const res = await axios.post(
        `${API_BASE}/storyboards/${storyboardId}/stage/regenerate-background/${locationKey}`,
        body,
        { timeout: API_TIMEOUT.STAGE_GENERATE },
      );
      if (res.data.status === "regenerated") {
        showToast("배경 재생성 완료", "success");
        await fetchStatus();
      } else {
        showToast("재생성 실패", "error");
      }
    } catch (error) {
      showToast(getErrorMsg(error, "재생성 실패"), "error");
    } finally {
      setRegeneratingKeys((prev) => {
        const next = new Set(prev);
        next.delete(locationKey);
        return next;
      });
    }
  };

  const handleDelete = async (loc: StageLocationStatus) => {
    if (!loc.background_id) return;
    const ok = await confirm({
      title: "배경 삭제",
      message: `"${loc.location_key.replace(/_/g, " ")}" 배경을 삭제하시겠습니까?`,
      confirmLabel: "삭제",
      cancelLabel: "취소",
      variant: "danger",
    });
    if (!ok) return;
    setDeletingKeys((prev) => new Set(prev).add(loc.location_key));
    try {
      await axios.delete(`${API_BASE}/backgrounds/${loc.background_id}`, {
        timeout: API_TIMEOUT.DEFAULT,
      });
      showToast("배경이 삭제되었습니다", "success");
      await fetchStatus();
    } catch (error) {
      showToast(getErrorMsg(error, "배경 삭제 실패"), "error");
    } finally {
      setDeletingKeys((prev) => {
        const next = new Set(prev);
        next.delete(loc.location_key);
        return next;
      });
    }
  };

  return {
    locations,
    stageStatus,
    total,
    ready,
    isLoading,
    isGenerating,
    regeneratingKeys,
    deletingKeys,
    dialogProps,
    handleGenerate,
    handleRegenerate,
    handleDelete,
  };
}
