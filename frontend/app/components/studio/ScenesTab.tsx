"use client";

import Button from "../ui/Button";

import { useShallow } from "zustand/react/shallow";
import { Film } from "lucide-react";
import ConfirmDialog from "../ui/ConfirmDialog";
import EmptyState from "../ui/EmptyState";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useRenderStore } from "../../store/useRenderStore";
import { useUIStore } from "../../store/useUIStore";
import { useTags } from "../../hooks";
import SceneListPanel from "../storyboard/SceneListPanel";
import SceneInsightsContent from "./SceneInsightsContent";
import SceneCard from "../storyboard/SceneCard";
import SceneNavHeader from "./SceneNavHeader";
import { STUDIO_2COL_LAYOUT, LEFT_PANEL_CLASSES, CENTER_PANEL_CLASSES } from "../ui/variants";
import { buildNegativePrompt, buildScenePrompt } from "../../store/actions/promptActions";
import {
  resolveCharacterIdForSpeaker,
  resolveBasePromptForSpeaker,
  resolveCharacterLorasForSpeaker,
} from "../../utils/speakerResolver";
import {
  handleGenerateImage,
  handleImageUpload,
  handleEditWithGemini,
  handleSuggestEditWithGemini,
} from "../../store/actions/imageActions";
import {
  applyMissingImageTags,
  handleSpeakerChange,
  handleValidateImage,
  handleMarkSuccess,
  handleMarkFail,
  handleSavePrompt,
} from "../../store/actions/sceneActions";
import { useSceneActions } from "../../hooks/useSceneActions";

