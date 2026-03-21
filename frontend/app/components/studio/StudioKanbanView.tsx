"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { Layers } from "lucide-react";
import { useStudioKanban } from "../../hooks/useStudioKanban";
import { useContextStore } from "../../store/useContextStore";
import { useUIStore, type StudioTab, DEFAULT_STUDIO_TAB } from "../../store/useUIStore";
import { deleteStoryboard } from "../../store/actions/storyboardActions";
import { cancelPendingSave } from "../../store/effects/autoSave";
import { resetAllStores, resetTransientStores } from "../../store/resetAllStores";
import { useChatStore } from "../../store/useChatStore";
import KanbanColumn from "./KanbanColumn";
import HomeSecondaryPanel from "./HomeSecondaryPanel";
import LoadingSpinner from "../ui/LoadingSpinner";
import Button from "../ui/Button";
import ConfirmDialog, { useConfirm } from "../ui/ConfirmDialog";
import { PAGE_2COL_LAYOUT, SECONDARY_PANEL_CLASSES } from "../ui/variants";
import { clearStudioUrlParams } from "../../utils/url";

const COLUMNS = ["draft", "in_prod", "rendered", "published"] as const;

const STATUS_TAB_MAP: Record<string, StudioTab> = {
  draft: "script",
  in_prod: "stage",
  rendered: "direct",
  published: "publish",
};

export default function StudioKanbanView() {
  const router = useRouter();
  const projectId = useContextStore((s) => s.projectId);
  const groups = useContextStore((s) => s.groups);
  const isLoadingGroups = useContextStore((s) => s.isLoadingGroups);
  const setUI = useUIStore((s) => s.set);
  const storyboardId = useContextStore((s) => s.storyboardId);
  const { columns, isLoading, total, refresh } = useStudioKanban();
  const { confirm, dialogProps } = useConfirm();

  const handleCardDelete = useCallback(
    async (id: number) => {
      const item = Object.values(columns)
        .flat()
        .find((i) => i.id === id);
      const ok = await confirm({
        title: "영상 삭제",
        message: (
          <>
            <span className="font-semibold text-zinc-900">{item?.title ?? "이 영상"}</span>
            을(를) 삭제하시겠습니까?
          </>
        ),
        confirmLabel: "삭제",
        variant: "danger",
      });
      if (!ok) return;
      const deleted = await deleteStoryboard(id);
      if (deleted) {
        if (id === storyboardId) {
          cancelPendingSave();
          await resetAllStores();
          clearStudioUrlParams();
        }
        await refresh();
      }
    },
    [columns, confirm, storyboardId, refresh]
  );

  const handleCardClick = (id: number, status: string) => {
    setUI({ activeTab: STATUS_TAB_MAP[status] ?? DEFAULT_STUDIO_TAB });
    router.push(`/studio?id=${id}`);
  };

  const handleNewShorts = async () => {
    cancelPendingSave();
    useContextStore.getState().resetContext();
    resetTransientStores();
    useChatStore.getState().clearMessages(null);

    // Draft 선생성 + isNewStoryboardMode 설정 → 채팅 화면 즉시 진입
    const { ensureDraftStoryboard } = await import("../../store/actions/draftActions");
    const draftId = await ensureDraftStoryboard();
    const currentSbId = useContextStore.getState().storyboardId;
    if (draftId === null) return;
    if (currentSbId !== null && currentSbId !== draftId) return;
    useUIStore.getState().set({ isNewStoryboardMode: true });
  };

  if (!projectId) {
    return (
      <div className="px-6 py-16 text-center">
        <p className="mb-2 text-sm text-zinc-500">영상을 만들려면 채널이 필요합니다.</p>
        <Button
          size="sm"
          onClick={() => setUI({ showSetupWizard: true, setupWizardInitialStep: 1 })}
        >
          채널 만들기
        </Button>
      </div>
    );
  }

  if (!isLoadingGroups && groups.length === 0) {
    return (
      <div className="px-6 py-16 text-center">
        <div className="mb-3 inline-flex rounded-full bg-amber-50 p-3">
          <Layers className="h-6 w-6 text-amber-500" />
        </div>
        <p className="mb-2 text-sm text-zinc-700">시리즈를 만들어야 영상을 저장할 수 있습니다.</p>
        <Button
          size="sm"
          onClick={() => setUI({ showSetupWizard: true, setupWizardInitialStep: 2 })}
        >
          시리즈 만들기
        </Button>
      </div>
    );
  }

  return (
    <div className="px-8 py-8">
      <div className={PAGE_2COL_LAYOUT}>
        {/* Primary — Kanban */}
        <div className="min-w-0">
          {/* Header */}
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-zinc-800">영상 목록</h2>
              <p className="text-xs text-zinc-400">
                {isLoading ? "로딩 중..." : `${total}개 영상`}
              </p>
            </div>
            <Button onClick={handleNewShorts} size="md">
              + 새 영상
            </Button>
          </div>

          {/* Kanban Grid */}
          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <LoadingSpinner size="lg" />
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              {COLUMNS.map((col) => (
                <KanbanColumn
                  key={col}
                  status={col}
                  items={columns[col] ?? []}
                  onCardClick={(id) => handleCardClick(id, col)}
                  onCardDelete={handleCardDelete}
                />
              ))}
            </div>
          )}
        </div>

        {/* Secondary */}
        <div className={SECONDARY_PANEL_CLASSES}>
          <HomeSecondaryPanel columns={columns} total={total} isLoading={isLoading} />
        </div>
      </div>

      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
