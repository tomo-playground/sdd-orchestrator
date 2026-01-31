import axios from "axios";
import type { Scene, AutoRunStepId } from "../../types";
import type { UseAutopilotReturn } from "../../hooks/useAutopilot";
import { useStudioStore } from "../useStudioStore";
import { API_BASE, AUTO_RUN_STEPS } from "../../constants";
import { computeValidationResults } from "../../utils";
import { applyAutoFixForScenes } from "./sceneActions";
import { generateSceneImageFor, generateSceneCandidates } from "./imageActions";

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
    topic, duration, style, language, structure, actorAGender,
    baseNegativePromptA, baseStepsA, baseCfgScaleA, baseSamplerA, baseSeedA, baseClipSkipA,
    layoutStyle, multiGenEnabled,
    scenes: initialScenes,
    showToast, setScenes, setActiveTab,
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
        const res = await axios.post(`${API_BASE}/storyboards/create`, {
          topic, duration, style, language, structure,
          actor_a_gender: actorAGender,
        });
        const incoming = Array.isArray(res.data.scenes) ? res.data.scenes : [];
        workingScenes = incoming.map((s: Record<string, unknown>, i: number) => ({
          id: i,
          script: (s.script as string) || "",
          speaker: (s.speaker as string) || "Narrator",
          duration: (s.duration as number) || 3,
          image_prompt: (s.image_prompt as string) || "",
          image_prompt_ko: (s.image_prompt_ko as string) || "",
          image_url: null,
          negative_prompt: baseNegativePromptA,
          steps: baseStepsA,
          cfg_scale: baseCfgScaleA,
          sampler_name: baseSamplerA,
          seed: baseSeedA,
          clip_skip: baseClipSkipA,
          isGenerating: false,
          debug_payload: "",
        }));
        if (!workingScenes.length) throw new Error("Storyboard is empty");
        setScenes(workingScenes);
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
        const { updateScene } = useStudioStore.getState();
        for (const scene of workingScenes) {
          assertNotCancelled();
          if (scene.image_url) continue;
          updateScene(scene.id, { isGenerating: true });
          let result = multiGenEnabled
            ? await generateSceneCandidates(scene, true)
            : await generateSceneImageFor(scene, true);
          if (!result?.image_url) {
            pushAutoRunLog(`Retry (Scene ${scene.id})`);
            result = multiGenEnabled
              ? await generateSceneCandidates(scene, true)
              : await generateSceneImageFor(scene, true);
          }
          updateScene(scene.id, { isGenerating: false });
          if (!result?.image_url) throw new Error(`Image failed for Scene ${scene.id}`);
          updateScene(scene.id, result);
          workingScenes = workingScenes.map((s) =>
            s.id === scene.id ? { ...s, ...result } : s
          );
        }
        pushAutoRunLog("Images generated");
      }

      if (currentStep === "validate") {
        setAutoRunStep("validate", "Validating images...");
        const { storyboardId } = useStudioStore.getState();
        for (const scene of workingScenes) {
          assertNotCancelled();
          if (!scene.image_url) continue;
          try {
            await axios.post(`${API_BASE}/scene/validate_image`, {
              image_b64: scene.image_url,
              prompt: scene.debug_prompt || scene.image_prompt,
              storyboard_id: storyboardId,
              scene_id: scene.id,
            });
          } catch {
            // non-critical
          }
        }
        const { results, summary } = computeValidationResults(workingScenes);
        useStudioStore.getState().setScenesState({
          validationResults: results,
          validationSummary: summary,
        });
        if (summary.error > 0) throw new Error(`Validation failed (${summary.error} errors)`);
        pushAutoRunLog("Validation complete");
      }

      if (currentStep === "render") {
        setAutoRunStep("render", `Rendering ${layoutStyle} video...`);
        setActiveTab("output");
        const { setOutput } = useStudioStore.getState();
        const payload = {
          scenes: workingScenes.filter((s) => s.image_url).map((s) => ({
            image_url: s.image_url,
            script: s.script,
            speaker: s.speaker,
            duration: s.duration,
          })),
          layout_style: layoutStyle,
          ken_burns_preset: useStudioStore.getState().kenBurnsPreset,
          ken_burns_intensity: useStudioStore.getState().kenBurnsIntensity,
          transition_type: useStudioStore.getState().transitionType,
          narrator_voice: useStudioStore.getState().narratorVoice,
          speed_multiplier: useStudioStore.getState().speedMultiplier,
          bgm_file: useStudioStore.getState().bgmFile,
          audio_ducking: useStudioStore.getState().audioDucking,
          bgm_volume: useStudioStore.getState().bgmVolume,
          include_scene_text: useStudioStore.getState().includeSceneText,
          subtitle_font: useStudioStore.getState().subtitleFont,
        };
        const res = await axios.post(`${API_BASE}/video/create`, payload);
        const videoUrl = res.data?.video_url;
        if (!videoUrl) throw new Error(`${layoutStyle} render failed`);
        const withTs = `${videoUrl}?t=${Date.now()}`;
        setOutput({
          videoUrl: withTs,
          ...(layoutStyle === "full"
            ? { videoUrlFull: withTs }
            : { videoUrlPost: withTs }),
          recentVideos: [
            { url: withTs, label: layoutStyle, createdAt: Date.now() },
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
  }
}
