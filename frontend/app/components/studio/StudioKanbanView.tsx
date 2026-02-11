"use client";

import { useRouter } from "next/navigation";
import { useStudioKanban } from "../../hooks/useStudioKanban";
import { useContextStore } from "../../store/useContextStore";
import KanbanColumn from "./KanbanColumn";
import LoadingSpinner from "../ui/LoadingSpinner";
import { CONTAINER_CLASSES, cx } from "../ui/variants";

const COLUMNS = ["draft", "in_prod", "rendered", "published"] as const;

export default function StudioKanbanView() {
  const router = useRouter();
  const projectId = useContextStore((s) => s.projectId);
  const { columns, isLoading, total } = useStudioKanban();

  const handleCardClick = (id: number) => {
    router.push(`/studio?id=${id}`);
  };

  const handleNewShorts = () => {
    router.push("/scripts?new=true");
  };

  if (!projectId) {
    return (
      <div className={cx(CONTAINER_CLASSES, "py-16 text-center")}>
        <p className="text-sm text-zinc-400">Select a project to view storyboards.</p>
      </div>
    );
  }

  return (
    <div className={cx(CONTAINER_CLASSES, "py-8")}>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-zinc-800">Studio</h2>
          <p className="text-xs text-zinc-400">
            {isLoading ? "Loading..." : `${total} storyboard${total !== 1 ? "s" : ""}`}
          </p>
        </div>
        <button
          onClick={handleNewShorts}
          className="rounded-lg bg-zinc-900 px-4 py-2 text-xs font-semibold text-white transition hover:bg-zinc-800"
        >
          + New Shorts
        </button>
      </div>

      {/* Kanban Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <LoadingSpinner size="lg" />
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-4">
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
  );
}
