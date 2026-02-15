"use client";

import { useCallback, useEffect, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { FileText } from "lucide-react";
import { useScriptEditor } from "../../hooks/useScriptEditor";
import { useUIStore } from "../../store/useUIStore";
import { useContextStore } from "../../store/useContextStore";
import ManualScriptEditor from "../scripts/ManualScriptEditor";
import AgentScriptEditor from "../scripts/AgentScriptEditor";
import ScriptSceneList from "../scripts/ScriptSceneList";
import EmptyState from "../ui/EmptyState";
import { TAB_ACTIVE, TAB_INACTIVE } from "../ui/variants";
import ScriptSidePanel from "./ScriptSidePanel";
import StudioThreeColumnLayout from "./StudioThreeColumnLayout";

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
      router.replace(`/studio?id=${id}`);
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
    },
    [router]
  );

  const toggleMode = (target: "quick" | "agent") => {
    const params = new URLSearchParams(searchParams.toString());
    if (target === "agent") {
      params.set("mode", "agent");
    } else {
      params.delete("mode");
    }
    const qs = params.toString();
    router.replace(qs ? `/studio?${qs}` : "/studio");
  };

  return (
    <StudioThreeColumnLayout
      leftPanel={
        editor.scenes.length > 0 ? (
          <div className="h-full overflow-y-auto p-4">
            <h3 className="mb-4 text-xs font-semibold tracking-wider text-zinc-500 uppercase">
              Scene Outline
            </h3>
            <ScriptSceneList
              scenes={editor.scenes}
              isSaving={editor.isSaving}
              approveLabel="Approve & Edit"
              onApprove={editor.save}
              compact
            />
          </div>
        ) : (
          <div className="flex h-full flex-col items-center justify-center p-6 text-center text-zinc-400">
            <FileText className="mb-2 h-8 w-8 opacity-20" />
            <p className="text-xs">No scenes yet</p>
          </div>
        )
      }
      centerPanel={
        <div className="mx-auto w-full max-w-3xl px-8 py-8">
          {/* Mode tabs */}
          <div className="mb-6 flex justify-center">
            <div className="flex gap-1 rounded-xl bg-zinc-100 p-1">
              <button
                className={`${TAB_BASE} ${isAgent ? TAB_INACTIVE : TAB_ACTIVE}`}
                onClick={() => toggleMode("quick")}
              >
                Quick
              </button>
              <button
                className={`${TAB_BASE} ${isAgent ? TAB_ACTIVE : TAB_INACTIVE}`}
                onClick={() => toggleMode("agent")}
              >
                AI Agent
              </button>
            </div>
          </div>

          {/* Mode-specific editor */}
          {isAgent ? (
            <AgentScriptEditor onStoryboardCreated={handleStoryboardCreated} />
          ) : (
            <ManualScriptEditor editor={editor} />
          )}

          {!isAgent && editor.scenes.length === 0 && !editor.isGenerating && (
            <div className="mt-12">
              <EmptyState
                icon={FileText}
                title="Start Writing"
                description="Enter a topic and click Generate Script, or write your own scenes manually."
              />
            </div>
          )}
        </div>
      }
      rightPanel={<ScriptSidePanel scenesCount={editor.scenes.length} isAgent={isAgent} />}
    />
  );
}
