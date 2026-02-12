"use client";

import { Loader2, Sparkles } from "lucide-react";
import { usePresets } from "../../hooks/usePresets";
import ConfirmDialog, { useConfirm } from "../ui/ConfirmDialog";
import StoryboardGeneratorPanel from "../storyboard/StoryboardGeneratorPanel";
import CharacterSelectSection from "./CharacterSelectSection";
import Button from "../ui/Button";
import { SECTION_CLASSES } from "../ui/variants";
import type { ScriptEditorActions } from "../../hooks/useScriptEditor";

type Props = {
  editor: ScriptEditorActions;
};

export default function ManualScriptEditor({ editor }: Props) {
  const { presets, languages, durations } = usePresets();
  const { confirm, dialogProps } = useConfirm();

  return (
    <div className="space-y-6">
      {/* Story settings + Characters + Generate — single card */}
      <section className={SECTION_CLASSES}>
        <StoryboardGeneratorPanel
          embedded
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

        {/* Divider + Characters */}
        <div className="mt-6 border-t border-zinc-200/60 pt-5">
          <CharacterSelectSection
            embedded
            structure={editor.structure}
            characterId={editor.characterId}
            characterBId={editor.characterBId}
            onChangeA={(id) => editor.setField("characterId", id)}
            onChangeB={(id) => editor.setField("characterBId", id)}
          />
        </div>

        {/* Generate button — card footer */}
        <div className="mt-5 flex justify-end border-t border-zinc-200/60 pt-5">
          <Button
            size="md"
            variant="gradient"
            disabled={!editor.topic.trim() || editor.isGenerating}
            onClick={async () => {
              if (editor.scenes.length > 0) {
                const ok = await confirm({
                  title: "스크립트 재생성",
                  message: `기존 ${editor.scenes.length}개 씬이 교체됩니다. 계속하시겠습니까?`,
                  confirmLabel: "재생성",
                  variant: "danger",
                });
                if (!ok) return;
              }
              editor.generate();
            }}
          >
            {editor.isGenerating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {editor.isGenerating ? "Generating..." : "Generate Script"}
          </Button>
        </div>
      </section>

      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
