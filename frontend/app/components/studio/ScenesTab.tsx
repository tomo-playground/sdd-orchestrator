"use client";

import { useState } from "react";
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
} from "../../store/actions/sceneActions";
import { useSceneActions } from "../../hooks/useSceneActions";
import { useTTSPreview } from "../../hooks/useTTSPreview";
import { buildTtsRequest } from "../../utils/buildTtsRequest";
import { useTimeline } from "../../hooks/useTimeline";
import { useContextStore } from "../../store/useContextStore";
import TimelineBar from "./TimelineBar";
import DirectorControlPanel from "./DirectorControlPanel";
import axios from "axios";
import { API_BASE } from "../../constants";

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
    structure,
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
      structure: s.structure,
    }))
  );

  const reorderScenes = useStoryboardStore((s) => s.reorderScenes);
  const sbSet = useStoryboardStore((s) => s.set);
  const showToast = useUIStore((s) => s.showToast);
  const { tagsByGroup, sceneTagGroups, isExclusiveGroup } = useTags(null);

  const {
    setCurrentSceneIndex,
    handleUpdateScene,
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
  const setActiveTab = useUIStore((s) => s.setActiveTab);
  const showAdvancedSettings = useUIStore((s) => s.showAdvancedSettings);
  const toggleAdvancedSettings = useUIStore((s) => s.toggleAdvancedSettings);
  const currentStyleProfile = useRenderStore((s) => s.currentStyleProfile);
  const storyboardId = useContextStore((s) => s.storyboardId);
  const language = useStoryboardStore((s) => s.language);
  const ttsPreview = useTTSPreview(storyboardId);
  const speedMultiplier = useRenderStore((s) => s.speedMultiplier);
  const transitionType = useRenderStore((s) => s.transitionType);
  const { timeline } = useTimeline({
    scenes,
    ttsStates: ttsPreview.previewStates,
    speedMultiplier,
    transitionType,
  });

  const [isApplying, setIsApplying] = useState(false);

  const handleApplyAll = async () => {
    if (storyboardId == null) {
      showToast("스토리보드가 선택되지 않았습니다", "error");
      return;
    }
    setIsApplying(true);
    const ok = await confirm({
      title: "TTS 전체 재생성",
      message: `${scenes.length}씬의 TTS를 재생성합니다. 약 ${Math.ceil(scenes.length * 0.3)}분 소요됩니다.`,
      confirmLabel: "재생성",
    });
    if (!ok) {
      setIsApplying(false);
      return;
    }
    try {
      const res = await axios.post(`${API_BASE}/scene/tts-prebuild`, {
        storyboard_id: storyboardId,
        scenes: scenes.map((s) => buildTtsRequest(s, language, storyboardId)),
      });
      const results: Array<{ scene_db_id: number; tts_asset_id: number | null; status: string }> =
        res.data.results ?? [];
      const successCount = results.filter((r) => r.status === "prebuilt").length;
      const failCount = (res.data.failed as number) ?? 0;
      for (const r of results) {
        if (r.tts_asset_id && r.status === "prebuilt") {
          const scene = scenes.find((s) => s.id === r.scene_db_id);
          if (scene) {
            useStoryboardStore.getState().updateScene(scene.client_id, {
              tts_asset_id: r.tts_asset_id,
            });
          }
        }
      }
      if (failCount > 0) {
        showToast(`TTS 재생성: ${successCount}씬 성공, ${failCount}씬 실패`, "warning");
      } else {
        showToast(`${successCount}씬 TTS 재생성 완료`, "success");
      }
    } catch (err) {
      console.error("TTS prebuild failed:", err);
      showToast("TTS 재생성에 실패했습니다", "error");
    } finally {
      setIsApplying(false);
    }
  };

  if (scenes.length === 0) {
    return (
      <EmptyState
        icon={Film}
        title="씬이 없습니다"
        description="먼저 스크립트를 생성하세요"
        action={
          <Button onClick={() => setActiveTab("script")} size="lg">
            Script 탭으로 이동
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
            timeline={timeline}
          />
          <div className="border-t border-zinc-200 px-3 py-2">
            <TimelineBar
              scenes={scenes}
              ttsStates={ttsPreview.previewStates}
              speedMultiplier={speedMultiplier}
              timeline={timeline}
              activeSceneIndex={currentSceneIndex}
              onSceneClick={setCurrentSceneIndex}
            />
          </div>
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
              <span
                className="max-w-[140px] truncate rounded-full bg-violet-50 px-2 py-0.5 text-[11px] font-medium text-violet-700"
                title={currentStyleProfile.display_name ?? currentStyleProfile.name}
              >
                {currentStyleProfile.display_name ?? currentStyleProfile.name}
              </span>
            )}
            {selectedCharacterName && (
              <span
                className="max-w-[120px] truncate rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-700"
                title={`A: ${selectedCharacterName}`}
              >
                A: {selectedCharacterName}
              </span>
            )}
            {selectedCharacterBName && (
              <span
                className="max-w-[120px] truncate rounded-full bg-teal-50 px-2 py-0.5 text-[11px] font-medium text-teal-700"
                title={`B: ${selectedCharacterBName}`}
              >
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
                고급 설정
              </button>
              <button
                onClick={() => setActiveTab("stage")}
                className="text-[11px] font-medium text-zinc-400 transition hover:text-zinc-600"
              >
                Stage에서 편집 →
              </button>
            </div>
          </div>

          {/* Director Control Panel */}
          <div className="shrink-0 border-b border-zinc-100 px-8 py-3">
            <DirectorControlPanel onApplyAll={handleApplyAll} showToast={showToast} isApplying={isApplying} />
          </div>

          <SceneNavHeader
            currentIndex={currentSceneIndex}
            total={scenes.length}
            duration={currentScene?.duration}
            onPrev={() => setCurrentSceneIndex(Math.max(0, currentSceneIndex - 1))}
            onNext={() => setCurrentSceneIndex(Math.min(scenes.length - 1, currentSceneIndex + 1))}
            onRemove={currentScene ? () => handleRemoveScene(currentScene.client_id) : undefined}
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
                  onMarkSuccess={() => handleMarkSuccess(currentScene)}
                  onMarkFail={() => handleMarkFail(currentScene)}
                  isMarkingStatus={markingStatusSceneId === currentScene.client_id}
                  selectedCharacterId={resolvedCharacterId}
                  basePromptA={resolvedBasePrompt}
                  characterLoras={resolvedCharacterLoras}
                  structure={structure}
                  characterAName={selectedCharacterName}
                  characterBName={selectedCharacterBName}
                  selectedCharacterBId={selectedCharacterBId}
                  genProgress={imageGenProgress[currentScene.client_id] ?? null}
                  buildNegativePrompt={buildNegativePrompt}
                  buildScenePrompt={buildScenePrompt}
                  showToast={showToast}
                  ttsState={ttsPreview.previewStates.get(currentScene.client_id)}
                  onTTSPreview={() => ttsPreview.previewScene(currentScene)}
                  onTTSRegenerate={() => ttsPreview.regenerate(currentScene)}
                  audioPlayer={ttsPreview.audioPlayer}
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
