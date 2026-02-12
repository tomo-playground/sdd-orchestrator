"use client";

import { useCallback, useEffect, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { FileText } from "lucide-react";
import { useScriptEditor } from "../../hooks/useScriptEditor";
import { useContextStore } from "../../store/useContextStore";
import { SCRIPTS_LIST_REFRESH } from "../../constants";
import ManualScriptEditor from "./ManualScriptEditor";
import AgentScriptEditor from "./AgentScriptEditor";
import ScriptSceneList from "./ScriptSceneList";
import EmptyState from "../ui/EmptyState";

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

  // Lifted: useScriptEditor at panel level (shared by Manual & Agent)
  const onSaved = useCallback(
    (id: number) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set("id", String(id));
      params.delete("new");
      router.replace(`/scripts?${params.toString()}`);
    },
    [router, searchParams]
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

  // Agent completion: keep mode=agent, add id
  const handleStoryboardCreated = useCallback(
    (id: number) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set("id", String(id));
      router.replace(`/scripts?${params.toString()}`);
      useContextStore.getState().setContext({ storyboardId: id });
      window.dispatchEvent(new CustomEvent(SCRIPTS_LIST_REFRESH));
    },
    [router, searchParams]
  );

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

      {/* Mode-specific top area */}
      {isAgent ? (
        <AgentScriptEditor onStoryboardCreated={handleStoryboardCreated} />
      ) : (
        <ManualScriptEditor editor={editor} />
      )}

      {/* Shared scene list (always visible) */}
      {editor.scenes.length > 0 ? (
        <ScriptSceneList
          scenes={editor.scenes}
          storyboardId={editor.storyboardId}
          isSaving={editor.isSaving}
          onUpdateScene={editor.updateScene}
          onSave={editor.save}
        />
      ) : hasEditor && !isAgent ? (
        <EmptyState
          icon={FileText}
          title="아직 생성된 씬이 없습니다"
          description="Topic을 입력하고 Generate Script를 클릭하세요"
        />
      ) : null}
    </div>
  );
}
