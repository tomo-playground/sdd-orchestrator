"use client";

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useStudioStore } from "../../store/useStudioStore";
import { useCharacters } from "../../hooks/useCharacters";
import { useAutopilot } from "../../hooks";
import { API_BASE } from "../../constants";
import type { Scene, AutoRunStepId } from "../../types";
import StoryboardGeneratorPanel from "../storyboard/StoryboardGeneratorPanel";
import PromptSetupPanel from "../setup/PromptSetupPanel";
import StoryboardActionsBar from "../storyboard/StoryboardActionsBar";
import AutoRunStatus from "../storyboard/AutoRunStatus";
import { runAutoRunFromStep } from "../../store/actions/autopilotActions";

export default function PlanTab() {
  const store = useStudioStore();
  const {
    topic, duration, style, language, structure, actorAGender,
    selectedCharacterId, basePromptA, baseNegativePromptA,
    autoComposePrompt, autoRewritePrompt, autoReplaceRiskyTags,
    baseStepsA, baseCfgScaleA, baseSamplerA, baseSeedA, baseClipSkipA,
    hiResEnabled, veoEnabled,
    setPlan,
  } = store;

  const scenes = useStudioStore((s) => s.scenes);
  const setScenes = useStudioStore((s) => s.setScenes);
  const setActiveTab = useStudioStore((s) => s.setActiveTab);
  const showToast = useStudioStore((s) => s.showToast);
  const setMeta = useStudioStore((s) => s.setMeta);
  const storyboardId = useStudioStore((s) => s.storyboardId);
  const isRendering = useStudioStore((s) => s.isRendering);

  const { characters, getCharacterFull } = useCharacters();
  const [isGenerating, setIsGenerating] = useState(false);
  const [baseTab, setBaseTab] = useState<"global" | "A">("A");

  // Autopilot
  const autopilot = useAutopilot();

  // Auto-load character LoRA/prompt settings when character changes
  useEffect(() => {
    if (!selectedCharacterId) {
      setPlan({ loraTriggerWords: [], characterLoras: [], characterPromptMode: "auto" });
      return;
    }
    getCharacterFull(selectedCharacterId).then((charFull) => {
      if (!charFull) return;
      if (charFull.loras?.length) {
        const triggers = charFull.loras.flatMap((l) => l.trigger_words || []);
        setPlan({
          loraTriggerWords: triggers,
          characterLoras: charFull.loras.map((l) => ({
            id: l.id,
            name: l.name,
            weight: l.weight,
            trigger_words: l.trigger_words,
            lora_type: l.lora_type,
            optimal_weight: l.optimal_weight,
          })),
        });
      } else {
        setPlan({ loraTriggerWords: [], characterLoras: [] });
      }
      // Prompt mode
      const mode = charFull.prompt_mode
        || (charFull.effective_mode === "lora" ? "lora" : "standard");
      setPlan({ characterPromptMode: mode || "auto" });

      // Auto-set IP-Adapter reference if available
      const refs = useStudioStore.getState().referenceImages;
      if (charFull.name && refs.length > 0) {
        const match = refs.find((r) => r.character_key === charFull.name);
        if (match) {
          setPlan({
            useIpAdapter: true,
            ipAdapterReference: match.character_key,
            ipAdapterWeight: match.preset?.weight
              ?? charFull.ip_adapter_weight
              ?? 0.75,
          });
        }
      }
    });
  }, [selectedCharacterId, getCharacterFull, setPlan]);

  const handleGenerateStoryboard = useCallback(async () => {
    if (!topic.trim()) {
      showToast("Enter a topic first", "error");
      return;
    }
    setIsGenerating(true);
    try {
      const res = await axios.post(`${API_BASE}/storyboards/create`, {
        topic,
        duration,
        style,
        language,
        structure,
        actor_a_gender: actorAGender,
      });
      const data = res.data;
      if (data.scenes) {
        const mapped: Scene[] = data.scenes.map((s: Record<string, unknown>, i: number) => ({
          id: i,
          script: (s.script as string) || "",
          speaker: (s.speaker as string) || "Narrator",
          duration: (s.duration as number) || 3,
          image_prompt: (s.image_prompt as string) || "",
          image_prompt_ko: (s.image_prompt_ko as string) || "",
          image_url: null,
          description: (s.description as string) || "",
          width: 512,
          height: 768,
          negative_prompt: "",
          steps: baseStepsA,
          cfg_scale: baseCfgScaleA,
          sampler_name: baseSamplerA,
          seed: baseSeedA,
          clip_skip: baseClipSkipA,
          isGenerating: false,
          debug_payload: "",
        }));
        setScenes(mapped);
        setActiveTab("scenes");
        showToast(`Generated ${mapped.length} scenes`, "success");
      }
    } catch {
      showToast("Failed to generate storyboard", "error");
    } finally {
      setIsGenerating(false);
    }
  }, [topic, duration, style, language, structure, actorAGender, baseStepsA, baseCfgScaleA, baseSamplerA, baseSeedA, baseClipSkipA, setScenes, setActiveTab, showToast]);

  const handleSaveStoryboard = useCallback(async () => {
    if (scenes.length === 0) {
      showToast("No scenes to save", "error");
      return;
    }
    try {
      const payload = {
        title: topic || "Untitled",
        description: topic,
        default_character_id: selectedCharacterId,
        scenes: scenes.map((s, i) => ({
          scene_id: i,
          script: s.script,
          speaker: s.speaker,
          duration: s.duration,
          image_prompt: s.image_prompt,
          image_prompt_ko: s.image_prompt_ko,
          image_url: s.image_url,
          description: s.description,
          width: s.width || 512,
          height: s.height || 768,
          negative_prompt: s.negative_prompt,
          steps: s.steps,
          cfg_scale: s.cfg_scale,
          sampler_name: s.sampler_name,
          seed: s.seed,
          clip_skip: s.clip_skip,
          context_tags: s.context_tags,
        })),
      };

      if (storyboardId) {
        await axios.put(`${API_BASE}/storyboards/${storyboardId}`, payload);
        showToast("Storyboard updated", "success");
      } else {
        const res = await axios.post(`${API_BASE}/storyboards`, payload);
        setMeta({ storyboardId: res.data.storyboard_id, storyboardTitle: topic });
        showToast("Storyboard saved", "success");
      }
    } catch {
      showToast("Failed to save storyboard", "error");
    }
  }, [scenes, topic, selectedCharacterId, storyboardId, showToast, setMeta]);

  const handleResetScenes = useCallback(() => {
    if (confirm("Reset all scenes?")) {
      setScenes([]);
    }
  }, [setScenes]);

  const handleResetDraft = useCallback(() => {
    if (confirm("Reset entire draft?")) {
      store.resetPlan();
      store.resetScenes();
      store.resetOutput();
      store.resetMeta();
    }
  }, [store]);

  return (
    <div className="space-y-6">
      {/* Generator Panel */}
      <StoryboardGeneratorPanel
        topic={topic}
        setTopic={(v: string) => setPlan({ topic: v })}
        duration={duration}
        setDuration={(v: number) => setPlan({ duration: v })}
        style={style}
        setStyle={(v: string) => setPlan({ style: v })}
        language={language}
        setLanguage={(v: string) => setPlan({ language: v })}
        structure={structure}
        setStructure={(v: string) => setPlan({ structure: v })}
      />

      {/* Prompt Setup */}
      <PromptSetupPanel
        baseTab={baseTab}
        setBaseTab={setBaseTab}
        autoComposePrompt={autoComposePrompt}
        setAutoComposePrompt={(v: boolean) => setPlan({ autoComposePrompt: v })}
        autoRewritePrompt={autoRewritePrompt}
        setAutoRewritePrompt={(v: boolean) => setPlan({ autoRewritePrompt: v })}
        autoReplaceRiskyTags={autoReplaceRiskyTags}
        setAutoReplaceRiskyTags={(v: boolean) => setPlan({ autoReplaceRiskyTags: v })}
        hiResEnabled={hiResEnabled}
        setHiResEnabled={(v: boolean) => setPlan({ hiResEnabled: v })}
        veoEnabled={veoEnabled}
        setVeoEnabled={(v: boolean) => setPlan({ veoEnabled: v })}
        actorAGender={actorAGender}
        setActorAGender={(v) => setPlan({ actorAGender: v })}
        basePromptA={basePromptA}
        setBasePromptA={(v: string) => setPlan({ basePromptA: v })}
        baseNegativePromptA={baseNegativePromptA}
        setBaseNegativePromptA={(v: string) => setPlan({ baseNegativePromptA: v })}
        baseStepsA={baseStepsA}
        setBaseStepsA={(v: number) => setPlan({ baseStepsA: v })}
        baseCfgScaleA={baseCfgScaleA}
        setBaseCfgScaleA={(v: number) => setPlan({ baseCfgScaleA: v })}
        baseSamplerA={baseSamplerA}
        setBaseSamplerA={(v: string) => setPlan({ baseSamplerA: v })}
        baseSeedA={baseSeedA}
        setBaseSeedA={(v: number) => setPlan({ baseSeedA: v })}
        baseClipSkipA={baseClipSkipA}
        setBaseClipSkipA={(v: number) => setPlan({ baseClipSkipA: v })}
        onOpenPromptHelper={() => setMeta({ isHelperOpen: true })}
        characters={characters}
        selectedCharacterId={selectedCharacterId}
        onSelectCharacter={(id) => setPlan({ selectedCharacterId: id })}
      />

      {/* Actions Bar */}
      <StoryboardActionsBar
        onResetScenes={handleResetScenes}
        onResetDraft={handleResetDraft}
        onGenerate={handleGenerateStoryboard}
        onAutoRun={() => runAutoRunFromStep("storyboard", autopilot)}
        isGenerating={isGenerating}
        isRendering={isRendering}
        isAutoRunning={autopilot.isAutoRunning}
        topicEmpty={!topic.trim()}
        autoRunStep={autopilot.autoRunState.step}
      />

      {/* Auto Run Status */}
      {autopilot.autoRunState.status !== "idle" && (
        <AutoRunStatus
          autoRunState={autopilot.autoRunState}
          autoRunLog={autopilot.autoRunLog}
          onResume={() => runAutoRunFromStep(autopilot.autoRunState.step as AutoRunStepId, autopilot)}
          onRestart={() => runAutoRunFromStep("storyboard", autopilot)}
        />
      )}

      {/* Save Button */}
      {scenes.length > 0 && (
        <div className="flex justify-end">
          <button
            onClick={handleSaveStoryboard}
            className="rounded-full bg-zinc-900 px-6 py-2 text-xs font-semibold text-white hover:bg-zinc-800 transition"
          >
            {storyboardId ? "Update Storyboard" : "Save to DB"}
          </button>
        </div>
      )}
    </div>
  );
}
