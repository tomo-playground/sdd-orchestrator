"use client";

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useStudioStore } from "../../store/useStudioStore";
import { useCharacters } from "../../hooks/useCharacters";
import type { UseAutopilotReturn } from "../../hooks/useAutopilot";
import { API_BASE } from "../../constants";
import type { Scene, AutoRunStepId } from "../../types";
import StoryboardGeneratorPanel from "../storyboard/StoryboardGeneratorPanel";
import PromptSetupPanel from "../setup/PromptSetupPanel";
import StoryboardActionsBar from "../storyboard/StoryboardActionsBar";
import { runAutoRunFromStep } from "../../store/actions/autopilotActions";
import { saveStoryboard } from "../../store/actions/storyboardActions";

type PlanTabProps = {
  autopilot: UseAutopilotReturn;
};

export default function PlanTab({ autopilot }: PlanTabProps) {
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
  const referenceImages = useStudioStore((s) => s.referenceImages);

  const { characters, getCharacterFull, buildCharacterPrompt, buildCharacterNegative } = useCharacters();
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [baseTab, setBaseTab] = useState<"global" | "A">("A");
  const [planSubTab, setPlanSubTab] = useState<"generator" | "prompt">("prompt");

  // Load IP-Adapter reference images on mount
  useEffect(() => {
    axios
      .get(`${API_BASE}/controlnet/ip-adapter/references`)
      .then((res) => {
        useStudioStore.getState().setScenesState({
          referenceImages: res.data.references || [],
        });
      })
      .catch(() => { });
  }, []);

  // Auto-load character LoRA/prompt settings when character changes
  useEffect(() => {
    if (!selectedCharacterId) {
      setPlan({
        loraTriggerWords: [],
        characterLoras: [],
        characterPromptMode: "auto",
        basePromptA: "",
        baseNegativePromptA: "",
      });
      return;
    }
    getCharacterFull(selectedCharacterId).then((charFull) => {
      if (!charFull) return;

      // Load base prompts
      const basePrompt = buildCharacterPrompt(charFull);
      const baseNegative = buildCharacterNegative(charFull);
      console.log("[PlanTab] Loading character:", charFull.name);
      console.log("[PlanTab] Base prompt:", basePrompt);
      console.log("[PlanTab] Base negative:", baseNegative);

      // Load LoRAs
      const triggers = charFull.loras?.length
        ? charFull.loras.flatMap((l) => l.trigger_words || [])
        : [];
      const characterLoras = charFull.loras?.length
        ? charFull.loras.map((l) => ({
          id: l.id,
          name: l.name,
          weight: l.weight,
          trigger_words: l.trigger_words,
          lora_type: l.lora_type,
          optimal_weight: l.optimal_weight,
        }))
        : [];

      // Prompt mode
      const mode = charFull.prompt_mode
        || (charFull.effective_mode === "lora" ? "lora" : "standard");

      // Auto-set IP-Adapter reference if available
      console.log("[PlanTab] Available references:", referenceImages.length, referenceImages.map(r => `${r.character_key} (ID: ${r.character_id})`));
      console.log("[PlanTab] Looking for character ID:", charFull.id);
      const match = referenceImages.length > 0
        ? referenceImages.find((r) => r.character_id === charFull.id)
        : null;
      console.log("[PlanTab] Matched reference:", match ? `${match.character_key} (ID: ${match.character_id})` : "none");

      // Apply all settings in a single setPlan call
      setPlan({
        basePromptA: basePrompt,
        baseNegativePromptA: baseNegative,
        loraTriggerWords: triggers,
        characterLoras,
        characterPromptMode: mode || "auto",
        useIpAdapter: !!match,
        ipAdapterReference: match?.character_key || "",
        ipAdapterWeight: match?.preset?.weight
          ?? charFull.ip_adapter_weight
          ?? 0.75,
      });
    });
  }, [selectedCharacterId, referenceImages, getCharacterFull, buildCharacterPrompt, buildCharacterNegative, setPlan]);

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
        console.log("[PlanTab] Received scenes from backend:", data.scenes.length);
        console.log("[PlanTab] First scene negative_prompt:", data.scenes[0]?.negative_prompt);
        console.log("[PlanTab] Character negative_prompt (baseNegativePromptA):", baseNegativePromptA);

        // Combine scene negative + character negative
        const combinedNegative = [baseNegativePromptA, data.scenes[0]?.negative_prompt]
          .filter(Boolean)
          .join(", ")
          .trim();
        console.log("[PlanTab] Combined negative_prompt:", combinedNegative);

        const mapped: Scene[] = data.scenes.map((s: Record<string, unknown>, i: number) => {
          const sceneNegative = (s.negative_prompt as string) || "";
          const combined = [baseNegativePromptA, sceneNegative]
            .filter(Boolean)
            .join(", ")
            .trim();

          return {
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
            negative_prompt: combined,
            steps: baseStepsA,
            cfg_scale: baseCfgScaleA,
            sampler_name: baseSamplerA,
            seed: baseSeedA,
            clip_skip: baseClipSkipA,
            isGenerating: false,
            debug_payload: "",
          };
        });
        setScenes(mapped);
        setActiveTab("scenes");
        showToast(`Generated ${mapped.length} scenes`, "success");
      }
    } catch {
      showToast("Failed to generate storyboard", "error");
    } finally {
      setIsGenerating(false);
    }
  }, [topic, duration, style, language, structure, actorAGender, baseStepsA, baseCfgScaleA, baseSamplerA, baseSeedA, baseClipSkipA, baseNegativePromptA, setScenes, setActiveTab, showToast]);

  const handleSaveStoryboard = useCallback(async () => {
    setIsSaving(true);
    try {
      await saveStoryboard();
    } finally {
      setIsSaving(false);
    }
  }, []);

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
      {/* Sub Tabs */}
      <div className="flex items-center gap-1 border-b border-zinc-200/60">
        <button
          onClick={() => setPlanSubTab("prompt")}
          className={`px-4 py-2 text-sm font-medium transition-colors relative ${planSubTab === "prompt"
              ? "text-zinc-900"
              : "text-zinc-500 hover:text-zinc-700"
            }`}
        >
          <span className="flex items-center gap-2">
            <span>🎨</span>
            <span>캐릭터</span>
          </span>
          {planSubTab === "prompt" && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-zinc-900" />
          )}
        </button>
        <button
          onClick={() => setPlanSubTab("generator")}
          className={`px-4 py-2 text-sm font-medium transition-colors relative ${planSubTab === "generator"
              ? "text-zinc-900"
              : "text-zinc-500 hover:text-zinc-700"
            }`}
        >
          <span className="flex items-center gap-2">
            <span>🎬</span>
            <span>스토리</span>
          </span>
          {planSubTab === "generator" && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-zinc-900" />
          )}
        </button>
      </div>

      {/* Generator Tab Content */}
      {planSubTab === "generator" && (
        <>
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

          {/* Save Button */}
          {scenes.length > 0 && (
            <div className="mt-8 flex justify-end">
              <button
                onClick={handleSaveStoryboard}
                disabled={isSaving}
                className={`rounded-lg px-8 py-3 font-medium text-white shadow-md transition-all hover:-translate-y-0.5 hover:shadow-lg active:scale-95 ${isSaving
                  ? "cursor-not-allowed bg-zinc-400"
                  : "bg-zinc-900 hover:bg-zinc-800"
                  }`}
              >
                {isSaving ? "Saving..." : "Validate & Save Plan"}
              </button>
            </div>
          )}
        </>
      )}

      {/* Prompt Tab Content */}
      {planSubTab === "prompt" && (
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
      )}
    </div>
  );
}
