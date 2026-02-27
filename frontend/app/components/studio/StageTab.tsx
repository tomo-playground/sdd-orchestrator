"use client";

import { useCallback, useEffect, useState } from "react";
import { Image } from "lucide-react";
import axios from "axios";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useUIStore } from "../../store/useUIStore";
import { useContextStore } from "../../store/useContextStore";
import { useMaterialsCheck } from "../../hooks/useMaterialsCheck";
import { useAudioPlayer } from "../../hooks/useAudioPlayer";
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

  const { data: materials } = useMaterialsCheck(storyboardId);
  const audioPlayer = useAudioPlayer();
  const [locReady, setLocReady] = useState(0);
  const [locTotal, setLocTotal] = useState(0);
  const [isAssigning, setIsAssigning] = useState(false);
  const [voicePresets, setVoicePresets] = useState<VoicePreset[]>([]);

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
        <StageLocationsSection storyboardId={storyboardId} onStatusChange={handleLocStatusChange} />

        <div className="border-t border-zinc-100" />
        <StageCharactersSection audioPlayer={audioPlayer} voicePresets={voicePresets} />

        <div className="border-t border-zinc-100" />
        <StageVoiceSection audioPlayer={audioPlayer} voicePresets={voicePresets} />

        <div className="border-t border-zinc-100" />
        <StageBgmSection audioPlayer={audioPlayer} />
      </div>
    </div>
  );
}
