"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Image } from "lucide-react";
import axios from "axios";
import { useShallow } from "zustand/react/shallow";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useUIStore } from "../../store/useUIStore";
import { useContextStore } from "../../store/useContextStore";
import { useRenderStore } from "../../store/useRenderStore";
import { useMaterialsCheck } from "../../hooks/useMaterialsCheck";
import { useAudioPlayer } from "../../hooks/useAudioPlayer";
import StyleProfileSelector from "../setup/StyleProfileSelector";
import EmptyState from "../ui/EmptyState";
import { API_BASE, API_TIMEOUT } from "../../constants";
import { getErrorMsg } from "../../utils/error";
import { isMultiCharStructure } from "../../utils/structure";
import type { VoicePreset } from "../../types";
import StageReadinessBar from "./StageReadinessBar";
import StageLocationsSection from "./StageLocationsSection";
import StageCharactersSection from "./StageCharactersSection";
import StageVoiceSection from "./StageVoiceSection";
import StageBgmSection from "./StageBgmSection";

export default function StageTab() {
  const storyboardId = useContextStore((s) => s.storyboardId);
  const scenes = useStoryboardStore((s) => s.scenes);
  const showToast = useUIStore((s) => s.showToast);
  const setActiveTab = useUIStore((s) => s.setActiveTab);
  const currentStyleProfile = useRenderStore((s) => s.currentStyleProfile);

  const router = useRouter();

  const {
    basePromptA,
    basePromptB,
    autoRewritePrompt,
    autoReplaceRiskyTags,
    hiResEnabled,
    veoEnabled,
    structure,
    selectedCharacterId,
    selectedCharacterBId,
    selectedCharacterName,
    selectedCharacterBName,
  } = useStoryboardStore(
    useShallow((s) => ({
      basePromptA: s.basePromptA,
      basePromptB: s.basePromptB,
      autoRewritePrompt: s.autoRewritePrompt,
      autoReplaceRiskyTags: s.autoReplaceRiskyTags,
      hiResEnabled: s.hiResEnabled,
      veoEnabled: s.veoEnabled,
      structure: s.structure,
      selectedCharacterId: s.selectedCharacterId,
      selectedCharacterBId: s.selectedCharacterBId,
      selectedCharacterName: s.selectedCharacterName,
      selectedCharacterBName: s.selectedCharacterBName,
    }))
  );
  const setPlan = useStoryboardStore((s) => s.set);

  const { data: materials } = useMaterialsCheck(storyboardId);
  const audioPlayer = useAudioPlayer();
  const [locReady, setLocReady] = useState(0);
  const [locTotal, setLocTotal] = useState(0);
  const [isAssigning, setIsAssigning] = useState(false);
  const [voicePresets, setVoicePresets] = useState<VoicePreset[]>([]);

  const isDialogue = isMultiCharStructure(structure);
  const hasPrompt = !!(basePromptA || basePromptB);

  const TOGGLES = [
    { key: "autoRewritePrompt" as const, label: "Auto Rewrite", value: autoRewritePrompt },
    { key: "autoReplaceRiskyTags" as const, label: "Safe Tags", value: autoReplaceRiskyTags },
    { key: "hiResEnabled" as const, label: "Hi-Res", value: hiResEnabled },
    { key: "veoEnabled" as const, label: "Veo", value: veoEnabled },
  ];

  useEffect(() => {
    axios
      .get<VoicePreset[]>(`${API_BASE}/voice-presets`)
      .then((r) => setVoicePresets(r.data))
      .catch(() => {});
  }, []);

  const handleLocStatusChange = useCallback((ready: number, total: number) => {
    setLocReady(ready);
    setLocTotal(total);
  }, []);

  const handleContinue = async () => {
    if (!storyboardId) return;
    setIsAssigning(true);
    try {
      const res = await axios.post(
        `${API_BASE}/storyboards/${storyboardId}/stage/assign-backgrounds`,
        null,
        { timeout: API_TIMEOUT.DEFAULT }
      );
      const assignments = res.data.assignments ?? [];
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
        showToast(`${assignments.length} scenes assigned to backgrounds`, "success");
      }
      setActiveTab("direct");
    } catch (error) {
      showToast(getErrorMsg(error, "Assignment failed — please retry"), "error");
    } finally {
      setIsAssigning(false);
    }
  };

  if (!storyboardId || scenes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-8 py-8">
        <EmptyState
          icon={Image}
          title="No Scenes Yet"
          description="Generate a script first to set up the stage."
        />
      </div>
    );
  }

  const readinessCategories = [
    {
      key: "style",
      label: "Style",
      ready: currentStyleProfile?.id != null,
    },
    {
      key: "locations",
      label: "Locations",
      ready: locTotal > 0 && locReady === locTotal,
    },
    {
      key: "characters",
      label: "Characters",
      ready: materials?.characters?.ready ?? false,
    },
    {
      key: "voice",
      label: "Voice",
      ready: materials?.voice?.ready ?? false,
    },
    {
      key: "music",
      label: "BGM",
      ready: materials?.music?.ready ?? false,
    },
  ];

  return (
    <div className="flex h-full flex-col overflow-y-auto px-8 py-6">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-base font-semibold text-zinc-900">Stage — Pre-production</h2>
        <p className="mt-0.5 text-xs text-zinc-500">
          Prepare backgrounds, characters, voice, and music before directing scenes.
        </p>
      </div>

      {/* Readiness Bar */}
      <div className="mb-6">
        <StageReadinessBar
          categories={readinessCategories}
          isAssigning={isAssigning}
          onContinue={handleContinue}
        />
      </div>

      {/* Sections */}
      <div className="space-y-8">
        {/* Visual Style */}
        <section>
          <h3 className="mb-3 text-sm font-semibold text-zinc-800">Visual Style</h3>
          <StyleProfileSelector
            currentProfileName={
              currentStyleProfile?.display_name ?? currentStyleProfile?.name ?? null
            }
          />
        </section>

        <div className="border-t border-zinc-100" />
        <StageLocationsSection storyboardId={storyboardId} onStatusChange={handleLocStatusChange} />

        <div className="border-t border-zinc-100" />
        <StageCharactersSection audioPlayer={audioPlayer} voicePresets={voicePresets} />

        {/* Base Prompts (read-only summary) */}
        <section>
          <h3 className="mb-2 text-[12px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">
            Base Prompts
          </h3>
          {hasPrompt ? (
            <div className="space-y-2">
              <PromptSummary
                label={isDialogue ? "A" : undefined}
                name={selectedCharacterName}
                value={basePromptA}
                charId={selectedCharacterId}
                onEdit={(id) => router.push(`/characters/${id}`)}
              />
              {isDialogue && (
                <PromptSummary
                  label="B"
                  name={selectedCharacterBName}
                  value={basePromptB}
                  charId={selectedCharacterBId}
                  onEdit={(id) => router.push(`/characters/${id}`)}
                />
              )}
            </div>
          ) : (
            <p className="text-xs text-zinc-400">캐릭터를 선택하면 자동 생성됩니다</p>
          )}
        </section>

        <div className="border-t border-zinc-100" />

        {/* Generation Settings */}
        <section>
          <h3 className="mb-3 text-sm font-semibold text-zinc-800">Generation Settings</h3>
          <div className="flex flex-wrap gap-1.5">
            {TOGGLES.map((t) => (
              <label
                key={t.key}
                className={`flex cursor-pointer items-center gap-1 rounded-full border px-2.5 py-1 text-[12px] font-medium transition ${
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
        </section>

        <div className="border-t border-zinc-100" />
        <StageVoiceSection audioPlayer={audioPlayer} voicePresets={voicePresets} />

        <div className="border-t border-zinc-100" />
        <StageBgmSection audioPlayer={audioPlayer} />
      </div>
    </div>
  );
}

/* ── Read-only prompt summary with edit link ────────────── */
function PromptSummary({
  label,
  name,
  value,
  charId,
  onEdit,
}: {
  label?: string;
  name?: string | null;
  value: string;
  charId?: number | null;
  onEdit: (id: number) => void;
}) {
  const truncated = value.length > 80 ? value.slice(0, 80) + "..." : value;
  return (
    <div className="flex items-start gap-3 rounded-xl border border-zinc-100 bg-zinc-50/50 px-3 py-2">
      <div className="min-w-0 flex-1">
        {label && <span className="text-[11px] font-semibold text-zinc-400">{label}: </span>}
        {name && <span className="text-[11px] font-medium text-zinc-600">{name}</span>}
        <p className="mt-0.5 truncate text-xs text-zinc-500" title={value}>
          {truncated || "—"}
        </p>
      </div>
      {charId && (
        <button
          type="button"
          onClick={() => onEdit(charId)}
          className="shrink-0 text-[11px] font-medium text-zinc-400 transition hover:text-zinc-600"
        >
          Edit →
        </button>
      )}
    </div>
  );
}
