"use client";

import Button from "../ui/Button";

import { useShallow } from "zustand/react/shallow";
import { Film } from "lucide-react";
import ConfirmDialog from "../ui/ConfirmDialog";
import EmptyState from "../ui/EmptyState";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useUIStore } from "../../store/useUIStore";
import { useTags } from "../../hooks";
import SceneListPanel from "../storyboard/SceneListPanel";
import RightPanelTabs from "./RightPanelTabs";
import ImageSettingsContent from "./ImageSettingsContent";
import SceneToolsContent from "./SceneToolsContent";
import SceneInsightsContent from "./SceneInsightsContent";
import SceneCard from "../storyboard/SceneCard";
import StudioThreeColumnLayout from "./StudioThreeColumnLayout";
import SceneNavHeader from "./SceneNavHeader";
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
      <StudioThreeColumnLayout
        leftPanel={
          <SceneListPanel
            scenes={scenes}
            currentSceneIndex={currentSceneIndex}
            onSceneSelect={setCurrentSceneIndex}
            onAddScene={handleAddScene}
            onRemoveScene={(idx) => handleRemoveScene(scenes[idx].client_id)}
            onReorderScene={reorderScenes}
            imageValidationResults={imageValidationResults}
          />
        }
        centerPanel={
          <>
            <SceneNavHeader
              currentIndex={currentSceneIndex}
              total={scenes.length}
              duration={currentScene?.duration}
              onPrev={() => setCurrentSceneIndex(Math.max(0, currentSceneIndex - 1))}
              onNext={() =>
                setCurrentSceneIndex(Math.min(scenes.length - 1, currentSceneIndex + 1))
              }
              onRemove={() => handleRemoveScene(currentScene.client_id)}
            />

            {currentScene && (
              <div className="flex-1 overflow-y-auto px-8 py-8">
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
          </>
        }
        rightPanel={
          <RightPanelTabs
            imageContent={<ImageSettingsContent />}
            toolsContent={<SceneToolsContent />}
            insightContent={
              <SceneInsightsContent
                imageValidationResults={imageValidationResults}
                scenes={scenes.map((s, i) => ({ id: s.id, client_id: s.client_id, order: i }))}
                onSceneSelect={setCurrentSceneIndex}
                fullScenes={scenes}
              />
            }
          />
        }
      />
      <ConfirmDialog {...dialogProps} />
    </>
  );
}
