"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { useStudioStore } from "../../store/useStudioStore";
import { useCharacters } from "../../hooks/useCharacters";
import { API_BASE } from "../../constants";
import StoryboardGeneratorPanel from "../storyboard/StoryboardGeneratorPanel";
import PromptSetupPanel from "../setup/PromptSetupPanel";
import StyleProfileSelector from "../setup/StyleProfileSelector";
import { handleInlineStyleProfileSelect } from "../../store/actions/styleProfileActions";

export default function PlanTab() {
  const store = useStudioStore();
  const {
    topic,
    description,
    duration,
    language,
    structure,
    actorAGender,
    selectedCharacterId,
    basePromptA,
    baseNegativePromptA,
    autoComposePrompt,
    autoRewritePrompt,
    autoReplaceRiskyTags,
    hiResEnabled,
    veoEnabled,
    setPlan,
  } = store;

  const setMeta = useStudioStore((s) => s.setMeta);
  const referenceImages = useStudioStore((s) => s.referenceImages);
  const currentStyleProfile = useStudioStore((s) => s.currentStyleProfile);

  const { characters, getCharacterFull, buildCharacterPrompt, buildCharacterNegative } =
    useCharacters();
  const [planSubTab, setPlanSubTab] = useState<"actor" | "story">("actor");

  // Load IP-Adapter reference images on mount
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

      const basePrompt = buildCharacterPrompt(charFull);
      const baseNegative = buildCharacterNegative(charFull);
      console.log("[PlanTab] Loading character:", charFull.name);
      console.log("[PlanTab] Base prompt:", basePrompt);
      console.log("[PlanTab] Base negative:", baseNegative);

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

      const mode =
        charFull.prompt_mode || (charFull.effective_mode === "lora" ? "lora" : "standard");

      console.log(
        "[PlanTab] Available references:",
        referenceImages.length,
        referenceImages.map((r) => `${r.character_key} (ID: ${r.character_id})`)
      );
      console.log("[PlanTab] Looking for character ID:", charFull.id);
      const match =
        referenceImages.length > 0
          ? referenceImages.find((r) => r.character_id === charFull.id)
          : null;
      console.log(
        "[PlanTab] Matched reference:",
        match ? `${match.character_key} (ID: ${match.character_id})` : "none"
      );

      setPlan({
        basePromptA: basePrompt,
        baseNegativePromptA: baseNegative,
        loraTriggerWords: triggers,
        characterLoras,
        characterPromptMode: mode || "auto",
        useIpAdapter: !!match,
        ipAdapterReference: match?.character_key || "",
        ipAdapterWeight: match?.preset?.weight ?? charFull.ip_adapter_weight ?? 0.75,
      });
    });
  }, [
    selectedCharacterId,
    referenceImages,
    getCharacterFull,
    buildCharacterPrompt,
    buildCharacterNegative,
    setPlan,
  ]);

  const TOGGLES = [
    { key: "autoComposePrompt" as const, label: "Auto Compose", value: autoComposePrompt },
    { key: "autoRewritePrompt" as const, label: "Auto Rewrite", value: autoRewritePrompt },
    { key: "autoReplaceRiskyTags" as const, label: "Safe Tags", value: autoReplaceRiskyTags },
    { key: "hiResEnabled" as const, label: "Hi-Res", value: hiResEnabled },
    { key: "veoEnabled" as const, label: "Veo", value: veoEnabled },
  ];

  return (
    <div className="space-y-6">
      {/* Sub Tabs */}
      <div className="flex items-center gap-1 border-b border-zinc-200/60">
        {(["actor", "story"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setPlanSubTab(tab)}
            className={`relative px-4 py-2 text-sm font-medium transition-colors ${
              planSubTab === tab ? "text-zinc-900" : "text-zinc-500 hover:text-zinc-700"
            }`}
          >
            <span className="flex items-center gap-2">
              <span>{tab === "actor" ? "🎭" : "🎬"}</span>
              <span>{tab === "actor" ? "액터 설정" : "스토리 설정"}</span>
            </span>
            {planSubTab === tab && (
              <div className="absolute right-0 bottom-0 left-0 h-0.5 bg-zinc-900" />
            )}
          </button>
        ))}
      </div>

      {/* Actor Settings */}
      {planSubTab === "actor" && (
        <div className="space-y-6">
          <PromptSetupPanel
            actorAGender={actorAGender}
            setActorAGender={(v) => setPlan({ actorAGender: v })}
            basePromptA={basePromptA}
            setBasePromptA={(v: string) => setPlan({ basePromptA: v })}
            baseNegativePromptA={baseNegativePromptA}
            setBaseNegativePromptA={(v: string) => setPlan({ baseNegativePromptA: v })}
            onOpenPromptHelper={() => setMeta({ isHelperOpen: true })}
            characters={characters}
            selectedCharacterId={selectedCharacterId}
            onSelectCharacter={(id) => setPlan({ selectedCharacterId: id })}
          />
        </div>
      )}

      {/* Story Settings */}
      {planSubTab === "story" && (
        <div className="space-y-6">
          <StyleProfileSelector
            currentProfileId={currentStyleProfile?.id ?? null}
            currentProfileName={
              currentStyleProfile?.display_name ?? currentStyleProfile?.name ?? null
            }
            onSelect={handleInlineStyleProfileSelect}
          />
          <div className="flex flex-wrap gap-2">
            {TOGGLES.map((t) => (
              <label
                key={t.key}
                className={`flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                  t.value
                    ? "border-zinc-900 bg-zinc-900 text-white"
                    : "border-zinc-200 bg-white text-zinc-500 hover:border-zinc-300"
                }`}
              >
                <input
                  type="checkbox"
                  checked={t.value}
                  onChange={(e) => setPlan({ [t.key]: e.target.checked })}
                  className="sr-only"
                />
                {t.label}
              </label>
            ))}
          </div>
          <StoryboardGeneratorPanel
            topic={topic}
            setTopic={(v: string) => setPlan({ topic: v })}
            description={description}
            setDescription={(v: string) => setPlan({ description: v })}
            duration={duration}
            setDuration={(v: number) => setPlan({ duration: v })}
            language={language}
            setLanguage={(v: string) => setPlan({ language: v })}
            structure={structure}
            setStructure={(v: string) => setPlan({ structure: v })}
            characters={characters}
            selectedCharacterId={selectedCharacterId}
            onSelectCharacter={(id) => setPlan({ selectedCharacterId: id })}
          />
        </div>
      )}
    </div>
  );
}
