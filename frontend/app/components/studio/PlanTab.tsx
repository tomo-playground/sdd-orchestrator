"use client";

import { useEffect } from "react";
import axios from "axios";
import { useStudioStore } from "../../store/useStudioStore";
import { useCharacters } from "../../hooks/useCharacters";
import { API_BASE } from "../../constants";
import StoryboardGeneratorPanel from "../storyboard/StoryboardGeneratorPanel";
import PromptSetupPanel from "../setup/PromptSetupPanel";
import StyleProfileSelector from "../setup/StyleProfileSelector";
import { handleInlineStyleProfileSelect } from "../../store/actions/styleProfileActions";
import { SIDE_PANEL_LAYOUT, SIDE_PANEL_CLASSES } from "../ui/variants";

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
    selectedCharacterBId,
    basePromptA,
    baseNegativePromptA,
    basePromptB,
    baseNegativePromptB,
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

  // Auto-load character B data when selectedCharacterBId changes
  useEffect(() => {
    if (!selectedCharacterBId) {
      setPlan({
        characterBLoras: [],
        basePromptB: "",
        baseNegativePromptB: "",
      });
      return;
    }
    getCharacterFull(selectedCharacterBId).then((charFull) => {
      if (!charFull) return;
      const basePrompt = buildCharacterPrompt(charFull);
      const baseNegative = buildCharacterNegative(charFull);
      const loras = charFull.loras?.length
        ? charFull.loras.map((l) => ({
            id: l.id,
            name: l.name,
            weight: l.weight,
            trigger_words: l.trigger_words,
            lora_type: l.lora_type,
            optimal_weight: l.optimal_weight,
          }))
        : [];

      const matchB =
        referenceImages.length > 0
          ? referenceImages.find((r) => r.character_id === charFull.id)
          : null;

      setPlan({
        basePromptB: basePrompt,
        baseNegativePromptB: baseNegative,
        characterBLoras: loras,
        ipAdapterReferenceB: matchB?.character_key || "",
        ipAdapterWeightB: matchB?.preset?.weight ?? charFull.ip_adapter_weight ?? 0.75,
      });
    });
  }, [
    selectedCharacterBId,
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
    <div className={SIDE_PANEL_LAYOUT}>
      {/* Left: Main Form */}
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
          structure={structure}
          selectedCharacterBId={selectedCharacterBId}
          onSelectCharacterB={(id) => setPlan({ selectedCharacterBId: id })}
          basePromptB={basePromptB}
          setBasePromptB={(v: string) => setPlan({ basePromptB: v })}
          baseNegativePromptB={baseNegativePromptB}
          setBaseNegativePromptB={(v: string) => setPlan({ baseNegativePromptB: v })}
        />
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
        />
      </div>

      {/* Right: Settings Panel (sticky) */}
      <div className={SIDE_PANEL_CLASSES}>
        <StyleProfileSelector
          currentProfileId={currentStyleProfile?.id ?? null}
          currentProfileName={
            currentStyleProfile?.display_name ?? currentStyleProfile?.name ?? null
          }
          onSelect={handleInlineStyleProfileSelect}
        />

        <div>
          <label className="mb-1.5 block text-[10px] font-semibold tracking-wider text-zinc-500 uppercase">
            Options
          </label>
          <div className="flex flex-wrap gap-1.5">
            {TOGGLES.map((t) => (
              <label
                key={t.key}
                className={`flex cursor-pointer items-center gap-1 rounded-full border px-2.5 py-1 text-[10px] font-medium transition ${
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
        </div>
      </div>
    </div>
  );
}
