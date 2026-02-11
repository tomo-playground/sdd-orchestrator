"use client";

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useUIStore } from "../../store/useUIStore";
import { useTags } from "../../hooks";
import { API_BASE } from "../../constants";
import type { Background } from "../../types";
import SceneFilmstrip from "../storyboard/SceneFilmstrip";
import SceneListHeader from "../storyboard/SceneListHeader";
import SceneSidePanel from "../storyboard/SceneSidePanel";
import SceneCard from "../storyboard/SceneCard";
import { SIDE_PANEL_LAYOUT } from "../ui/variants";
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
    autoComposePrompt,
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
  } = useStoryboardStore();

  const sbSet = useStoryboardStore((s) => s.set);
  const setScenes = useStoryboardStore((s) => s.setScenes);
  const showToast = useUIStore((s) => s.showToast);
  const { tagsByGroup, sceneTagGroups, isExclusiveGroup } = useTags(null);
  const [backgrounds, setBackgrounds] = useState<Background[]>([]);

  const setCurrentSceneIndex = useCallback(
    (idx: number) => sbSet({ currentSceneIndex: idx }),
    [sbSet]
  );

  // Fetch IP-Adapter reference images on mount
  useEffect(() => {
    axios
      .get(`${API_BASE}/controlnet/ip-adapter/references`)
      .then((res) => {
        useStoryboardStore.getState().set({
          referenceImages: res.data.references || [],
        });
      })
      .catch(() => {});
  }, []);

  // Fetch background assets on mount
  useEffect(() => {
    axios
      .get(`${API_BASE}/backgrounds`)
      .then((res) => setBackgrounds(res.data || []))
      .catch(() => {});
  }, []);

  const currentScene = scenes[currentSceneIndex];
  const currentSpeaker = currentScene?.speaker ?? "A";
  const resolvedIpAdapter = resolveIpAdapterForSpeaker(currentSpeaker, {
    ipAdapterReference,
    ipAdapterWeight,
    ipAdapterReferenceB,
    ipAdapterWeightB,
  });

  // Resolve character settings based on current speaker
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

  // Resolve pinned scene order for display (environment_reference_id -> scene order)
  const pinnedSceneOrder = currentScene?.environment_reference_id
    ? scenes.find((s) => s.image_asset_id === currentScene.environment_reference_id)?.order
    : undefined;

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
    const { baseNegativePromptA } = useStoryboardStore.getState();
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
    setScenes([...scenes, newScene]);
    setCurrentSceneIndex(scenes.length);
  }, [scenes, setCurrentSceneIndex, setScenes]);

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
    <div className={SIDE_PANEL_LAYOUT}>
      {/* Left: Scene Editor */}
      <section className="min-w-0 space-y-4">
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
              sbSet({
                sceneTab: { ...sceneTab, [currentScene.id]: tab },
              })
            }
            sceneMenuOpen={sceneMenuOpen === currentScene.id}
            onSceneMenuToggle={() =>
              sbSet({
                sceneMenuOpen: sceneMenuOpen === currentScene.id ? null : currentScene.id,
              })
            }
            onSceneMenuClose={() => sbSet({ sceneMenuOpen: null })}
            suggestionExpanded={suggestionExpanded[currentScene.id] ?? false}
            onSuggestionToggle={() =>
              sbSet({
                suggestionExpanded: {
                  ...suggestionExpanded,
                  [currentScene.id]: !suggestionExpanded[currentScene.id],
                },
              })
            }
            validatingSceneId={validatingSceneId}
            autoComposePrompt={autoComposePrompt}
            loraTriggerWords={loraTriggerWords}
            promptMode={characterPromptMode}
            tagsByGroup={tagsByGroup}
            sceneTagGroups={sceneTagGroups}
            isExclusiveGroup={isExclusiveGroup}
            onUpdateScene={handleUpdateScene}
            onPinToggle={handlePinToggle}
            pinnedSceneOrder={pinnedSceneOrder}
            onRemoveScene={() => handleRemoveScene(currentScene.id)}
            onSpeakerChange={(speaker) => handleSpeakerChange(currentScene, speaker)}
            onImageUpload={(file) => handleImageUpload(currentScene.id, file)}
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
            onSavePrompt={() => handleSavePrompt(currentScene)}
            onMarkSuccess={() => handleMarkSuccess(currentScene)}
            onMarkFail={() => handleMarkFail(currentScene)}
            isMarkingStatus={markingStatusSceneId === currentScene.id}
            getSceneStatus={getSceneStatus}
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
            buildNegativePrompt={buildNegativePrompt}
            buildScenePrompt={buildScenePrompt}
            showToast={showToast}
          />
        )}
      </section>

      {/* Right: Settings & Status (sticky) */}
      <SceneSidePanel
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
          if (currentScene) updateScene(currentScene.id, { multi_gen_enabled: v });
        }}
        sceneControlnet={currentScene?.use_controlnet}
        onSceneControlnetChange={(v) => {
          if (currentScene) updateScene(currentScene.id, { use_controlnet: v });
        }}
        sceneControlnetWeight={currentScene?.controlnet_weight}
        onSceneControlnetWeightChange={(v) => {
          if (currentScene) updateScene(currentScene.id, { controlnet_weight: v });
        }}
        sceneIpAdapter={currentScene?.use_ip_adapter}
        onSceneIpAdapterChange={(v) => {
          if (currentScene) updateScene(currentScene.id, { use_ip_adapter: v });
        }}
        sceneIpAdapterReference={currentScene?.ip_adapter_reference}
        onSceneIpAdapterReferenceChange={(v) => {
          if (currentScene) updateScene(currentScene.id, { ip_adapter_reference: v });
        }}
        sceneIpAdapterWeight={currentScene?.ip_adapter_weight}
        onSceneIpAdapterWeightChange={(v) => {
          if (currentScene) updateScene(currentScene.id, { ip_adapter_weight: v });
        }}
        currentSpeaker={currentSpeaker}
        validationSummary={validationSummary}
        imageValidationResults={imageValidationResults}
        scenes={scenes.map((s, i) => ({ id: s.id, order: i }))}
        onSceneSelect={setCurrentSceneIndex}
      />
    </div>
  );
}
