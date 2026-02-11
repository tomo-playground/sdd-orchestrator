"use client";

import { useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Sparkles } from "lucide-react";
import { useScriptEditor } from "../../hooks/useScriptEditor";
import { usePresets } from "../../hooks/usePresets";
import StoryboardGeneratorPanel from "../storyboard/StoryboardGeneratorPanel";
import CharacterSelectSection from "./CharacterSelectSection";
import ScriptSceneList from "./ScriptSceneList";
import Button from "../ui/Button";

type Props = {
  storyboardId?: number | null;
};

export default function ManualScriptEditor({ storyboardId }: Props) {
  const router = useRouter();
  const onSaved = useCallback((id: number) => router.replace(`/scripts?id=${id}`), [router]);
  const editor = useScriptEditor({ onSaved });
  const { presets, languages, durations } = usePresets();
  const loadedRef = useRef<number | null>(null);

  // Load existing storyboard
  useEffect(() => {
    if (storyboardId && loadedRef.current !== storyboardId) {
      loadedRef.current = storyboardId;
      editor.loadStoryboard(storyboardId);
    }
  }, [storyboardId]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-6">
      {/* Story settings */}
      <StoryboardGeneratorPanel
        presets={presets}
        languages={languages}
        durations={durations}
        topic={editor.topic}
        setTopic={(v) => editor.setField("topic", v)}
        description={editor.description}
        setDescription={(v) => editor.setField("description", v)}
        duration={editor.duration}
        setDuration={(v) => editor.setField("duration", v)}
        language={editor.language}
        setLanguage={(v) => editor.setField("language", v)}
        structure={editor.structure}
        setStructure={(v) => editor.setField("structure", v)}
      />

      {/* Character selection */}
      <CharacterSelectSection
        structure={editor.structure}
        characterId={editor.characterId}
        characterBId={editor.characterBId}
        onChangeA={(id) => editor.setField("characterId", id)}
        onChangeB={(id) => editor.setField("characterBId", id)}
      />

      {/* Generate button */}
      <div className="flex justify-end">
        <Button
          size="md"
          variant="gradient"
          disabled={!editor.topic.trim() || editor.isGenerating}
          onClick={editor.generate}
        >
          {editor.isGenerating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4" />
          )}
          {editor.isGenerating ? "Generating..." : "Generate Script"}
        </Button>
      </div>

      {/* Scene list */}
      <ScriptSceneList
        scenes={editor.scenes}
        storyboardId={editor.storyboardId}
        isSaving={editor.isSaving}
        onUpdateScene={editor.updateScene}
        onSave={editor.save}
      />
    </div>
  );
}
