"use client";

import { useCallback, useEffect, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useChatScriptEditor } from "../../hooks/useChatScriptEditor";
import { usePresets } from "../../hooks/usePresets";
import { useUIStore } from "../../store/useUIStore";
import { EXPRESS_SKIP_STAGES } from "../../utils/pipelineSteps";
import SettingsSidebar from "../chat/SettingsSidebar";
import ChatArea from "../chat/ChatArea";

export default function ScriptTab() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const idParam = searchParams.get("id");
  const legacyMode = searchParams.get("mode");
  const presetParam = searchParams.get("preset");
  const storyboardId = idParam ? Number(idParam) : null;
  const { presets, languages, durations } = usePresets();

  const onSaved = useCallback(
    (id: number) => {
      router.replace(`/studio?id=${id}`);
      useUIStore.getState().setActiveTab("stage");
    },
    [router]
  );
  const editor = useChatScriptEditor({ onSaved });

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

  // Legacy ?mode migration + preset initialization
  useEffect(() => {
    if (legacyMode) {
      const params = new URLSearchParams(searchParams.toString());
      params.delete("mode");
      if (legacyMode === "full") {
        params.set("preset", "standard");
        editor.setField("skipStages", []);
        editor.setField("preset", "standard");
      }
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

  const handleGenerate = () => {
    editor.confirmAndGenerate();
  };

  return (
    <div className="flex h-full">
      <SettingsSidebar
        editor={editor}
        presets={presets}
        languages={languages}
        durations={durations}
        onPresetChange={handlePresetChange}
        onGenerate={handleGenerate}
      />
      <ChatArea editor={editor} />
    </div>
  );
}
