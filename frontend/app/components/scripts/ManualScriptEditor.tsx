"use client";

import { useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Sparkles } from "lucide-react";
import { useScriptEditor } from "../../hooks/useScriptEditor";
import { useCharacters } from "../../hooks/useCharacters";
import StoryboardGeneratorPanel from "../storyboard/StoryboardGeneratorPanel";
import ScriptSceneList from "./ScriptSceneList";
import Button from "../ui/Button";
import { SECTION_CLASSES, FORM_INPUT_CLASSES, FORM_LABEL_CLASSES, cx } from "../ui/variants";

type Props = {
  storyboardId?: number | null;
};

export default function ManualScriptEditor({ storyboardId }: Props) {
  const router = useRouter();
  const onSaved = useCallback((id: number) => router.replace(`/scripts?id=${id}`), [router]);
  const editor = useScriptEditor({ onSaved });
  const { characters } = useCharacters();
  const loadedRef = useRef<number | null>(null);

  // Load existing storyboard
  useEffect(() => {
    if (storyboardId && loadedRef.current !== storyboardId) {
      loadedRef.current = storyboardId;
      editor.loadStoryboard(storyboardId);
    }
  }, [storyboardId]); // eslint-disable-line react-hooks/exhaustive-deps

  const isMultiChar = editor.structure === "Dialogue" || editor.structure === "Narrated Dialogue";

  return (
    <div className="space-y-6">
      {/* Story settings */}
      <StoryboardGeneratorPanel
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
      <section className={cx(SECTION_CLASSES, "space-y-3")}>
        <h3 className="text-xs font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Characters
        </h3>
        <div className={isMultiChar ? "grid grid-cols-2 gap-3" : ""}>
          <div>
            <label className={`mb-1 block ${FORM_LABEL_CLASSES}`}>
              {isMultiChar ? "Character A" : "Character"}
            </label>
            <select
              value={editor.characterId ?? ""}
              onChange={(e) =>
                editor.setField("characterId", e.target.value ? Number(e.target.value) : null)
              }
              className={FORM_INPUT_CLASSES}
            >
              <option value="">None</option>
              {characters.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          {isMultiChar && (
            <div>
              <label className={`mb-1 block ${FORM_LABEL_CLASSES}`}>Character B</label>
              <select
                value={editor.characterBId ?? ""}
                onChange={(e) =>
                  editor.setField("characterBId", e.target.value ? Number(e.target.value) : null)
                }
                className={FORM_INPUT_CLASSES}
              >
                <option value="">None</option>
                {characters.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </section>

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
