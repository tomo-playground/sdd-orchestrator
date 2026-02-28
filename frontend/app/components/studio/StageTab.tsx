"use client";

import React, { useCallback, useEffect, useState } from "react";
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
import StageReadinessBar from "./StageReadinessBar";
import StageLocationsSection from "./StageLocationsSection";
import StageCharactersSection from "./StageCharactersSection";
import StageVoiceSection from "./StageVoiceSection";
import StageBgmSection from "./StageBgmSection";
import InfoTooltip from "../ui/InfoTooltip";

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

  const voicePresets = useRenderStore((s) => s.voicePresets);
  const fetchVoicePresets = useRenderStore((s) => s.fetchVoicePresets);

  const { data: materials } = useMaterialsCheck(storyboardId);
  const audioPlayer = useAudioPlayer();
  const [locReady, setLocReady] = useState(0);
  const [locTotal, setLocTotal] = useState(0);
  const [isAssigning, setIsAssigning] = useState(false);

  const TOGGLES: {
    key: "autoRewritePrompt" | "autoReplaceRiskyTags" | "hiResEnabled" | "veoEnabled";
    label: string;
    value: boolean;
    tooltip?: React.ReactNode;
  }[] = [
    { key: "autoRewritePrompt", label: "자동 리라이트", value: autoRewritePrompt },
    { key: "autoReplaceRiskyTags", label: "안전 태그", value: autoReplaceRiskyTags },
    {
      key: "hiResEnabled",
      label: "고해상도",
      value: hiResEnabled,
      tooltip: <InfoTooltip term="hi-res" position="bottom" />,
    },
    { key: "veoEnabled", label: "Veo", value: veoEnabled },
  ];

  useEffect(() => {
    void fetchVoicePresets();
  }, [fetchVoicePresets]);

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
        showToast(`${assignments.length}개 씬에 배경이 할당되었습니다`, "success");
      }
      setActiveTab("direct");
    } catch (error) {
      showToast(getErrorMsg(error, "배경 할당에 실패했습니다 — 다시 시도하세요"), "error");
    } finally {
      setIsAssigning(false);
    }
  };

  if (!storyboardId || scenes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-8 py-8">
        <EmptyState
          icon={Image}
          title="씬이 없습니다"
          description="먼저 스크립트를 생성하세요."
        />
      </div>
    );
  }

  const readinessCategories = [
    { key: "style", label: "화풍", ready: currentStyleProfile?.id != null },
    { key: "locations", label: "배경", ready: locTotal > 0 && locReady === locTotal },
    { key: "characters", label: "캐릭터", ready: materials?.characters?.ready ?? false },
    { key: "voice", label: "음성", ready: materials?.voice?.ready ?? false },
    { key: "music", label: "BGM", ready: materials?.music?.ready ?? false },
  ];

  return (
    <div className="flex h-full flex-col overflow-y-auto px-5 py-4">
      {/* Header */}
      <div className="mb-4">
        <h2 className="text-base font-semibold text-zinc-900">스테이지 — 사전 준비</h2>
        <p className="mt-0.5 text-xs text-zinc-500">
          배경, 캐릭터, 음성, 음악을 준비한 후 씬을 연출하세요.
        </p>
      </div>

      {/* Readiness Bar */}
      <div className="mb-4">
        <StageReadinessBar
          categories={readinessCategories}
          isAssigning={isAssigning}
          onContinue={handleContinue}
        />
      </div>

      {/* Sections */}
      <div className="space-y-5">
        {/* Visual Style + Generation Settings — inline */}
        <section>
          <h3 className="mb-3 text-sm font-semibold text-zinc-800">화풍 및 생성 설정</h3>
          <div className="flex flex-wrap items-center gap-2">
            <StyleProfileSelector
              currentProfileName={
                currentStyleProfile?.display_name ?? currentStyleProfile?.name ?? null
              }
            />
            <span className="mx-1 h-4 w-px bg-zinc-200" />
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
                {t.tooltip && <span className="ml-0.5">{t.tooltip}</span>}
              </label>
            ))}
          </div>
        </section>

        <StageLocationsSection storyboardId={storyboardId} onStatusChange={handleLocStatusChange} />
        <StageCharactersSection audioPlayer={audioPlayer} voicePresets={voicePresets} />
        <StageVoiceSection audioPlayer={audioPlayer} voicePresets={voicePresets} />
        <StageBgmSection audioPlayer={audioPlayer} />
      </div>
    </div>
  );
}
