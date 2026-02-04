"use client";

import { useCallback, useEffect } from "react";
import axios from "axios";
import { useStudioStore } from "../../store/useStudioStore";
import { useTags } from "../../hooks";
import { API_BASE } from "../../constants";
import SceneFilmstrip from "../storyboard/SceneFilmstrip";
import SceneListHeader from "../storyboard/SceneListHeader";
import SceneSidePanel from "../storyboard/SceneSidePanel";
import SceneCard from "../storyboard/SceneCard";
import { SIDE_PANEL_LAYOUT } from "../ui/variants";
import { buildNegativePrompt, buildScenePrompt } from "../../store/actions/promptActions";
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
    selectedCharacterId,
    basePromptA,
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

  const handlePinToggle = useCallback(async () => {
    if (!currentScene) return;

    if (currentScene.environment_reference_id) {
      updateScene(currentScene.id, { environment_reference_id: null });
      return;
    }

    const currentIdx = scenes.findIndex((s) => s.id === currentScene.id);
    let referenceScene = null;

    for (let i = currentIdx - 1; i >= 0; i--) {
      if (scenes[i].image_asset_id) {
        referenceScene = scenes[i];
        break;
      }
    }

    if (!referenceScene) {
      showToast("이전 씬에 고정할 배경 이미지가 없습니다.", "error");
      return;
    }

    updateScene(currentScene.id, {
      environment_reference_id: referenceScene.image_asset_id,
      environment_reference_weight: 0.3,
    });
    showToast(`Scene ${referenceScene.order}의 배경을 참조로 설정했습니다.`, "success");
  }, [currentScene, scenes, updateScene, showToast]);

  const handleRemoveScene = useCallback(
    (sceneId: number) => {
      if (confirm("Remove this scene?")) removeScene(sceneId);
    },
    [removeScene]
  );

  const handleAddScene = useCallback(() => {
    const newId = scenes.length > 0 ? Math.max(...scenes.map((s) => s.id)) + 1 : 0;
    const { baseNegativePromptA } = useStudioStore.getState();
    const newScene = {
      id: newId,
      order: scenes.length,
      script: "",
      speaker: "Narrator" as const,
      duration: 3,
      image_prompt: "",
      image_prompt_ko: "",
      image_url: null,
      width: 512,
      height: 768,
      negative_prompt: baseNegativePromptA,
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
          className="rounded-full bg-zinc-900 px-8 py-3 text-sm font-semibold text-white shadow-md transition-all hover:-translate-y-0.5 hover:bg-zinc-800 hover:shadow-lg active:scale-95"
        >
          Go to Plan
        </button>
      </div>
    );
  }

  return (
    <div className={SIDE_PANEL_LAYOUT}>
      {/* Left: Scene Editor */}
      <section className="space-y-4">
        <SceneListHeader
          onValidate={runValidation}
          onAutoFixAll={handleAutoFixAll}
          onAddScene={handleAddScene}
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
            sceneIndex={currentSceneIndex}
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
            onPinToggle={handlePinToggle}
            onRemoveScene={() => handleRemoveScene(currentScene.id)}
            onSpeakerChange={(speaker) => handleSpeakerChange(currentScene, speaker)}
            onImageUpload={(file) => handleImageUpload(currentScene.id, file)}
            onGenerateImage={() => handleGenerateImage(currentScene)}
            onEditWithGemini={(target) => handleEditWithGemini(currentScene, target)}
            onSuggestEditWithGemini={() => handleSuggestEditWithGemini(currentScene)}
            onValidateImage={() => handleValidateImage(currentScene)}
            onApplyMissingTags={(tags) => applyMissingImageTags(currentScene, tags)}
            onImagePreview={(src, candidates) =>
              useStudioStore.getState().setMeta({
                imagePreviewSrc: src,
                imagePreviewCandidates: candidates || null,
              })
            }
            onSavePrompt={() => handleSavePrompt(currentScene)}
            onMarkSuccess={() => handleMarkSuccess(currentScene)}
            onMarkFail={() => handleMarkFail(currentScene)}
            isMarkingStatus={markingStatusSceneId === currentScene.id}
            getSceneStatus={getSceneStatus}
            getFixSuggestions={(scene, validation) =>
              getFixSuggestions(scene, validation, useStudioStore.getState().topic)
            }
            applySuggestion={applySuggestion}
            selectedCharacterId={selectedCharacterId}
            basePromptA={basePromptA}
            buildNegativePrompt={buildNegativePrompt}
            buildScenePrompt={buildScenePrompt}
            showToast={showToast}
          />
        )}
      </section>

      {/* Right: Settings & Status (sticky) */}
      <SceneSidePanel
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
        imageValidationResults={imageValidationResults}
        scenes={scenes.map((s, i) => ({ id: s.id, order: i }))}
        onSceneSelect={setCurrentSceneIndex}
      />
    </div>
  );
}
