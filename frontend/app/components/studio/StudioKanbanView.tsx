"use client";

import { useRouter } from "next/navigation";
import { useStudioKanban } from "../../hooks/useStudioKanban";
import { useContextStore } from "../../store/useContextStore";
import { useUIStore } from "../../store/useUIStore";
import KanbanColumn from "./KanbanColumn";
import HomeSecondaryPanel from "./HomeSecondaryPanel";
import LoadingSpinner from "../ui/LoadingSpinner";
import Button from "../ui/Button";
import { PAGE_2COL_LAYOUT, SECONDARY_PANEL_CLASSES } from "../ui/variants";

const COLUMNS = ["draft", "in_prod", "rendered", "published"] as const;

export default function StudioKanbanView() {
  const router = useRouter();
  const projectId = useContextStore((s) => s.projectId);
  const { columns, isLoading, total } = useStudioKanban();

  const handleCardClick = (id: number) => {
    router.push(`/studio?id=${id}`);
  };

  const handleNewShorts = () => {
    router.push("/studio?new=true");
  };

  if (!projectId) {
    return (
      <div className="px-6 py-16 text-center">
        <p className="mb-2 text-sm text-zinc-500">영상을 만들려면 채널이 필요합니다.</p>
        <Button
          size="sm"
          onClick={() =>
            useUIStore.getState().set({ showSetupWizard: true, setupWizardInitialStep: 1 })
          }
        >
          채널 만들기
        </Button>
      </div>
    );
  }

  return (
    <div className="px-6 py-8">
      <div className={PAGE_2COL_LAYOUT}>
        {/* Primary — Kanban */}
        <div className="min-w-0">
          {/* Header */}
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-zinc-800">Projects</h2>
              <p className="text-xs text-zinc-400">
                {isLoading ? "Loading..." : `${total} storyboard${total !== 1 ? "s" : ""}`}
              </p>
            </div>
            <Button onClick={handleNewShorts} size="md">
              + New Shorts
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
                  onCardClick={handleCardClick}
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
    </div>
  );
}
