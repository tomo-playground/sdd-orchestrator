import axios from "axios";
import type { AutoRunStepId } from "../../types";
import type { UseAutopilotReturn } from "../../hooks/useAutopilot";
import { useStudioStore } from "../useStudioStore";
import { API_BASE, AUTO_RUN_STEPS } from "../../constants";
import { computeValidationResults } from "../../utils";
import { applyAutoFixForScenes } from "./sceneActions";
import { generateBatchImages } from "./batchActions";
import { generateSceneImageFor, generateSceneCandidates } from "./imageActions";
import { getCurrentProject } from "../selectors/projectSelectors";
import { initializeVideoMetadata } from "./outputActions";
import { mapGeminiScenes, persistStoryboard } from "./storyboardActions";
import { applyAutoPinAfterGeneration } from "../../utils/applyAutoPin";

/**
 * Run the autopilot pipeline from a given step.
 * This orchestrates storyboard → fix → images → validate → render.
 */
export async function runAutoRunFromStep(
  startStep: AutoRunStepId,
  autopilot: UseAutopilotReturn,
  stepsToRun?: AutoRunStepId[]
) {
  const {
    topic,
    duration,
    style,
    language,
    structure,
    actorAGender,
    baseNegativePromptA,
    layoutStyle,
    multiGenEnabled,
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

  if (allowedSteps.includes("storyboard") && !topic.trim()) {
    showToast("Enter a topic first", "error");
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

      if (currentStep === "storyboard") {
        setAutoRunStep("storyboard", "Generating storyboard...");
        pushAutoRunLog("Storyboard started");
        const structureLower = structure.toLowerCase();
        const hasCharacterB =
          structureLower === "dialogue" || structureLower === "narrated dialogue";
        const res = await axios.post(`${API_BASE}/storyboards/create`, {
          topic,
          duration,
          style,
          language,
          structure,
          actor_a_gender: actorAGender,
          description: useStudioStore.getState().description || undefined,
          character_id: useStudioStore.getState().selectedCharacterId || undefined,
          character_b_id: hasCharacterB
            ? useStudioStore.getState().selectedCharacterBId || undefined
            : undefined,
        });
        const incoming = Array.isArray(res.data.scenes) ? res.data.scenes : [];
        workingScenes = mapGeminiScenes(incoming, baseNegativePromptA);
        if (!workingScenes.length) throw new Error("Storyboard is empty");
        setScenes(workingScenes);
        await initializeVideoMetadata(topic);
        await persistStoryboard();
        workingScenes = useStudioStore.getState().scenes;
        pushAutoRunLog(`Storyboard created (${workingScenes.length} scenes)`);
      }

      if (currentStep === "fix") {
        setAutoRunStep("fix", "Auto-fixing scripts and prompts...");
        workingScenes = applyAutoFixForScenes(workingScenes);
        setScenes(workingScenes);
        pushAutoRunLog("Auto-fix applied");
      }

      if (currentStep === "images") {
        setAutoRunStep("images", "Generating scene images...");
        setActiveTab("scenes");
        assertNotCancelled();

        if (multiGenEnabled) {
          // Multi-gen mode: sequential per scene (candidate ranking)
          const { updateScene } = useStudioStore.getState();
          for (const scene of workingScenes) {
            assertNotCancelled();
            if (scene.image_url) continue;
            updateScene(scene.id, { isGenerating: true });
            let result = await generateSceneCandidates(scene, true);
            if (!result?.image_url) {
              pushAutoRunLog(`Retry (Scene ${scene.id})`);
              result = await generateSceneCandidates(scene, true);
            }
            updateScene(scene.id, { isGenerating: false });
            if (!result?.image_url) throw new Error(`Image failed for Scene ${scene.id}`);
            updateScene(scene.id, result);
            workingScenes = workingScenes.map((s) => (s.id === scene.id ? { ...s, ...result } : s));
          }
        } else {
          // Batch mode: concurrent generation with server-side throttling
          const sceneIds = workingScenes.filter((s) => !s.image_url).map((s) => s.id);
          if (sceneIds.length > 0) {
            const batchResult = await generateBatchImages(sceneIds);
            if (!batchResult || batchResult.failed > 0) {
              const failCount = batchResult?.failed ?? sceneIds.length;
              pushAutoRunLog(`Batch: ${failCount} scene(s) failed, retrying individually`);
              // Retry failed scenes individually
              const { updateScene } = useStudioStore.getState();
              for (const scene of workingScenes) {
                assertNotCancelled();
                if (scene.image_url) continue;
                updateScene(scene.id, { isGenerating: true });
                const result = await generateSceneImageFor(scene, true);
                updateScene(scene.id, { isGenerating: false });
                if (!result?.image_url) throw new Error(`Image failed for Scene ${scene.id}`);
                updateScene(scene.id, result);
                workingScenes = workingScenes.map((s) =>
                  s.id === scene.id ? { ...s, ...result } : s
                );
              }
            }
            // Sync workingScenes with store state after batch
            workingScenes = useStudioStore.getState().scenes;
          }
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
        pushAutoRunLog("Images generated");
      }

      if (currentStep === "validate") {
        setAutoRunStep("validate", "Validating images...");
        const { storyboardId } = useStudioStore.getState();
        for (const scene of workingScenes) {
          assertNotCancelled();
          if (!scene.image_url) continue;
          try {
            await axios.post(`${API_BASE}/scene/validate-and-auto-edit`, {
              image_b64: scene.image_url,
              prompt: scene.debug_prompt || scene.image_prompt,
              storyboard_id: storyboardId,
              scene_id: scene.id,
            });
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
        const res = await axios.post(`${API_BASE}/video/create`, payload);
        const videoUrl = res.data?.video_url;
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
              renderHistoryId: res.data.render_history_id,
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
