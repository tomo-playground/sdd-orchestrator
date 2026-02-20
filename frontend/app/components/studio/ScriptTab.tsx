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
      {/* Editor — both modes use ManualScriptEditor */}
      <ManualScriptEditor editor={editor} onToggleMode={toggleMode} />

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
