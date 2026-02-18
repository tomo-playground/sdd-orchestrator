import axios from "axios";
import type { AutoRunStepId } from "../../types";
import type { UseAutopilotReturn } from "../../hooks/useAutopilot";
import { useStoryboardStore } from "../useStoryboardStore";
import { useContextStore } from "../useContextStore";
import { useRenderStore } from "../useRenderStore";
import { useUIStore } from "../useUIStore";
import { API_BASE, AUTO_RUN_STEPS } from "../../constants";
import { computeValidationResults } from "../../utils";
import { generateBatchImages } from "./batchActions";
import { generateSceneImageFor, generateSceneCandidates } from "./imageActions";
import { resolveSceneMultiGen } from "../../utils/sceneSettingsResolver";
import { getCurrentProject } from "../selectors/projectSelectors";
import { persistStoryboard } from "./storyboardActions";
import { applyAutoPinAfterGeneration } from "../../utils/applyAutoPin";
import { renderWithProgress } from "../../utils/renderWithProgress";

/**
 * Run the autopilot pipeline from a given step.
 * This orchestrates images -> validate -> render.
 */
export async function runAutoRunFromStep(
  startStep: AutoRunStepId,
  autopilot: UseAutopilotReturn,
  stepsToRun?: AutoRunStepId[]
) {
  // Derive startStep from stepsToRun to prevent mismatch
  if (stepsToRun?.length) {
    startStep = stepsToRun[0];
  }

  const renderStore = useRenderStore.getState();
  const { layoutStyle } = renderStore;
  const sbState = useStoryboardStore.getState();
  const { scenes: initialScenes } = sbState;
  const { showToast, setActiveTab } = useUIStore.getState();

  const {
    startRun,
    setStep: setAutoRunStep,
    setDone: setAutoRunDone,
    setError: setAutoRunError,
    checkCancelled: assertNotCancelled,
    pushLog: pushAutoRunLog,
  } = autopilot;

  const allowedSteps = stepsToRun || AUTO_RUN_STEPS.map((s) => s.id as AutoRunStepId);

  if (!initialScenes.length) {
    showToast("Create a script first", "error");
    return;
  }

  startRun();
  useUIStore.getState().set({ isAutoRunning: true });
  let workingScenes = initialScenes;
  let currentStep: AutoRunStepId = startStep;

  try {
    const steps = AUTO_RUN_STEPS.map((s) => s.id);
    const startIndex = steps.indexOf(startStep);

    for (let idx = startIndex; idx < steps.length; idx += 1) {
      currentStep = steps[idx] as AutoRunStepId;
      assertNotCancelled();

      if (!allowedSteps.includes(currentStep)) {
        pushAutoRunLog(`Skipped: ${currentStep}`);
        continue;
      }

      if (currentStep === "images") {
        setAutoRunStep("images", "Generating scene images...");
        setActiveTab("edit");
        assertNotCancelled();

        // Track failed scenes to save progress before throwing
        const failedSceneOrders: number[] = [];

        // Split scenes by per-scene multiGen setting
        const globalState = useStoryboardStore.getState();
        const multiGenScenes = workingScenes.filter(
          (s) => !s.image_url && resolveSceneMultiGen(s, globalState)
        );
        const singleGenScenes = workingScenes.filter(
          (s) => !s.image_url && !resolveSceneMultiGen(s, globalState)
        );

        // Multi-gen scenes: sequential per scene (candidate ranking)
        if (multiGenScenes.length > 0) {
          for (const scene of multiGenScenes) {
            assertNotCancelled();
            // Fresh lookup by client_id (stable across save/ID reassignment)
            const freshScene =
              useStoryboardStore.getState().scenes.find((s) => s.client_id === scene.client_id) ||
              scene;
            useStoryboardStore.getState().updateScene(scene.client_id, { isGenerating: true });
            let result = await generateSceneCandidates(freshScene, true);
            if (!result?.image_url) {
              pushAutoRunLog(`Retry (Scene #${scene.order + 1})`);
              const retryScene =
                useStoryboardStore.getState().scenes.find((s) => s.client_id === scene.client_id) ||
                freshScene;
              result = await generateSceneCandidates(retryScene, true);
            }
            useStoryboardStore.getState().updateScene(scene.client_id, { isGenerating: false });
            if (!result?.image_url) {
              failedSceneOrders.push(scene.order);
              pushAutoRunLog(`Image failed for Scene #${scene.order + 1}`);
            } else {
              useStoryboardStore.getState().updateScene(scene.client_id, result);
            }
            workingScenes = useStoryboardStore.getState().scenes;
          }
        }

        // Single-gen scenes: batch mode with server-side throttling
        if (singleGenScenes.length > 0) {
          const sceneClientIds = singleGenScenes.map((s) => s.client_id);
          const batchResult = await generateBatchImages(sceneClientIds);

          // Check for scenes that need retry: either batch API failure OR
          // successful generation but failed image store (missing image_asset_id)
          const freshAfterBatch = useStoryboardStore.getState().scenes;
          const scenesNeedingRetry = singleGenScenes.filter((target) => {
            const fresh = freshAfterBatch.find((s) => s.client_id === target.client_id);
            // Retry if: no image_url, or has data URL (store failed), or no asset_id
            return !fresh?.image_url || !fresh?.image_asset_id;
          });

          const batchFailed = !batchResult || batchResult.failed > 0;
          if (batchFailed || scenesNeedingRetry.length > 0) {
            const reason = batchFailed
              ? `Batch: ${batchResult?.failed ?? sceneClientIds.length} scene(s) failed`
              : `${scenesNeedingRetry.length} scene(s) missing stored image`;
            pushAutoRunLog(`${reason}, retrying individually`);
            // Retry scenes that are missing images (use fresh store, not stale workingScenes)
            for (const target of scenesNeedingRetry) {
              assertNotCancelled();
              const freshScene =
                useStoryboardStore
                  .getState()
                  .scenes.find((s) => s.client_id === target.client_id) || target;
              useStoryboardStore.getState().updateScene(target.client_id, { isGenerating: true });
              const result = await generateSceneImageFor(freshScene, true);
              useStoryboardStore.getState().updateScene(target.client_id, { isGenerating: false });
              if (!result?.image_url) {
                failedSceneOrders.push(target.order);
                pushAutoRunLog(`Image failed for Scene #${target.order + 1}`);
              } else {
                useStoryboardStore.getState().updateScene(target.client_id, result);
              }
            }
          }
          // Sync workingScenes with store state after batch
          workingScenes = useStoryboardStore.getState().scenes;
        }

        // Apply auto-pin for all scenes after image generation
        // Process in scene order so earlier scenes get pinned first
        const { updateScene } = useStoryboardStore.getState();
        const sortedScenes = [...workingScenes].sort((a, b) => a.order - b.order);
        let autoPinCount = 0;
        for (const scene of sortedScenes) {
          // Re-fetch scenes each iteration to get updated environment_reference_id
          const currentScenes = useStoryboardStore.getState().scenes;
          const result = applyAutoPinAfterGeneration(currentScenes, scene.client_id, updateScene);
          if (result?.success) {
            autoPinCount++;
            pushAutoRunLog(`AutoPin: Scene ${scene.order + 1} - ${result.message}`);
          }
        }
        if (autoPinCount > 0) {
          pushAutoRunLog(`AutoPin applied to ${autoPinCount} scenes`);
        }

        // Sync workingScenes after auto-pin
        workingScenes = useStoryboardStore.getState().scenes;
        // Always save progress — even if some scenes failed
        await persistStoryboard();
        // Re-sync after persistStoryboard: scene IDs may have changed
        workingScenes = useStoryboardStore.getState().scenes;
        pushAutoRunLog("Images generated");

        // Throw after saving so successful images are preserved
        if (failedSceneOrders.length > 0) {
          throw new Error(
            `Image failed for Scene #${failedSceneOrders.map((o) => o + 1).join(", #")} (${workingScenes.length - failedSceneOrders.length} saved)`
          );
        }
      }

      if (currentStep === "validate") {
        setAutoRunStep("validate", "Validating images...");
        // Use fresh scenes from store (IDs may have changed after persistStoryboard)
        const { storyboardId } = useContextStore.getState();
        const freshScenes = useStoryboardStore.getState().scenes;
        workingScenes = freshScenes;
        for (const scene of workingScenes) {
          assertNotCancelled();
          if (!scene.image_url) continue;
          // Don't send data: (base64) in body -- causes large request -> Network Error. Use URL or skip.
          if (scene.image_url.startsWith("data:")) continue;
          try {
            const payload =
              scene.image_url.startsWith("http://") || scene.image_url.startsWith("https://")
                ? {
                  image_url: scene.image_url,
                  prompt: scene.debug_prompt || scene.image_prompt,
                  storyboard_id: storyboardId,
                  scene_id: scene.id,
                }
                : {
                  image_b64: scene.image_url,
                  prompt: scene.debug_prompt || scene.image_prompt,
                  storyboard_id: storyboardId,
                  scene_id: scene.id,
                };
            await axios.post(`${API_BASE}/scene/validate-and-auto-edit`, payload);
          } catch {
            // non-critical
          }
        }
        const { results, summary } = computeValidationResults(
          workingScenes,
          useStoryboardStore.getState().structure
        );
        useStoryboardStore.getState().set({
          validationResults: results,
          validationSummary: summary,
        });
        if (summary.error > 0) throw new Error(`Validation failed (${summary.error} errors)`);
        pushAutoRunLog("Validation complete");
      }

      if (currentStep === "render") {
        setAutoRunStep("render", `Rendering ${layoutStyle} video...`);
        setActiveTab("publish");
        const renderProjectId = useContextStore.getState().projectId;
        const renderGroupId = useContextStore.getState().groupId;
        if (!renderProjectId || !renderGroupId) {
          throw new Error("Project/Group context required for render");
        }
        const project = getCurrentProject();
        const store = useRenderStore.getState();
        const ctxStore = useContextStore.getState();
        const overlaySettings =
          layoutStyle === "full" && project
            ? {
              channel_name: project.name,
              avatar_key: project.avatar_key || project.handle || project.name,
              frame_style: store.frameStyle,
              caption: store.videoCaption,
              likes_count: store.videoLikesCount,
            }
            : null;
        const postCardSettings =
          layoutStyle === "post" && project
            ? {
              channel_name: project.name,
              avatar_key: project.avatar_key || project.handle || project.name,
              caption: store.videoCaption,
            }
            : null;

        const payload = {
          project_id: renderProjectId,
          group_id: renderGroupId,
          storyboard_id: ctxStore.storyboardId,
          scenes: workingScenes
            .filter((s) => s.image_url)
            .map((s) => ({
              image_url: s.image_url,
              script: s.script,
              speaker: s.speaker,
              duration: s.duration,
            })),
          layout_style: layoutStyle,
          ken_burns_preset: store.kenBurnsPreset,
          ken_burns_intensity: store.kenBurnsIntensity,
          transition_type: store.transitionType,
          speed_multiplier: store.speedMultiplier,
          bgm_file: store.bgmFile,
          audio_ducking: store.audioDucking,
          bgm_volume: store.bgmVolume,
          include_scene_text: store.includeSceneText,
          scene_text_font: store.sceneTextFont,
          tts_engine: "qwen",
          voice_design_prompt: store.voiceDesignPrompt || null,
          voice_preset_id: store.voicePresetId || null,
          overlay_settings: overlaySettings,
          post_card_settings: postCardSettings,
        };
        const result = await renderWithProgress(payload, (p) => {
          pushAutoRunLog(`Rendering... ${p.percent}% (${p.message || p.stage})`);
        });
        const videoUrl = result.video_url;
        if (!videoUrl) throw new Error(`${layoutStyle} render failed`);
        const withTs = `${videoUrl}?t=${Date.now()}`;
        const currentProject = getCurrentProject();
        const currentGroupId = renderGroupId;
        const currentGroup = ctxStore.groups.find((g) => g.id === currentGroupId);

        useRenderStore.getState().set({
          videoUrl: withTs,
          ...(layoutStyle === "full" ? { videoUrlFull: withTs } : { videoUrlPost: withTs }),
          recentVideos: [
            {
              url: withTs,
              label: layoutStyle,
              createdAt: Date.now(),
              renderHistoryId: result.render_history_id,
              projectId: renderProjectId,
              projectName: currentProject?.name,
              groupId: renderGroupId,
              groupName: currentGroup?.name,
            },
            ...useRenderStore.getState().recentVideos.slice(0, 9),
          ],
        });
        pushAutoRunLog(`${layoutStyle} render complete`);
      }
    }

    setAutoRunDone();
    setActiveTab("publish");
    showToast("Auto Run complete!", "success");
  } catch (err) {
    const message = err instanceof Error ? err.message : "Autopilot failed";
    setAutoRunError(currentStep, message);
    pushAutoRunLog(message);
    if (message !== "Autopilot cancelled") {
      showToast(`Autopilot stopped: ${message}`, "error");
    }
  } finally {
    useUIStore.getState().set({ isAutoRunning: false });
  }
}
