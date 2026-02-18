"use client";

import { useCallback, useEffect, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { FileText } from "lucide-react";
import { useScriptEditor } from "../../hooks/useScriptEditor";
import { useUIStore } from "../../store/useUIStore";
import ManualScriptEditor from "../scripts/ManualScriptEditor";
import EmptyState from "../ui/EmptyState";
import { TAB_ACTIVE, TAB_INACTIVE } from "../ui/variants";

const TAB_BASE = "px-4 py-1.5 text-xs font-semibold rounded-lg transition";

export default function ScriptTab() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const idParam = searchParams.get("id");
  const mode = searchParams.get("mode");
  const storyboardId = idParam ? Number(idParam) : null;
  const isFull = mode === "full";

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

  const toggleMode = (target: "quick" | "full") => {
    const params = new URLSearchParams(searchParams.toString());
    if (target === "full") {
      params.set("mode", "full");
    } else {
      params.delete("mode");
    }
    editor.setField("mode", target);
    const qs = params.toString();
    router.replace(qs ? `/studio?${qs}` : "/studio");
  };

  return (
    <div className="mx-auto w-full max-w-5xl">
      {/* Mode tabs + status badges */}
      <div className="mb-6 flex items-center justify-center gap-3">
        <div className="flex gap-1 rounded-xl bg-zinc-100 p-1">
          <button
            className={`${TAB_BASE} ${isFull ? TAB_INACTIVE : TAB_ACTIVE}`}
            onClick={() => toggleMode("quick")}
          >
            Quick
          </button>
          <button
            className={`${TAB_BASE} ${isFull ? TAB_ACTIVE : TAB_INACTIVE}`}
            onClick={() => toggleMode("full")}
          >
            Full
          </button>
        </div>
        {editor.scenes.length > 0 && (
          <span className="rounded-full bg-zinc-100 px-2.5 py-1 text-xs text-zinc-500">
            {editor.scenes.length} scenes
          </span>
        )}
      </div>

      {/* Editor — both modes use ManualScriptEditor */}
      <ManualScriptEditor editor={editor} />

      {editor.scenes.length === 0 && !editor.isGenerating && !editor.isWaitingForInput && (
        <div className="mt-12">
          <EmptyState
            icon={FileText}
            title="Start Writing"
            description="Enter a topic and click Generate Script, or write your own scenes manually."
          />
        </div>
      )}
    </div>
  );
}
