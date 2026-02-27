"use client";

import { useCallback, useEffect, useState } from "react";
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

  const { autoRewritePrompt, autoReplaceRiskyTags, hiResEnabled, veoEnabled } = useStoryboardStore(
    useShallow((s) => ({
      autoRewritePrompt: s.autoRewritePrompt,
      autoReplaceRiskyTags: s.autoReplaceRiskyTags,
      hiResEnabled: s.hiResEnabled,
      veoEnabled: s.veoEnabled,
    }))
  );
  const setPlan = useStoryboardStore((s) => s.set);

  const { data: materials } = useMaterialsCheck(storyboardId);
  const audioPlayer = useAudioPlayer();
  const [locReady, setLocReady] = useState(0);
  const [locTotal, setLocTotal] = useState(0);
  const [isAssigning, setIsAssigning] = useState(false);
  const [voicePresets, setVoicePresets] = useState<VoicePreset[]>([]);

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
