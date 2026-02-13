"use client";

import { useState } from "react";
import { useShallow } from "zustand/react/shallow";
import ConfirmDialog from "../ui/ConfirmDialog";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useUIStore } from "../../store/useUIStore";
import { useTags } from "../../hooks";
import SceneListPanel from "../storyboard/SceneListPanel";
import RightPanelTabs from "./RightPanelTabs";
import ImageSettingsContent from "./ImageSettingsContent";
import SceneToolsContent from "./SceneToolsContent";
import SceneInsightsContent from "./SceneInsightsContent";
import SceneCard, { type SceneEditTab } from "../storyboard/SceneCard";
import { STUDIO_3COL_LAYOUT, CENTER_PANEL_CLASSES } from "../ui/variants";
import SceneNavHeader from "./SceneNavHeader";
import { buildNegativePrompt, buildScenePrompt } from "../../store/actions/promptActions";
import {
  resolveIpAdapterForSpeaker,
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
  runValidation,
  handleAutoFixAll,
  applySuggestion,
  applyMissingImageTags,
  handleSpeakerChange,
  handleValidateImage,
  handleMarkSuccess,
  handleMarkFail,
  handleSavePrompt,
} from "../../store/actions/sceneActions";
import { getFixSuggestions } from "../../utils";
import { useSceneActions } from "../../hooks/useSceneActions";

