"use client";

import { useCallback, useEffect, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { FileText } from "lucide-react";
import { useScriptEditor } from "../../hooks/useScriptEditor";
import { useUIStore } from "../../store/useUIStore";
import { useContextStore } from "../../store/useContextStore";
import { SCRIPTS_LIST_REFRESH } from "../../constants";
import ManualScriptEditor from "../scripts/ManualScriptEditor";
import AgentScriptEditor from "../scripts/AgentScriptEditor";
import ScriptSceneList from "../scripts/ScriptSceneList";
import EmptyState from "../ui/EmptyState";
import { TAB_ACTIVE, TAB_INACTIVE } from "../ui/variants";

const TAB_BASE = "px-4 py-1.5 text-xs font-semibold rounded-lg transition";

export default function ScriptTab() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const idParam = searchParams.get("id");
  const mode = searchParams.get("mode");
  const storyboardId = idParam ? Number(idParam) : null;
  const isAgent = mode === "agent";

  const onSaved = useCallback(
    (id: number) => {
      // Update URL to reflect saved storyboard
      router.replace(`/studio?id=${id}`);
      // Switch to Edit tab
      useUIStore.getState().setActiveTab("edit");
    },
    [router]
  );
  const editor = useScriptEditor({ onSaved });

  // Load storyboard when URL id changes
  const loadedRef = useRef<number | null>(null);
  useEffect(() => {
    if (storyboardId && loadedRef.current !== storyboardId) {
      loadedRef.current = storyboardId;
      editor.loadStoryboard(storyboardId);
    } else if (!storyboardId && loadedRef.current !== null) {
      loadedRef.current = null;
      editor.reset();
    }
  }, [storyboardId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Agent completion handler
  const handleStoryboardCreated = useCallback(
    (id: number) => {
      router.replace(`/studio?id=${id}`);
      useContextStore.getState().setContext({ storyboardId: id });
      window.dispatchEvent(new CustomEvent(SCRIPTS_LIST_REFRESH));
    },
    [router]
  );

  const toggleMode = (target: "manual" | "agent") => {
    const params = new URLSearchParams();
    if (storyboardId) params.set("id", String(storyboardId));
    if (target === "agent") params.set("mode", "agent");
    const qs = params.toString();
    router.replace(qs ? `/studio?${qs}` : "/studio");
  };

  return (
    <div className="space-y-4">
      {/* Mode tabs */}
      <div className="flex gap-1 rounded-xl bg-zinc-50 p-1">
        <button
          className={`${TAB_BASE} ${isAgent ? TAB_INACTIVE : TAB_ACTIVE}`}
          onClick={() => toggleMode("manual")}
        >
          Manual
        </button>
        <button
          className={`${TAB_BASE} ${isAgent ? TAB_ACTIVE : TAB_INACTIVE}`}
          onClick={() => toggleMode("agent")}
        >
          AI Agent
        </button>
      </div>

      {/* Mode-specific editor */}
      {isAgent ? (
        <AgentScriptEditor onStoryboardCreated={handleStoryboardCreated} />
      ) : (
        <ManualScriptEditor editor={editor} />
      )}

      {/* Shared scene list */}
      {editor.scenes.length > 0 ? (
        <ScriptSceneList
          scenes={editor.scenes}
          storyboardId={editor.storyboardId}
          isSaving={editor.isSaving}
          onUpdateScene={editor.updateScene}
          onSave={editor.save}
        />
      ) : !isAgent ? (
        <EmptyState
          icon={FileText}
          title="No scenes generated yet"
          description="Enter a topic and click Generate Script"
        />
      ) : null}
    </div>
  );
}
