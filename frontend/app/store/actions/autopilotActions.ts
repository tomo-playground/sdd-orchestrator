import axios from "axios";
import type { AutoRunStepId } from "../../types";
import type { UseAutopilotReturn } from "../../hooks/useAutopilot";
import { useStudioStore } from "../useStudioStore";
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
 * This orchestrates images → validate → render.
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
  const {
    layoutStyle,
    scenes: initialScenes,
    showToast,
    setScenes,
    setActiveTab,
  } = useStudioStore.getState();

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
  useStudioStore.getState().setMeta({ isAutoRunning: true });
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
        setActiveTab("scenes");
        assertNotCancelled();

        // Split scenes by per-scene multiGen setting
        const globalState = useStudioStore.getState();
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
            const sceneOrder = scene.order;
            // Fresh lookup: scene IDs may change between iterations (save → ID reassignment)
            const freshScene =
              useStudioStore.getState().scenes.find((s) => s.order === sceneOrder) || scene;
            useStudioStore.getState().updateScene(freshScene.id, { isGenerating: true });
            let result = await generateSceneCandidates(freshScene, true);
            if (!result?.image_url) {
              pushAutoRunLog(`Retry (Scene #${sceneOrder})`);
              const retryScene =
                useStudioStore.getState().scenes.find((s) => s.order === sceneOrder) || freshScene;
              result = await generateSceneCandidates(retryScene, true);
            }
            // Re-lookup after async: scene IDs may have changed
            const currentScene = useStudioStore
              .getState()
              .scenes.find((s) => s.order === sceneOrder);
            const currentId = currentScene?.id ?? freshScene.id;
            useStudioStore.getState().updateScene(currentId, { isGenerating: false });
            if (!result?.image_url) throw new Error(`Image failed for Scene #${sceneOrder}`);
            useStudioStore.getState().updateScene(currentId, result);
            workingScenes = useStudioStore.getState().scenes;
          }
        }

        // Single-gen scenes: batch mode with server-side throttling
        if (singleGenScenes.length > 0) {
          const sceneIds = singleGenScenes.map((s) => s.id);
          const batchResult = await generateBatchImages(sceneIds);

          // Check for scenes that need retry: either batch API failure OR
          // successful generation but failed image store (missing image_asset_id)
          const freshAfterBatch = useStudioStore.getState().scenes;
          const scenesNeedingRetry = singleGenScenes.filter((target) => {
            const fresh = freshAfterBatch.find((s) => s.order === target.order);
            // Retry if: no image_url, or has data URL (store failed), or no asset_id
            return !fresh?.image_url || !fresh?.image_asset_id;
          });

          const batchFailed = !batchResult || batchResult.failed > 0;
          if (batchFailed || scenesNeedingRetry.length > 0) {
            const reason = batchFailed
              ? `Batch: ${batchResult?.failed ?? sceneIds.length} scene(s) failed`
              : `${scenesNeedingRetry.length} scene(s) missing stored image`;
            pushAutoRunLog(`${reason}, retrying individually`);
            // Retry scenes that are missing images (use fresh store, not stale workingScenes)
            for (const target of scenesNeedingRetry) {
              assertNotCancelled();
              const sceneOrder = target.order;
              const freshScene =
                useStudioStore.getState().scenes.find((s) => s.order === sceneOrder) || target;
              useStudioStore.getState().updateScene(freshScene.id, { isGenerating: true });
              const result = await generateSceneImageFor(freshScene, true);
              // Re-lookup after async: scene IDs may have changed
              const currentScene = useStudioStore
                .getState()
                .scenes.find((s) => s.order === sceneOrder);
              const currentId = currentScene?.id ?? freshScene.id;
              useStudioStore.getState().updateScene(currentId, { isGenerating: false });
              if (!result?.image_url) throw new Error(`Image failed for Scene #${sceneOrder}`);
              useStudioStore.getState().updateScene(currentId, result);
            }
          }
          // Sync workingScenes with store state after batch
          workingScenes = useStudioStore.getState().scenes;
        }

        // Apply auto-pin for all scenes after image generation
        // Process in scene order so earlier scenes get pinned first
        const { updateScene } = useStudioStore.getState();
        const sortedScenes = [...workingScenes].sort((a, b) => a.order - b.order);
        let autoPinCount = 0;
        for (const scene of sortedScenes) {
          // Re-fetch scenes each iteration to get updated environment_reference_id
          const currentScenes = useStudioStore.getState().scenes;
          const result = applyAutoPinAfterGeneration(currentScenes, scene.id, updateScene);
          if (result?.success) {
            autoPinCount++;
            pushAutoRunLog(`AutoPin: Scene ${scene.order} - ${result.message}`);
          }
        }
        if (autoPinCount > 0) {
          pushAutoRunLog(`AutoPin applied to ${autoPinCount} scenes`);
        }

        // Sync workingScenes after auto-pin
        workingScenes = useStudioStore.getState().scenes;
        await persistStoryboard();
        // Re-sync after persistStoryboard: scene IDs may have changed
        workingScenes = useStudioStore.getState().scenes;
        pushAutoRunLog("Images generated");
      }

      if (currentStep === "validate") {
        setAutoRunStep("validate", "Validating images...");
        // Use fresh scenes from store (IDs may have changed after persistStoryboard)
        const { storyboardId, scenes: freshScenes } = useStudioStore.getState();
        workingScenes = freshScenes;
        for (const scene of workingScenes) {
          assertNotCancelled();
          if (!scene.image_url) continue;
          // Don't send data: (base64) in body — causes large request → Network Error. Use URL or skip.
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
          useStudioStore.getState().structure
        );
        useStudioStore.getState().setScenesState({
          validationResults: results,
          validationSummary: summary,
        });
        if (summary.error > 0) throw new Error(`Validation failed (${summary.error} errors)`);
        pushAutoRunLog("Validation complete");
      }

      if (currentStep === "render") {
        setAutoRunStep("render", `Rendering ${layoutStyle} video...`);
        setActiveTab("render");
        const { setOutput } = useStudioStore.getState();
        const renderProjectId = useStudioStore.getState().projectId;
        const renderGroupId = useStudioStore.getState().groupId;
        if (!renderProjectId || !renderGroupId) {
          throw new Error("Project/Group context required for render");
        }
        const project = getCurrentProject();
        const store = useStudioStore.getState();
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
          storyboard_id: store.storyboardId,
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
          pushAutoRunLog(`Rendering... ${p.percent}% (${p.stage_detail || p.stage})`);
        });
        const videoUrl = result.video_url;
        if (!videoUrl) throw new Error(`${layoutStyle} render failed`);
        const withTs = `${videoUrl}?t=${Date.now()}`;
        setOutput({
          videoUrl: withTs,
          ...(layoutStyle === "full" ? { videoUrlFull: withTs } : { videoUrlPost: withTs }),
          recentVideos: [
            {
              url: withTs,
              label: layoutStyle,
              createdAt: Date.now(),
              renderHistoryId: result.render_history_id,
            },
            ...useStudioStore.getState().recentVideos.slice(0, 9),
          ],
        });
        pushAutoRunLog(`${layoutStyle} render complete`);
      }
    }

    setAutoRunDone();
    showToast("Auto Run complete!", "success");
  } catch (err) {
    const message = err instanceof Error ? err.message : "Autopilot failed";
    setAutoRunError(currentStep, message);
    pushAutoRunLog(message);
    if (message !== "Autopilot cancelled") {
      showToast(`Autopilot stopped: ${message}`, "error");
    }
  } finally {
    useStudioStore.getState().setMeta({ isAutoRunning: false });
  }
}