export default function ScenesTab() {
  const [sceneEditTab, setSceneEditTab] = useState<SceneEditTab>("script");

  const { scenes, currentSceneIndex } = useStoryboardStore(
    useShallow((s) => ({ scenes: s.scenes, currentSceneIndex: s.currentSceneIndex }))
  );

  const { validationResults, validationSummary, imageValidationResults } = useStoryboardStore(
    useShallow((s) => ({
      validationResults: s.validationResults,
      validationSummary: s.validationSummary,
      imageValidationResults: s.imageValidationResults,
    }))
  );

  const {
    sceneMenuOpen,
    suggestionExpanded,
    validatingSceneId,
    markingStatusSceneId,
    imageGenProgress,
  } = useStoryboardStore(
    useShallow((s) => ({
      sceneMenuOpen: s.sceneMenuOpen,
      suggestionExpanded: s.suggestionExpanded,
      validatingSceneId: s.validatingSceneId,
      markingStatusSceneId: s.markingStatusSceneId,
      imageGenProgress: s.imageGenProgress,
    }))
  );

  const {
    multiGenEnabled,
    loraTriggerWords,
    characterLoras,
    characterBLoras,
    characterPromptMode,
    selectedCharacterId,
    selectedCharacterBId,
    selectedCharacterName,
    selectedCharacterBName,
    basePromptA,
    basePromptB,
    useControlnet,
    controlnetWeight,
    useIpAdapter,
    ipAdapterReference,
    ipAdapterWeight,
    ipAdapterReferenceB,
    ipAdapterWeightB,
    referenceImages,
  } = useStoryboardStore(
    useShallow((s) => ({
      multiGenEnabled: s.multiGenEnabled,
      loraTriggerWords: s.loraTriggerWords,
      characterLoras: s.characterLoras,
      characterBLoras: s.characterBLoras,
      characterPromptMode: s.characterPromptMode,
      selectedCharacterId: s.selectedCharacterId,
      selectedCharacterBId: s.selectedCharacterBId,
      selectedCharacterName: s.selectedCharacterName,
      selectedCharacterBName: s.selectedCharacterBName,
      basePromptA: s.basePromptA,
      basePromptB: s.basePromptB,
      useControlnet: s.useControlnet,
      controlnetWeight: s.controlnetWeight,
      useIpAdapter: s.useIpAdapter,
      ipAdapterReference: s.ipAdapterReference,
      ipAdapterWeight: s.ipAdapterWeight,
      ipAdapterReferenceB: s.ipAdapterReferenceB,
      ipAdapterWeightB: s.ipAdapterWeightB,
      referenceImages: s.referenceImages,
    }))
  );

  const reorderScenes = useStoryboardStore((s) => s.reorderScenes);
  const sbSet = useStoryboardStore((s) => s.set);
  const showToast = useUIStore((s) => s.showToast);
  const { tagsByGroup, sceneTagGroups, isExclusiveGroup } = useTags(null);

  const {
    backgrounds,
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
  const resolvedIpAdapter = resolveIpAdapterForSpeaker(currentSpeaker, {
    ipAdapterReference,
    ipAdapterWeight,
    ipAdapterReferenceB,
    ipAdapterWeightB,
  });
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

  if (scenes.length === 0) {
    return (
      <div className="flex flex-col items-center gap-4 py-16 text-center">
        <p className="text-sm text-zinc-400">No scenes yet. Create a script first.</p>
        <a
          href="/scripts?new=true"
          className="rounded-full bg-zinc-900 px-8 py-3 text-sm font-semibold text-white shadow-md transition-all hover:-translate-y-0.5 hover:bg-zinc-800 hover:shadow-lg active:scale-95"
        >
          Go to Scripts
        </a>
      </div>
    );
  }

  return (
    <div className={STUDIO_3COL_LAYOUT}>
      {/* Left: Scene List */}
      <SceneListPanel
        scenes={scenes}
        currentSceneIndex={currentSceneIndex}
        onSceneSelect={setCurrentSceneIndex}
        onAddScene={handleAddScene}
        onRemoveScene={(idx) => handleRemoveScene(scenes[idx].client_id)}
        onReorderScene={reorderScenes}
        imageValidationResults={imageValidationResults}
      />

      {/* Center: Scene Editor */}
      <main className={CENTER_PANEL_CLASSES}>
        <SceneNavHeader
          currentIndex={currentSceneIndex}
          total={scenes.length}
          duration={currentScene?.duration}
          onPrev={() => setCurrentSceneIndex(Math.max(0, currentSceneIndex - 1))}
          onNext={() => setCurrentSceneIndex(Math.min(scenes.length - 1, currentSceneIndex + 1))}
          onRemove={() => handleRemoveScene(currentScene.client_id)}
        />

        {currentScene && (
          <div className="flex-1 overflow-y-auto px-6 py-4">
            <SceneCard
              key={currentScene.client_id}
              scene={currentScene}
              sceneIndex={currentSceneIndex}
              activeTab={sceneEditTab}
              onTabChange={setSceneEditTab}
              validationResult={validationResults[currentScene.client_id]}
              imageValidationResult={imageValidationResults[currentScene.client_id]}
              qualityScore={
                imageValidationResults[currentScene.client_id]
                  ? {
                      match_rate: imageValidationResults[currentScene.client_id].match_rate ?? 0,
                      missing_tags: imageValidationResults[currentScene.client_id].missing ?? [],
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
              suggestionExpanded={suggestionExpanded[currentScene.client_id] ?? false}
              onSuggestionToggle={() =>
                sbSet({
                  suggestionExpanded: {
                    ...suggestionExpanded,
                    [currentScene.client_id]: !suggestionExpanded[currentScene.client_id],
                  },
                })
              }
              validatingSceneId={validatingSceneId}
              loraTriggerWords={loraTriggerWords}
              promptMode={characterPromptMode}
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
              getFixSuggestions={(scene, validation) =>
                getFixSuggestions(scene, validation, useStoryboardStore.getState().topic)
              }
              applySuggestion={applySuggestion}
              selectedCharacterId={resolvedCharacterId}
              basePromptA={resolvedBasePrompt}
              characterLoras={resolvedCharacterLoras}
              structure={useStoryboardStore.getState().structure}
              characterAName={selectedCharacterName}
              characterBName={selectedCharacterBName}
              selectedCharacterBId={selectedCharacterBId}
              backgrounds={backgrounds}
              genProgress={imageGenProgress[currentScene.client_id] ?? null}
              buildNegativePrompt={buildNegativePrompt}
              buildScenePrompt={buildScenePrompt}
              showToast={showToast}
            />
          </div>
        )}
      </main>

      {/* Right: Tabbed Panel */}
      <RightPanelTabs
        imageContent={<ImageSettingsContent />}
        toolsContent={
          <SceneToolsContent
            multiGenEnabled={multiGenEnabled}
            useControlnet={useControlnet}
            controlnetWeight={controlnetWeight}
            onControlnetWeightChange={(v) => sbSet({ controlnetWeight: v })}
            useIpAdapter={useIpAdapter}
            ipAdapterReference={resolvedIpAdapter.reference}
            onIpAdapterReferenceChange={(v) =>
              sbSet(currentSpeaker === "B" ? { ipAdapterReferenceB: v } : { ipAdapterReference: v })
            }
            ipAdapterWeight={resolvedIpAdapter.weight}
            onIpAdapterWeightChange={(v) =>
              sbSet(currentSpeaker === "B" ? { ipAdapterWeightB: v } : { ipAdapterWeight: v })
            }
            referenceImages={referenceImages}
            sceneMultiGen={currentScene?.multi_gen_enabled}
            onSceneMultiGenChange={(v) => {
              if (currentScene)
                useStoryboardStore
                  .getState()
                  .updateScene(currentScene.client_id, { multi_gen_enabled: v });
            }}
            sceneControlnet={currentScene?.use_controlnet}
            onSceneControlnetChange={(v) => {
              if (currentScene)
                useStoryboardStore
                  .getState()
                  .updateScene(currentScene.client_id, { use_controlnet: v });
            }}
            sceneControlnetWeight={currentScene?.controlnet_weight}
            onSceneControlnetWeightChange={(v) => {
              if (currentScene)
                useStoryboardStore
                  .getState()
                  .updateScene(currentScene.client_id, { controlnet_weight: v });
            }}
            sceneIpAdapter={currentScene?.use_ip_adapter}
            onSceneIpAdapterChange={(v) => {
              if (currentScene)
                useStoryboardStore
                  .getState()
                  .updateScene(currentScene.client_id, { use_ip_adapter: v });
            }}
            sceneIpAdapterReference={currentScene?.ip_adapter_reference}
            onSceneIpAdapterReferenceChange={(v) => {
              if (currentScene)
                useStoryboardStore
                  .getState()
                  .updateScene(currentScene.client_id, { ip_adapter_reference: v });
            }}
            sceneIpAdapterWeight={currentScene?.ip_adapter_weight}
            onSceneIpAdapterWeightChange={(v) => {
              if (currentScene)
                useStoryboardStore
                  .getState()
                  .updateScene(currentScene.client_id, { ip_adapter_weight: v });
            }}
            currentSpeaker={currentSpeaker}
            validationSummary={validationSummary}
            onValidate={runValidation}
            onAutoFixAll={handleAutoFixAll}
            scenesCount={scenes.length}
          />
        }
        insightContent={
          <SceneInsightsContent
            imageValidationResults={imageValidationResults}
            scenes={scenes.map((s, i) => ({ id: s.id, client_id: s.client_id, order: i }))}
            onSceneSelect={setCurrentSceneIndex}
            fullScenes={scenes}
          />
        }
      />

      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