export default function ScenesTab() {
  const { scenes, currentSceneIndex } = useStoryboardStore(
    useShallow((s) => ({ scenes: s.scenes, currentSceneIndex: s.currentSceneIndex }))
  );

  const imageValidationResults = useStoryboardStore((s) => s.imageValidationResults);

  const { sceneMenuOpen, validatingSceneId, markingStatusSceneId, imageGenProgress } =
    useStoryboardStore(
      useShallow((s) => ({
        sceneMenuOpen: s.sceneMenuOpen,
        validatingSceneId: s.validatingSceneId,
        markingStatusSceneId: s.markingStatusSceneId,
        imageGenProgress: s.imageGenProgress,
      }))
    );

  const {
    loraTriggerWords,
    characterLoras,
    characterBLoras,
    selectedCharacterId,
    selectedCharacterBId,
    selectedCharacterName,
    selectedCharacterBName,
    basePromptA,
    basePromptB,
  } = useStoryboardStore(
    useShallow((s) => ({
      loraTriggerWords: s.loraTriggerWords,
      characterLoras: s.characterLoras,
      characterBLoras: s.characterBLoras,
      selectedCharacterId: s.selectedCharacterId,
      selectedCharacterBId: s.selectedCharacterBId,
      selectedCharacterName: s.selectedCharacterName,
      selectedCharacterBName: s.selectedCharacterBName,
      basePromptA: s.basePromptA,
      basePromptB: s.basePromptB,
    }))
  );

  const reorderScenes = useStoryboardStore((s) => s.reorderScenes);
  const sbSet = useStoryboardStore((s) => s.set);
  const showToast = useUIStore((s) => s.showToast);
  const { tagsByGroup, sceneTagGroups, isExclusiveGroup } = useTags(null);

  const {
    setCurrentSceneIndex,
    handleUpdateScene,
    handlePinToggle,
    handleRemoveScene,
    handleAddScene,
    confirm,
    dialogProps,
  } = useSceneActions();

  const currentScene = scenes[currentSceneIndex];
  const currentSpeaker = currentScene?.speaker ?? "A";
  const resolvedCharacterId = resolveCharacterIdForSpeaker(currentSpeaker, {
    selectedCharacterId,
    selectedCharacterBId,
  });
  const resolvedBasePrompt = resolveBasePromptForSpeaker(currentSpeaker, basePromptA, basePromptB);
  const resolvedCharacterLoras = resolveCharacterLorasForSpeaker(
    currentSpeaker,
    characterLoras,
    characterBLoras
  );
  const pinnedSceneOrder = currentScene?.environment_reference_id
    ? scenes.find((s) => s.image_asset_id === currentScene.environment_reference_id)?.order
    : undefined;

  const setActiveTab = useUIStore((s) => s.setActiveTab);
  const showAdvancedSettings = useUIStore((s) => s.showAdvancedSettings);
  const toggleAdvancedSettings = useUIStore((s) => s.toggleAdvancedSettings);
  const currentStyleProfile = useRenderStore((s) => s.currentStyleProfile);

  if (scenes.length === 0) {
    return (
      <EmptyState
        icon={Film}
        title="No scenes yet"
        description="Create a script first to get started with your storyboard."
        action={
          <Button onClick={() => setActiveTab("script")} size="lg">
            Go to Script
          </Button>
        }
      />
    );
  }

  return (
    <>
      <div className={STUDIO_2COL_LAYOUT}>
        {/* ── Left Panel: Scene List + Insights ── */}
        <aside className={LEFT_PANEL_CLASSES}>
          <SceneListPanel
            scenes={scenes}
            currentSceneIndex={currentSceneIndex}
            onSceneSelect={setCurrentSceneIndex}
            onAddScene={handleAddScene}
            onRemoveScene={(idx) => handleRemoveScene(scenes[idx].client_id)}
            onReorderScene={reorderScenes}
            imageValidationResults={imageValidationResults}
          />
          <div className="space-y-4 border-t border-zinc-200 p-4">
            <SceneInsightsContent
              imageValidationResults={imageValidationResults}
              scenes={scenes.map((s, i) => ({ id: s.id, client_id: s.client_id, order: i }))}
              onSceneSelect={setCurrentSceneIndex}
              fullScenes={scenes}
            />
          </div>
        </aside>

        {/* ── Center Panel: Context Strip + Scene Editor ── */}
        <main className={CENTER_PANEL_CLASSES}>
          {/* Context Strip — read-only badges + Advanced toggle + Stage deep link */}
          <div className="flex shrink-0 items-center gap-2 border-b border-zinc-100 bg-white px-8 py-1.5">
            {currentStyleProfile && (
              <span className="rounded-full bg-violet-50 px-2 py-0.5 text-[11px] font-medium text-violet-700">
                {currentStyleProfile.display_name ?? currentStyleProfile.name}
              </span>
            )}
            {selectedCharacterName && (
              <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-700">
                A: {selectedCharacterName}
              </span>
            )}
            {selectedCharacterBName && (
              <span className="rounded-full bg-teal-50 px-2 py-0.5 text-[11px] font-medium text-teal-700">
                B: {selectedCharacterBName}
              </span>
            )}
            <div className="ml-auto flex items-center gap-3">
              <button
                onClick={toggleAdvancedSettings}
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium transition ${
                  showAdvancedSettings
                    ? "bg-zinc-900 text-white"
                    : "border border-zinc-200 text-zinc-400 hover:border-zinc-300 hover:text-zinc-500"
                }`}
              >
                Advanced
              </button>
              <button
                onClick={() => setActiveTab("stage")}
                className="text-[11px] font-medium text-zinc-400 transition hover:text-zinc-600"
              >
                Edit in Stage →
              </button>
            </div>
          </div>

          <SceneNavHeader
            currentIndex={currentSceneIndex}
            total={scenes.length}
            duration={currentScene?.duration}
            onPrev={() => setCurrentSceneIndex(Math.max(0, currentSceneIndex - 1))}
            onNext={() => setCurrentSceneIndex(Math.min(scenes.length - 1, currentSceneIndex + 1))}
            onRemove={() => handleRemoveScene(currentScene.client_id)}
          />

          {currentScene && (
            <div className="scrollbar-hide flex-1 overflow-y-auto px-8 py-8">
              <div className="mx-auto w-full max-w-5xl">
                <SceneCard
                  key={currentScene.client_id}
                  scene={currentScene}
                  sceneIndex={currentSceneIndex}
                  imageValidationResult={imageValidationResults[currentScene.client_id]}
                  qualityScore={
                    imageValidationResults[currentScene.client_id]
                      ? {
                          match_rate:
                            imageValidationResults[currentScene.client_id].match_rate ?? 0,
                          missing_tags:
                            imageValidationResults[currentScene.client_id].missing ?? [],
                        }
                      : null
                  }
                  sceneMenuOpen={sceneMenuOpen === currentScene.client_id}
                  onSceneMenuToggle={() =>
                    sbSet({
                      sceneMenuOpen:
                        sceneMenuOpen === currentScene.client_id ? null : currentScene.client_id,
                    })
                  }
                  onSceneMenuClose={() => sbSet({ sceneMenuOpen: null })}
                  validatingSceneId={validatingSceneId}
                  loraTriggerWords={loraTriggerWords}
                  tagsByGroup={tagsByGroup}
                  sceneTagGroups={sceneTagGroups}
                  isExclusiveGroup={isExclusiveGroup}
                  onUpdateScene={handleUpdateScene}
                  onPinToggle={handlePinToggle}
                  pinnedSceneOrder={pinnedSceneOrder}
                  onRemoveScene={() => handleRemoveScene(currentScene.client_id)}
                  onSpeakerChange={(speaker) => handleSpeakerChange(currentScene, speaker)}
                  onImageUpload={(file) => handleImageUpload(currentScene.client_id, file)}
                  onGenerateImage={() => handleGenerateImage(currentScene)}
                  onEditWithGemini={(target) => handleEditWithGemini(currentScene, target)}
                  onSuggestEditWithGemini={() => handleSuggestEditWithGemini(currentScene)}
                  onValidateImage={() => handleValidateImage(currentScene)}
                  onApplyMissingTags={(tags) => applyMissingImageTags(currentScene, tags)}
                  onImagePreview={(src, candidates) =>
                    useUIStore.getState().set({
                      imagePreviewSrc: src,
                      imagePreviewCandidates: candidates || null,
                    })
                  }
                  onSavePrompt={async () => {
                    const result = await confirm({
                      title: "Save Prompt",
                      message: "Enter a name for this prompt:",
                      confirmLabel: "Save",
                      inputField: { label: "Name", placeholder: "Enter prompt name..." },
                    });
                    if (result === false) return;
                    handleSavePrompt(currentScene, result as string);
                  }}
                  onMarkSuccess={() => handleMarkSuccess(currentScene)}
                  onMarkFail={() => handleMarkFail(currentScene)}
                  isMarkingStatus={markingStatusSceneId === currentScene.client_id}
                  selectedCharacterId={resolvedCharacterId}
                  basePromptA={resolvedBasePrompt}
                  characterLoras={resolvedCharacterLoras}
                  structure={useStoryboardStore.getState().structure}
                  characterAName={selectedCharacterName}
                  characterBName={selectedCharacterBName}
                  selectedCharacterBId={selectedCharacterBId}
                  genProgress={imageGenProgress[currentScene.client_id] ?? null}
                  buildNegativePrompt={buildNegativePrompt}
                  buildScenePrompt={buildScenePrompt}
                  showToast={showToast}
                />
              </div>
            </div>
          )}
        </main>
      </div>
      <ConfirmDialog {...dialogProps} />
    </>
  );
}
