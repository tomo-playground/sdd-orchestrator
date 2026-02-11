"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { FileText } from "lucide-react";
import ManualScriptEditor from "./ManualScriptEditor";
import AgentScriptEditor from "./AgentScriptEditor";

const TAB_BASE = "px-4 py-1.5 text-xs font-semibold rounded-lg transition";
const TAB_ACTIVE = `${TAB_BASE} bg-zinc-900 text-white`;
const TAB_INACTIVE = `${TAB_BASE} text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100`;

export default function ScriptEditorPanel() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const isNew = searchParams.get("new") === "true";
  const idParam = searchParams.get("id");
  const mode = searchParams.get("mode");
  const storyboardId = idParam ? Number(idParam) : null;
  const isAgent = mode === "agent";

  const hasEditor = isNew || storyboardId !== null;

  if (!hasEditor) {
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

  const toggleMode = (target: "manual" | "agent") => {
    const params = new URLSearchParams(searchParams.toString());
    if (target === "agent") {
      params.set("mode", "agent");
    } else {
      params.delete("mode");
    }
    router.replace(`/scripts?${params.toString()}`);
  };

  return (
    <div className="space-y-4">
      {/* Mode tabs */}
      <div className="flex gap-1 rounded-xl bg-zinc-50 p-1">
        <button
          className={isAgent ? TAB_INACTIVE : TAB_ACTIVE}
          onClick={() => toggleMode("manual")}
        >
          Manual
        </button>
        <button className={isAgent ? TAB_ACTIVE : TAB_INACTIVE} onClick={() => toggleMode("agent")}>
          AI Agent
        </button>
      </div>

      {/* Editor content */}
      {isAgent ? (
        <AgentScriptEditor />
      ) : storyboardId ? (
        <ManualScriptEditor key={storyboardId} storyboardId={storyboardId} />
      ) : (
        <ManualScriptEditor />
      )}
    </div>
  );
}
