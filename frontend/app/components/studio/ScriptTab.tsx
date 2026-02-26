"use client";

import { useCallback, useEffect, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { FileText } from "lucide-react";
import { useScriptEditor } from "../../hooks/useScriptEditor";
import { useUIStore } from "../../store/useUIStore";
import ManualScriptEditor from "../scripts/ManualScriptEditor";
import EmptyState from "../ui/EmptyState";

export default function ScriptTab() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const idParam = searchParams.get("id");
  const legacyMode = searchParams.get("mode");
  const presetParam = searchParams.get("preset");
  const storyboardId = idParam ? Number(idParam) : null;

  // Track preset for onSaved callback (Express skips Stage)
  const presetRef = useRef(presetParam);
  useEffect(() => {
    presetRef.current = presetParam;
  }, [presetParam]);

  const onSaved = useCallback(
    (id: number) => {
      router.replace(`/studio?id=${id}`);
      const isExpress = !presetRef.current || presetRef.current === "express";
      useUIStore.getState().setActiveTab(isExpress ? "direct" : "stage");
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

  // Legacy ?mode=full/quick migration + preset initialization
  useEffect(() => {
    if (legacyMode) {
      const params = new URLSearchParams(searchParams.toString());
      params.delete("mode");
      if (legacyMode === "full") {
        params.set("preset", "standard");
        editor.setField("skipStages", []);
        editor.setField("preset", "standard");
      }
      // ?mode=quick → just remove param (Express is default)
      const qs = params.toString();
      router.replace(qs ? `/studio?${qs}` : "/studio");
    } else if (presetParam === "standard" || presetParam === "creator") {
      editor.setField("skipStages", []);
      editor.setField("preset", presetParam);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePresetChange = (preset: string, skipStages: string[]) => {
    const params = new URLSearchParams(searchParams.toString());
    if (preset !== "express") {
      params.set("preset", preset);
    } else {
      params.delete("preset");
    }
    params.delete("mode");
    editor.setField("skipStages", skipStages);
    editor.setField("preset", preset);
    const qs = params.toString();
    router.replace(qs ? `/studio?${qs}` : "/studio");
  };

  return (
    <div className="mx-auto w-full max-w-5xl">
      {/* Editor — both modes use ManualScriptEditor */}
      <ManualScriptEditor editor={editor} onPresetChange={handlePresetChange} />

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
