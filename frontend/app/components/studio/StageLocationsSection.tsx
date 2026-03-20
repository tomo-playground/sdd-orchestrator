"use client";

import { Image as ImageIcon, Loader2, RefreshCw } from "lucide-react";
import Button from "../ui/Button";
import ConfirmDialog from "../ui/ConfirmDialog";
import EmptyState from "../ui/EmptyState";
import StageLocationCard from "./StageLocationCard";
import { useStageLocations } from "./useStageLocations";

type Props = {
  storyboardId: number;
  onStatusChange: (ready: number, total: number) => void;
};

export default function StageLocationsSection({ storyboardId, onStatusChange }: Props) {
  const {
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
  } = useStageLocations(storyboardId, onStatusChange);

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
            disabled={isGenerating || isLoading || deletingKeys.size > 0}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            {locations.length > 0 ? "전체 재생성" : "생성"}
          </Button>
        </div>
      </div>

      {isLoading && locations.length === 0 && (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
        </div>
      )}

      {!isLoading && locations.length === 0 && (
        <EmptyState icon={ImageIcon} title="배경 이미지를 생성하세요" variant="inline" />
      )}

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
                isDeleting={deletingKeys.has(loc.location_key)}
                onRegenerate={(tags) => handleRegenerate(loc.location_key, tags)}
                onDelete={() => handleDelete(loc)}
              />
            ))}
          </div>
        </>
      )}
      <ConfirmDialog {...dialogProps} />
    </section>
  );
}
