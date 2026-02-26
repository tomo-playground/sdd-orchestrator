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
      await axios.post(
        `${API_BASE}/storyboards/${storyboardId}/stage/generate-backgrounds`,
        null,
        { timeout: API_TIMEOUT.STAGE_GENERATE }
      );
      showToast("Background generation complete", "success");
      await fetchStatus();
    } catch (error) {
      showToast(getErrorMsg(error, "Background generation failed"), "error");
      useStoryboardStore.getState().set({ stageStatus: "failed" });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRegenerate = async (locationKey: string) => {
    if (!storyboardId) return;
    setRegeneratingKey(locationKey);
    try {
      const res = await axios.post(
        `${API_BASE}/storyboards/${storyboardId}/stage/regenerate-background/${locationKey}`,
        null,
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

  const handleAssign = async () => {
    if (!storyboardId) return;
    setIsAssigning(true);
    try {
      const res = await axios.post(
        `${API_BASE}/storyboards/${storyboardId}/stage/assign-backgrounds`,
        null,
        { timeout: API_TIMEOUT.DEFAULT }
      );
      const count = res.data.assignments?.length ?? 0;
      showToast(`${count} scenes assigned to backgrounds`, "success");
      await fetchStatus();
    } catch (error) {
      showToast(getErrorMsg(error, "Assignment failed"), "error");
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
              onClick={handleAssign}
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
              <Button size="sm" onClick={() => setActiveTab("direct")}>
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
            <LocationCard
              key={loc.location_key}
              location={loc}
              isRegenerating={regeneratingKey === loc.location_key}
              onRegenerate={() => handleRegenerate(loc.location_key)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Location Card ─────────────────────────────────────────────

function LocationCard({
  location,
  isRegenerating,
  onRegenerate,
}: {
  location: StageLocationStatus;
  isRegenerating: boolean;
  onRegenerate: () => void;
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
      {/* Image area */}
      <div className="relative aspect-video bg-zinc-100">
        {location.has_image && location.image_url ? (
          <img
            src={location.image_url}
            alt={location.location_key}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <Image className="h-8 w-8 text-zinc-300" />
          </div>
        )}
        {isRegenerating && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40">
            <Loader2 className="h-6 w-6 animate-spin text-white" />
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-zinc-900">
            {location.location_key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
          </h3>
          {location.has_image ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          ) : (
            <AlertCircle className="h-4 w-4 text-zinc-300" />
          )}
        </div>

        {/* Tags */}
        <div className="mb-2 flex flex-wrap gap-1">
          {location.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] text-zinc-600"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* Scene count */}
        <p className="mb-2 text-[11px] text-zinc-400">
          {location.scene_ids.length} scene{location.scene_ids.length !== 1 ? "s" : ""}
        </p>

        {/* Actions */}
        <Button
          size="sm"
          variant="outline"
          className="w-full"
          onClick={onRegenerate}
          loading={isRegenerating}
          disabled={isRegenerating}
        >
          <RefreshCw className="h-3 w-3" />
          {location.has_image ? "Regenerate" : "Generate"}
        </Button>
      </div>
    </div>
  );
}
