"use client";

import { useCallback, useEffect, useState } from "react";
import { Image as ImageIcon, Loader2, RefreshCw } from "lucide-react";
import axios from "axios";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useUIStore } from "../../store/useUIStore";
import Button from "../ui/Button";
import EmptyState from "../ui/EmptyState";
import { API_BASE, API_TIMEOUT } from "../../constants";
import { getErrorMsg } from "../../utils/error";
import StageLocationCard from "./StageLocationCard";
import type { StageLocationStatus, StageStatusResponse, StageStatus } from "../../types";

type Props = {
  storyboardId: number;
  onStatusChange: (ready: number, total: number) => void;
};

export default function StageLocationsSection({ storyboardId, onStatusChange }: Props) {
  const showToast = useUIStore((s) => s.showToast);

  const [locations, setLocations] = useState<StageLocationStatus[]>([]);
  const [stageStatus, setStageStatus] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [ready, setReady] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [regeneratingKeys, setRegeneratingKeys] = useState<Set<string>>(new Set());

  const fetchStatus = useCallback(async () => {
    if (!storyboardId) return;
    setIsLoading(true);
    try {
      const res = await axios.get<StageStatusResponse>(
        `${API_BASE}/storyboards/${storyboardId}/stage/status`,
        { timeout: API_TIMEOUT.DEFAULT }
      );
      setLocations(res.data.locations);
      setStageStatus(res.data.stage_status);
      setTotal(res.data.total);
      setReady(res.data.ready);
      onStatusChange(res.data.ready, res.data.total);

      // Sync background_id to storyboard store scenes
      const bgMap = new Map<number, number>();
      for (const loc of res.data.locations) {
        if (loc.background_id != null) {
          for (const sid of loc.scene_ids) bgMap.set(sid, loc.background_id);
        }
      }
      if (bgMap.size > 0) {
        const store = useStoryboardStore.getState();
        let changed = false;
        const synced = store.scenes.map((s) => {
          const bgId = bgMap.get(s.id);
          if (bgId != null && s.background_id !== bgId) {
            changed = true;
            return { ...s, background_id: bgId };
          }
          return s;
        });
        if (changed) store.setScenes(synced);
      }

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
      // Force-regenerate all: run each location individually for per-card progress
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
            { timeout: API_TIMEOUT.STAGE_GENERATE }
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
      await fetchStatus();
      if (failCount > 0) {
        showToast(`${failCount}개 배경 재생성 실패`, "error");
      } else {
        showToast("전체 배경 재생성 완료", "success");
      }
      setIsGenerating(false);
    } else {
      // First-time generation (batch)
      setIsGenerating(true);
      useStoryboardStore.getState().set({ stageStatus: "staging" });
      try {
        await axios.post(`${API_BASE}/storyboards/${storyboardId}/stage/generate-backgrounds`, null, {
          timeout: API_TIMEOUT.STAGE_GENERATE,
        });
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
        { timeout: API_TIMEOUT.STAGE_GENERATE }
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

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-800">배경</h3>
        <div className="flex items-center gap-2">
          {stageStatus === "failed" && (
            <span className="text-[11px] font-medium text-red-500">생성 실패</span>
          )}
          <Button
            size="sm"
            variant="outline"
            onClick={handleGenerate}
            loading={isGenerating}
            disabled={isGenerating || isLoading}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            {locations.length > 0 ? "전체 재생성" : "생성"}
          </Button>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && locations.length === 0 && (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
        </div>
      )}

      {/* Empty state */}
      {!isLoading && locations.length === 0 && (
        <EmptyState icon={ImageIcon} title="배경 이미지를 생성하세요" variant="inline" />
      )}

      {/* Location Cards Grid */}
      {locations.length > 0 && (
        <>
          <p className="mb-2 text-[11px] text-zinc-400">
            {ready}/{total}개 배경 준비 완료
          </p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {locations.map((loc) => (
              <StageLocationCard
                key={loc.location_key}
                location={loc}
                isRegenerating={regeneratingKeys.has(loc.location_key)}
                onRegenerate={(tags) => handleRegenerate(loc.location_key, tags)}
              />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
