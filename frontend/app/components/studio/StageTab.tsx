"use client";

import { useCallback, useEffect, useState } from "react";
import { Image, Loader2, RefreshCw, CheckCircle2, AlertCircle, ArrowRight } from "lucide-react";
import axios from "axios";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useUIStore } from "../../store/useUIStore";
import { useContextStore } from "../../store/useContextStore";
import Button from "../ui/Button";
import EmptyState from "../ui/EmptyState";
import { API_BASE, API_TIMEOUT } from "../../constants";
import { getErrorMsg } from "../../utils/error";
import StageLocationCard from "./StageLocationCard";
import type { StageLocationStatus, StageStatusResponse, StageStatus } from "../../types";

export default function StageTab() {
  const storyboardId = useContextStore((s) => s.storyboardId);
  const scenes = useStoryboardStore((s) => s.scenes);
  const showToast = useUIStore((s) => s.showToast);
  const setActiveTab = useUIStore((s) => s.setActiveTab);

  const [locations, setLocations] = useState<StageLocationStatus[]>([]);
  const [stageStatus, setStageStatus] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [ready, setReady] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isAssigning, setIsAssigning] = useState(false);
  const [regeneratingKey, setRegeneratingKey] = useState<string | null>(null);

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
      useStoryboardStore.getState().set({
        stageStatus: (res.data.stage_status ?? "pending") as StageStatus,
      });
    } catch {
      // Silently fail on initial load
    } finally {
      setIsLoading(false);
    }
  }, [storyboardId]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleGenerate = async () => {
    if (!storyboardId) return;
    setIsGenerating(true);
    useStoryboardStore.getState().set({ stageStatus: "staging" });
    try {
      await axios.post(`${API_BASE}/storyboards/${storyboardId}/stage/generate-backgrounds`, null, {
        timeout: API_TIMEOUT.STAGE_GENERATE,
      });
      showToast("Background generation complete", "success");
      await fetchStatus();
    } catch (error) {
      showToast(getErrorMsg(error, "Background generation failed"), "error");
      useStoryboardStore.getState().set({ stageStatus: "failed" });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRegenerate = async (locationKey: string, tags?: string[]) => {
    if (!storyboardId) return;
    setRegeneratingKey(locationKey);
    try {
      const body = tags ? { tags } : null;
      const res = await axios.post(
        `${API_BASE}/storyboards/${storyboardId}/stage/regenerate-background/${locationKey}`,
        body,
        { timeout: API_TIMEOUT.STAGE_GENERATE }
      );
      if (res.data.status === "regenerated") {
        showToast("Background regenerated", "success");
        await fetchStatus();
      } else {
        showToast("Regeneration failed", "error");
      }
    } catch (error) {
      showToast(getErrorMsg(error, "Regeneration failed"), "error");
    } finally {
      setRegeneratingKey(null);
    }
  };

  /** Assign backgrounds to scenes. If navigateToDirect, proceed to Direct tab after. */
  const doAssign = async (opts?: { navigateToDirect?: boolean }) => {
    if (!storyboardId) return;
    setIsAssigning(true);
    try {
      const res = await axios.post(
        `${API_BASE}/storyboards/${storyboardId}/stage/assign-backgrounds`,
        null,
        { timeout: API_TIMEOUT.DEFAULT }
      );
      const assignments = res.data.assignments ?? [];
      if (assignments.length > 0) {
        // Sync scene store: set background_id + clear old scene-to-scene pin
        const { scenes, setScenes } = useStoryboardStore.getState();
        const assignMap = new Map<number, number>(
          assignments.map((a: { scene_id: number; background_id: number }) => [
            a.scene_id,
            a.background_id,
          ] as [number, number])
        );
        const updated = scenes.map((s) => {
          const bgId = assignMap.get(s.id);
          if (bgId != null) {
            return { ...s, background_id: bgId, environment_reference_id: null };
          }
          return s;
        });
        setScenes(updated);
        showToast(`${assignments.length} scenes assigned to backgrounds`, "success");
      }
      await fetchStatus();
      if (opts?.navigateToDirect) {
        setActiveTab("direct");
      }
    } catch (error) {
      const suffix = opts?.navigateToDirect ? " — please retry" : "";
      showToast(getErrorMsg(error, `Assignment failed${suffix}`), "error");
    } finally {
      setIsAssigning(false);
    }
  };

  if (!storyboardId || scenes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-8 py-8">
        <EmptyState
          icon={Image}
          title="No Scenes Yet"
          description="Generate a script first to set up stage backgrounds."
        />
      </div>
    );
  }

  const allReady = total > 0 && ready === total;

  return (
    <div className="flex h-full flex-col overflow-y-auto px-8 py-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-zinc-900">Stage — Backgrounds</h2>
          <p className="mt-0.5 text-xs text-zinc-500">
            Generate no-humans background images for each location, then assign to scenes.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleGenerate}
            loading={isGenerating}
            disabled={isGenerating || isLoading}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            {locations.length > 0 ? "Regenerate All" : "Generate Backgrounds"}
          </Button>
          {locations.some((l) => l.has_image) && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => doAssign()}
              loading={isAssigning}
              disabled={isAssigning}
            >
              Assign to Scenes
            </Button>
          )}
        </div>
      </div>

      {/* Readiness Bar */}
      {total > 0 && (
        <div className="mb-6 rounded-xl border border-zinc-200 bg-zinc-50 p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-medium text-zinc-600">
              Readiness: {ready}/{total} locations
            </span>
            {allReady && (
              <span className="flex items-center gap-1 text-xs font-medium text-emerald-600">
                <CheckCircle2 className="h-3.5 w-3.5" />
                All Ready
              </span>
            )}
            {stageStatus === "failed" && (
              <span className="flex items-center gap-1 text-xs font-medium text-red-500">
                <AlertCircle className="h-3.5 w-3.5" />
                Generation Failed
              </span>
            )}
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-zinc-200">
            <div
              className={`h-full rounded-full transition-all ${allReady ? "bg-emerald-500" : "bg-blue-500"}`}
              style={{ width: total > 0 ? `${(ready / total) * 100}%` : "0%" }}
            />
          </div>
          {allReady && (
            <div className="mt-3 flex justify-end">
              <Button
                size="sm"
                onClick={() => doAssign({ navigateToDirect: true })}
                loading={isAssigning}
                disabled={isAssigning}
              >
                Continue to Direct
                <ArrowRight className="ml-1 h-3.5 w-3.5" />
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Loading state */}
      {isLoading && locations.length === 0 && (
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
        </div>
      )}

      {/* Empty state — no locations derived */}
      {!isLoading && locations.length === 0 && (
        <div className="flex flex-1 items-center justify-center">
          <div className="text-center">
            <Image className="mx-auto mb-3 h-10 w-10 text-zinc-300" />
            <p className="text-sm font-medium text-zinc-600">No locations detected</p>
            <p className="mt-1 text-xs text-zinc-400">
              Scene environment tags are needed to derive locations.
            </p>
            <Button
              size="sm"
              variant="outline"
              className="mt-4"
              onClick={handleGenerate}
              loading={isGenerating}
            >
              Generate Backgrounds
            </Button>
          </div>
        </div>
      )}

      {/* Location Cards Grid */}
      {locations.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {locations.map((loc) => (
            <StageLocationCard
              key={loc.location_key}
              location={loc}
              isRegenerating={regeneratingKey === loc.location_key}
              onRegenerate={(tags) => handleRegenerate(loc.location_key, tags)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
