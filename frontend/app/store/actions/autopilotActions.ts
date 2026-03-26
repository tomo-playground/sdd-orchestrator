import type { AutoRunStepId, StageStatusResponse } from "../../types";
import { syncStageLocationsToStore } from "../../utils/syncStageLocations";
import type { UseAutopilotReturn } from "../../hooks/useAutopilot";
import axios from "axios";
import { useStoryboardStore } from "../useStoryboardStore";
import { useContextStore } from "../useContextStore";
import { useUIStore } from "../useUIStore";
import { useRenderStore } from "../useRenderStore";
import { AUTO_RUN_STEPS, API_BASE, API_TIMEOUT, AUTORUN_CONCURRENCY } from "../../constants";
import { generateSceneImageFor, generateSceneCandidates } from "./imageActions";
import { resolveSceneMultiGen } from "../../utils/sceneSettingsResolver";
import { buildTtsRequest } from "../../utils/buildTtsRequest";
import { persistStoryboard } from "./storyboardActions";
import { applyAutoPinAfterGeneration } from "../../utils/applyAutoPin";
import { executeRenderStep } from "./autopilotRenderStep";

/**
 * Run the autopilot pipeline from a given step.
 * This orchestrates images -> render.
 */
export async function runAutoRunFromStep(
  startStep: AutoRunStepId,
  autopilot: UseAutopilotReturn,
  stepsToRun?: AutoRunStepId[]
) {
  // M-5: Guard against duplicate execution
  if (useUIStore.getState().isAutoRunning) return;

  // Derive startStep from stepsToRun to prevent mismatch
  if (stepsToRun?.length) {
    startStep = stepsToRun[0];
  }

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
    cancel: cancelFn,
  } = autopilot;

  const allowedSteps = stepsToRun || AUTO_RUN_STEPS.map((s) => s.id as AutoRunStepId);

  if (!initialScenes.length) {
    showToast("먼저 스크립트를 생성하세요", "error");
    return;
  }

  // C-1: AbortController for cancelling in-flight HTTP requests on autopilot cancel
  const abortController = new AbortController();

  // Patch cancel to also abort in-flight requests immediately
  const originalCancel = cancelFn;
  autopilot.cancel = () => {
    originalCancel();
    abortController.abort();
  };

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

      if (currentStep === "stage") {
        const storyboardId = useContextStore.getState().storyboardId;
        if (!storyboardId) throw new Error("Storyboard ID required for Stage");

        // 0) DB 싱크 보장 — 새 씬이 DB에 저장된 후 배경 생성
        setAutoRunStep("stage", "씬 데이터 저장 중...");
        const saved = await persistStoryboard();
        if (!saved) throw new Error("스토리보드 저장 실패 — Stage를 시작할 수 없습니다.");
        assertNotCancelled();

        setAutoRunStep("stage", "Generating backgrounds...");
        useStoryboardStore.getState().set({ stageStatus: "staging" });
        assertNotCancelled();

        // 1) Generate backgrounds
        const bgRes = await axios.post(
          `${API_BASE}/storyboards/${storyboardId}/stage/generate-backgrounds`,
          null,
          { timeout: API_TIMEOUT.STAGE_GENERATE, signal: abortController.signal }
        );
        const bgResults = bgRes.data.results ?? [];
        const bgSuccess = bgResults.filter((r: { status: string }) => r.status !== "failed").length;
        if (bgSuccess === 0 && bgResults.length > 0) {
          throw new Error("배경 이미지 생성에 실패했습니다. SD WebUI 상태를 확인해주세요.");
        }
        pushAutoRunLog(`Backgrounds generated (${bgSuccess}/${bgResults.length})`);
        assertNotCancelled();

        // 2) Assign to scenes
        setAutoRunStep("stage", "Assigning backgrounds to scenes...");
        const assignRes = await axios.post(
          `${API_BASE}/storyboards/${storyboardId}/stage/assign-backgrounds`,
          null,
          { timeout: API_TIMEOUT.DEFAULT, signal: abortController.signal }
        );
        const assignments = assignRes.data.assignments ?? [];
        if (assignments.length > 0) {
          const { scenes, setScenes } = useStoryboardStore.getState();
          const assignMap = new Map<number, number>(
            assignments.map(
              (a: { scene_id: number; background_id: number }) =>
                [a.scene_id, a.background_id] as [number, number]
            )
          );
          const updated = scenes.map((s) => {
            const bgId = assignMap.get(s.id);
            if (bgId != null) {
              return { ...s, background_id: bgId, environment_reference_id: null };
            }
            return s;
          });
          setScenes(updated);
          pushAutoRunLog(`${assignments.length} scenes assigned to backgrounds`);
          // A-2: warn about scenes with env tags that still have no background assigned
          const currentScenesAfterAssign = useStoryboardStore.getState().scenes;
          const unassignedWithEnv = currentScenesAfterAssign.filter(
            (s) =>
              !s.background_id &&
              Array.isArray((s.context_tags as Record<string, unknown>)?.environment) &&
              ((s.context_tags as Record<string, unknown>)?.environment as unknown[]).length > 0
          );
          if (unassignedWithEnv.length > 0) {
            pushAutoRunLog(
              `Warning: ${unassignedWithEnv.length} scene(s) with environment tags have no background assigned`
            );
          }
        }

        // 3) Save & sync — stageLocations refetch 포함
        useStoryboardStore.getState().set({ stageStatus: "staged" });
        // H-2: Check persistStoryboard return value
        const stageSaved = await persistStoryboard();
        if (!stageSaved) throw new Error("Failed to save storyboard after stage");
        workingScenes = useStoryboardStore.getState().scenes;

        // Stage locations를 store에 동기화 (Stage 탭 미활성 시에도 배경 표시)
        try {
          const stageRes = await axios.get<StageStatusResponse>(
            `${API_BASE}/storyboards/${storyboardId}/stage/status`,
            { timeout: API_TIMEOUT.DEFAULT, signal: abortController.signal }
          );
          syncStageLocationsToStore(stageRes.data.locations ?? []);
        } catch {
          pushAutoRunLog("Stage locations sync skipped (will refetch on tab mount)");
        }

        // 4) BGM prebuild (auto 모드 only, non-blocking)
        const { bgmMode, bgmPrompt } = useRenderStore.getState();
        if (bgmMode === "auto" && bgmPrompt) {
          setAutoRunStep("stage", "Generating BGM...");
          try {
            const totalDur = workingScenes.reduce((sum, s) => sum + (s.duration || 3), 0);
            await axios.post(
              `${API_BASE}/storyboards/${storyboardId}/stage/bgm-prebuild`,
              { bgm_prompt: bgmPrompt, total_duration: totalDur },
              { timeout: API_TIMEOUT.VIDEO_RENDER, signal: abortController.signal }
            );
            pushAutoRunLog("BGM prebuilt");
          } catch {
            pushAutoRunLog("BGM prebuild skipped (will generate during render)");
          }
        }
        pushAutoRunLog("Stage complete");
      }

      if (currentStep === "images") {
        setAutoRunStep("images", "Generating scene images...");
        assertNotCancelled();

        // Guard: Stage를 실행했어야 하는데 배경이 없으면 차단
        if (allowedSteps.includes("stage")) {
          const currentScenes = useStoryboardStore.getState().scenes;
          const missingBg = currentScenes.filter(
            (s) =>
              !s.background_id &&
              Array.isArray((s.context_tags as Record<string, unknown>)?.environment) &&
              ((s.context_tags as Record<string, unknown>)?.environment as unknown[]).length > 0
          );
          if (missingBg.length > 0) {
            throw new Error(
              `배경이 생성되지 않은 씬이 ${missingBg.length}개 있습니다. Stage 단계를 먼저 완료해주세요.`
            );
          }
        }

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

        // Single-gen scenes: individual SSE with concurrency limit
        if (singleGenScenes.length > 0) {
          const queue = [...singleGenScenes];
          const running = new Set<Promise<void>>();

          while (queue.length > 0 || running.size > 0) {
            if (abortController.signal.aborted) {
              // Wait for in-flight tasks so their results land in store before persistStoryboard
              if (running.size > 0) await Promise.allSettled([...running]);
              break;
            }

            while (running.size < AUTORUN_CONCURRENCY && queue.length > 0) {
              const target = queue.shift()!;
              const p = (async () => {
                try {
                  const freshScene =
                    useStoryboardStore
                      .getState()
                      .scenes.find((s) => s.client_id === target.client_id) || target;
                  useStoryboardStore
                    .getState()
                    .updateScene(target.client_id, { isGenerating: true });
                  try {
                    const result = await generateSceneImageFor(freshScene, true);
                    if (!result?.image_url) {
                      failedSceneOrders.push(target.order);
                      pushAutoRunLog(`Image failed for Scene #${target.order + 1}`);
                    } else {
                      useStoryboardStore.getState().updateScene(target.client_id, result);
                    }
                  } finally {
                    useStoryboardStore
                      .getState()
                      .updateScene(target.client_id, { isGenerating: false });
                  }
                } catch {
                  failedSceneOrders.push(target.order);
                  pushAutoRunLog(`Image failed for Scene #${target.order + 1}`);
                }
              })();
              running.add(p);
              p.finally(() => running.delete(p));
            }

            if (running.size > 0) {
              await Promise.race(running);
            }
          }
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
        // H-2: Always save progress — even if some scenes failed
        const imgSaved = await persistStoryboard();
        if (!imgSaved) throw new Error("Failed to save storyboard after image generation");
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

      if (currentStep === "tts") {
        setAutoRunStep("tts", "Pre-building TTS audio...");
        const storyboardId = useContextStore.getState().storyboardId;
        if (!storyboardId) throw new Error("Storyboard ID required for TTS prebuild");
        const language = useStoryboardStore.getState().language;

        const ttsScenes = workingScenes
          .filter((s) => s.script?.trim())
          .map((s) => ({
            ...buildTtsRequest(s, language, storyboardId),
            tts_asset_id: s.tts_asset_id ?? undefined,
          }));

        if (ttsScenes.length > 0) {
          const res = await axios.post(
            `${API_BASE}/scene/tts-prebuild`,
            {
              storyboard_id: storyboardId,
              scenes: ttsScenes,
              tts_engine: useRenderStore.getState().ttsEngine,
            },
            { timeout: API_TIMEOUT.VIDEO_RENDER, signal: abortController.signal }
          );
          const { prebuilt, skipped, failed } = res.data;
          pushAutoRunLog(`TTS: ${prebuilt} prebuilt, ${skipped} skipped, ${failed} failed`);

          // Update store with new tts_asset_ids
          const results: Array<{
            scene_db_id: number;
            tts_asset_id: number | null;
            status: string;
          }> = res.data.results ?? [];
          for (const r of results) {
            if (r.tts_asset_id && r.status === "prebuilt") {
              const scene = workingScenes.find((s) => s.id === r.scene_db_id);
              if (scene) {
                useStoryboardStore
                  .getState()
                  .updateScene(scene.client_id, { tts_asset_id: r.tts_asset_id });
              }
            }
          }
          workingScenes = useStoryboardStore.getState().scenes;
        }
        pushAutoRunLog("TTS prebuild complete");
      }

      if (currentStep === "render") {
        await executeRenderStep(workingScenes, abortController.signal, {
          setAutoRunStep,
          setActiveTab,
          pushAutoRunLog,
        });
      }
    }

    setAutoRunDone();
    setActiveTab("publish");
    showToast("Auto Run 완료!", "success");
  } catch (err) {
    // C-1: Abort any in-flight render SSE on error/cancel
    abortController.abort();
    // H-1: Restore stageStatus on failure
    const sbNow = useStoryboardStore.getState();
    if (sbNow.stageStatus === "staging") {
      useStoryboardStore.getState().set({ stageStatus: "failed" });
    }
    const isAborted = axios.isCancel(err) || (err instanceof Error && err.name === "AbortError");
    const message = isAborted
      ? "Autopilot cancelled"
      : err instanceof Error
        ? err.message
        : "Autopilot failed";
    setAutoRunError(currentStep, message);
    pushAutoRunLog(message);
    if (message !== "Autopilot cancelled") {
      showToast(`Auto Run 중단: ${message}`, "error");
    }
  } finally {
    autopilot.cancel = originalCancel;
    useUIStore.getState().set({ isAutoRunning: false });
  }
}
