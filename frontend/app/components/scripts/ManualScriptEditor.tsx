"use client";

import { useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Sparkles, FileText } from "lucide-react";
import { useScriptEditor } from "../../hooks/useScriptEditor";
import { usePresets } from "../../hooks/usePresets";
import ConfirmDialog, { useConfirm } from "../ui/ConfirmDialog";
import StoryboardGeneratorPanel from "../storyboard/StoryboardGeneratorPanel";
import CharacterSelectSection from "./CharacterSelectSection";
import ScriptSceneList from "./ScriptSceneList";
import EmptyState from "../ui/EmptyState";
import Button from "../ui/Button";
import { SECTION_CLASSES } from "../ui/variants";

type Props = {
  storyboardId?: number | null;
};

export default function ManualScriptEditor({ storyboardId }: Props) {
  const router = useRouter();
  const onSaved = useCallback((id: number) => router.replace(`/scripts?id=${id}`), [router]);
  const editor = useScriptEditor({ onSaved });
  const { presets, languages, durations } = usePresets();
  const { confirm, dialogProps } = useConfirm();
  const loadedRef = useRef<number | null>(null);

  // Load existing storyboard
  useEffect(() => {
    if (storyboardId && loadedRef.current !== storyboardId) {
      loadedRef.current = storyboardId;
      editor.loadStoryboard(storyboardId);
    }
  }, [storyboardId]); // eslint-disable-line react-hooks/exhaustive-deps

  const hasScenes = editor.scenes.length > 0;

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

      {/* Scene list or empty hint */}
      {hasScenes ? (
        <ScriptSceneList
          scenes={editor.scenes}
          storyboardId={editor.storyboardId}
          isSaving={editor.isSaving}
          onUpdateScene={editor.updateScene}
          onSave={editor.save}
        />
      ) : (
        <EmptyState
          icon={FileText}
          title="아직 생성된 씬이 없습니다"
          description="Topic을 입력하고 Generate Script를 클릭하세요"
        />
      )}

      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
