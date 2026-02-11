"use client";

import { useSearchParams } from "next/navigation";
import { FileText } from "lucide-react";
import ManualScriptEditor from "./ManualScriptEditor";
import AgentScriptEditor from "./AgentScriptEditor";

export default function ScriptEditorPanel() {
  const searchParams = useSearchParams();
  const isNew = searchParams.get("new") === "true";
  const idParam = searchParams.get("id");
  const mode = searchParams.get("mode");
  const storyboardId = idParam ? Number(idParam) : null;

  // Agent mode
  if (storyboardId && mode === "agent") {
    return <AgentScriptEditor />;
  }

  // New script
  if (isNew) {
    return <ManualScriptEditor />;
  }

  // Edit existing
  if (storyboardId) {
    return <ManualScriptEditor key={storyboardId} storyboardId={storyboardId} />;
  }

  // Empty state
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
      <FileText className="h-10 w-10 text-zinc-200" />
      <div>
        <p className="text-sm font-medium text-zinc-400">Select a script or create new</p>
        <p className="mt-1 text-xs text-zinc-300">
          Choose from the list on the left, or click &quot;+ New&quot; to start
        </p>
      </div>
    </div>
  );
}
