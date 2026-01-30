"use client";

import { useCallback, useEffect } from "react";
import axios from "axios";
import { useStudioStore } from "../../store/useStudioStore";
import { useTags } from "../../hooks";
import { API_BASE } from "../../constants";
import SceneFilmstrip from "../storyboard/SceneFilmstrip";
import SceneListHeader from "../storyboard/SceneListHeader";
import SceneCard from "../storyboard/SceneCard";
import {
  buildPositivePrompt,
  buildNegativePrompt,
  buildScenePrompt,
  getBasePromptForScene,
  getBaseSettingsForSpeaker,
} from "../../store/actions/promptActions";
import {
  handleGenerateImage,
  handleImageUpload,
  handleEditWithGemini,
  handleSuggestEditWithGemini,
} from "../../store/actions/imageActions";
import {
  runValidation,
  handleAutoFixAll,
  getSceneStatus,
  applySuggestion,
  applyMissingImageTags,
  handleSpeakerChange,
  handleValidateImage,
  handleMarkSuccess,
  handleMarkFail,
  handleSavePrompt,
} from "../../store/actions/sceneActions";
import { getFixSuggestions } from "../../utils";

export default function ScenesTab() {
  const {
    scenes,
    currentSceneIndex,
    setCurrentSceneIndex,
    updateScene,
    removeScene,
    validationResults,
    validationSummary,
    imageValidationResults,
    sceneTab,
    sceneMenuOpen,
    suggestionExpanded,
    validatingSceneId,
    markingStatusSceneId,
    multiGenEnabled,
    setScenesState,
  } = useStudioStore();

  const {
    autoComposePrompt,
    loraTriggerWords,
    characterLoras,
    characterPromptMode,
    useControlnet,
    controlnetWeight,
    useIpAdapter,
    ipAdapterReference,
    ipAdapterWeight,
    setPlan,
  } = useStudioStore();

  const referenceImages = useStudioStore((s) => s.referenceImages);
  const showToast = useStudioStore((s) => s.showToast);
  const { tagsByGroup, sceneTagGroups, isExclusiveGroup } = useTags(null);

  // Fetch IP-Adapter reference images on mount
  useEffect(() => {
    axios
      .get(`${API_BASE}/controlnet/ip-adapter/references`)
      .then((res) => {
        useStudioStore.getState().setScenesState({
          referenceImages: res.data.references || [],
        });
      })
      .catch(() => {});
  }, []);

  const currentScene = scenes[currentSceneIndex];

  const handleUpdateScene = useCallback(
    (updates: Partial<(typeof scenes)[0]>) => {
      if (currentScene) updateScene(currentScene.id, updates);
    },
    [currentScene, updateScene]
  );

  const handleRemoveScene = useCallback(
    (sceneId: number) => {
      if (confirm("Remove this scene?")) removeScene(sceneId);
    },
    [removeScene]
  );

  const handleAddScene = useCallback(() => {
    const bs = getBaseSettingsForSpeaker("Narrator");
    const newId = scenes.length > 0 ? Math.max(...scenes.map((s) => s.id)) + 1 : 0;
    const { baseNegativePromptA } = useStudioStore.getState();
    const newScene = {
      id: newId,
      script: "",
      speaker: "Narrator" as const,
      duration: 3,
      image_prompt: "",
      image_prompt_ko: "",
      image_url: null,
      width: 512,
      height: 768,
      negative_prompt: baseNegativePromptA,
      steps: bs.steps,
      cfg_scale: bs.cfg,
      sampler_name: bs.sampler,
      seed: bs.seed,
      clip_skip: bs.clipSkip,
      isGenerating: false,
      debug_payload: "",
    };
    useStudioStore.getState().setScenes([...scenes, newScene]);
    setCurrentSceneIndex(scenes.length);
  }, [scenes, setCurrentSceneIndex]);

  if (scenes.length === 0) {
    return (
      <div className="flex flex-col items-center gap-4 py-16 text-center">
        <p className="text-sm text-zinc-400">No scenes yet. Generate a storyboard first.</p>
        <button
          onClick={() => useStudioStore.getState().setActiveTab("plan")}
          className="rounded-full bg-zinc-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-zinc-800"
        >
          Go to Plan
        </button>
      </div>
    );
  }

  return (
    <section className="space-y-4">
      <SceneListHeader
        onValidate={runValidation}
        onAutoFixAll={handleAutoFixAll}
        onAddScene={handleAddScene}
        multiGenEnabled={multiGenEnabled}
        onMultiGenEnabledChange={(v) => setScenesState({ multiGenEnabled: v })}
        useControlnet={useControlnet}
        onUseControlnetChange={(v) => setPlan({ useControlnet: v })}
        controlnetWeight={controlnetWeight}
        onControlnetWeightChange={(v) => setPlan({ controlnetWeight: v })}
        useIpAdapter={useIpAdapter}
        onUseIpAdapterChange={(v) => setPlan({ useIpAdapter: v })}
        ipAdapterReference={ipAdapterReference}
        onIpAdapterReferenceChange={(v) => setPlan({ ipAdapterReference: v })}
        ipAdapterWeight={ipAdapterWeight}
        onIpAdapterWeightChange={(v) => setPlan({ ipAdapterWeight: v })}
        referenceImages={referenceImages}
        validationSummary={validationSummary}
        scenesCount={scenes.length}
      />

      <SceneFilmstrip
        scenes={scenes}
        currentSceneIndex={currentSceneIndex}
        onSceneSelect={setCurrentSceneIndex}
      />

      {currentScene && (
        <SceneCard
          key={currentScene.id}
          scene={currentScene}
          validationResult={validationResults[currentScene.id]}
          imageValidationResult={imageValidationResults[currentScene.id]}
          qualityScore={
            imageValidationResults[currentScene.id]
              ? {
                  match_rate: imageValidationResults[currentScene.id].match_rate ?? 0,
                  missing_tags: imageValidationResults[currentScene.id].missing ?? [],
                }
              : null
          }
          sceneTab={sceneTab[currentScene.id] ?? null}
          onSceneTabChange={(tab) =>
            setScenesState({
              sceneTab: { ...sceneTab, [currentScene.id]: tab },
            })
          }
          sceneMenuOpen={sceneMenuOpen === currentScene.id}
          onSceneMenuToggle={() =>
            setScenesState({
              sceneMenuOpen: sceneMenuOpen === currentScene.id ? null : currentScene.id,
            })
          }
          onSceneMenuClose={() => setScenesState({ sceneMenuOpen: null })}
          suggestionExpanded={suggestionExpanded[currentScene.id] ?? false}
          onSuggestionToggle={() =>
            setScenesState({
              suggestionExpanded: {
                ...suggestionExpanded,
                [currentScene.id]: !suggestionExpanded[currentScene.id],
              },
            })
          }
          validatingSceneId={validatingSceneId}
          autoComposePrompt={autoComposePrompt}
          loraTriggerWords={loraTriggerWords}
          characterLoras={characterLoras}
          promptMode={characterPromptMode}
          tagsByGroup={tagsByGroup}
          sceneTagGroups={sceneTagGroups}
          isExclusiveGroup={isExclusiveGroup}
          onUpdateScene={handleUpdateScene}
          onRemoveScene={() => handleRemoveScene(currentScene.id)}
          onSpeakerChange={(speaker) => handleSpeakerChange(currentScene, speaker)}
          onImageUpload={(file) => handleImageUpload(currentScene.id, file)}
          onGenerateImage={() => handleGenerateImage(currentScene)}
          onEditWithGemini={(target) => handleEditWithGemini(currentScene, target)}
          onSuggestEditWithGemini={() => handleSuggestEditWithGemini(currentScene)}
          onValidateImage={() => handleValidateImage(currentScene)}
          onApplyMissingTags={(tags) => applyMissingImageTags(currentScene, tags)}
          onImagePreview={(src) => useStudioStore.getState().setMeta({ imagePreviewSrc: src })}
          onSavePrompt={() => handleSavePrompt(currentScene)}
          onMarkSuccess={() => handleMarkSuccess(currentScene)}
          onMarkFail={() => handleMarkFail(currentScene)}
          isMarkingStatus={markingStatusSceneId === currentScene.id}
          getSceneStatus={getSceneStatus}
          getFixSuggestions={(scene, validation) =>
            getFixSuggestions(scene, validation, useStudioStore.getState().topic)
          }
          applySuggestion={applySuggestion}
          buildPositivePrompt={buildPositivePrompt}
          buildNegativePrompt={buildNegativePrompt}
          buildScenePrompt={buildScenePrompt}
          getBasePromptForScene={getBasePromptForScene}
          showToast={showToast}
        />
      )}
    </section>
  );
}
