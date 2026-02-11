"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { X, ChevronRight, Clapperboard } from "lucide-react";
import { useContextStore } from "../../store/useContextStore";

export default function PersistentContextBar() {
  const pathname = usePathname();
  const storyboardId = useContextStore((s) => s.storyboardId);
  const storyboardTitle = useContextStore((s) => s.storyboardTitle);
  const projectId = useContextStore((s) => s.projectId);
  const groupId = useContextStore((s) => s.groupId);
  const projects = useContextStore((s) => s.projects);
  const groups = useContextStore((s) => s.groups);

  // Hide on Studio page (has its own ContextBar) or when no storyboard
  if (pathname.startsWith("/studio") || storyboardId === null) return null;

  const projectName = projects.find((p) => p.id === projectId)?.name;
  const groupName = groups.find((g) => g.id === groupId)?.name;
  const resetContext = useContextStore.getState().resetContext;

  return (
    <div className="flex h-8 shrink-0 items-center justify-between border-b border-zinc-100 bg-zinc-50/80 px-6 text-xs text-zinc-500">
      <div className="flex items-center gap-1.5 truncate">
        <Clapperboard className="h-3 w-3 shrink-0 text-zinc-400" />
        {projectName && (
          <>
            <span className="truncate">{projectName}</span>
            <ChevronRight className="h-3 w-3 shrink-0 text-zinc-300" />
          </>
        )}
        {groupName && (
          <>
            <span className="truncate">{groupName}</span>
            <ChevronRight className="h-3 w-3 shrink-0 text-zinc-300" />
          </>
        )}
        <Link
          href={`/studio?id=${storyboardId}`}
          className="truncate font-medium text-zinc-700 hover:text-zinc-900 hover:underline"
        >
          {storyboardTitle || "Untitled"}
        </Link>
      </div>
      <button
        onClick={resetContext}
        className="ml-2 shrink-0 rounded p-0.5 text-zinc-400 transition hover:bg-zinc-200 hover:text-zinc-600"
        title="Dismiss storyboard context"
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}
