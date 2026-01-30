"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import axios from "axios";
import { useStudioStore } from "../store/useStudioStore";
import type { StudioTab } from "../store/slices/metaSlice";
import type { Scene } from "../types";
import { API_BASE } from "../constants";
import TabBar from "../components/studio/TabBar";
import PlanTab from "../components/studio/PlanTab";
import ScenesTab from "../components/studio/ScenesTab";
import OutputTab from "../components/studio/OutputTab";
import InsightsTab from "../components/studio/InsightsTab";
import Toast from "../components/ui/Toast";
import LoadingSpinner from "../components/ui/LoadingSpinner";

function StudioContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const storyboardId = searchParams.get("id");
  const [isLoadingDb, setIsLoadingDb] = useState(false);

  const activeTab = useStudioStore((s) => s.activeTab);
  const setActiveTab = useStudioStore((s) => s.setActiveTab);
  const toast = useStudioStore((s) => s.toast);
  const setMeta = useStudioStore((s) => s.setMeta);
  const setScenes = useStudioStore((s) => s.setScenes);
  const setPlan = useStudioStore((s) => s.setPlan);
  const scenes = useStudioStore((s) => s.scenes);

  // Load storyboard from DB if ?id=X
  useEffect(() => {
    if (!storyboardId) return;
    const id = parseInt(storyboardId, 10);
    if (isNaN(id)) return;

    setIsLoadingDb(true);
    axios
      .get(`${API_BASE}/storyboards/${id}`)
      .then((res) => {
        const data = res.data;
        setMeta({
          storyboardId: data.id,
          storyboardTitle: data.title,
          activeTab: data.scenes?.length > 0 ? "scenes" : "plan",
        });
        setPlan({
          selectedCharacterId: data.default_character_id || null,
          topic: data.description || "",
        });

        // Map DB scenes → frontend Scene type
        if (data.scenes?.length > 0) {
          const mapped: Scene[] = data.scenes.map((s: Record<string, unknown>, i: number) => ({
            id: i,
            script: s.script || "",
            speaker: s.speaker || "Narrator",
            duration: s.duration || 3,
            image_prompt: s.image_prompt || "",
            image_prompt_ko: s.image_prompt_ko || "",
            image_url: s.image_url || null,
            description: s.description || "",
            width: s.width || 512,
            height: s.height || 768,
            negative_prompt: s.negative_prompt || "",
            steps: s.steps || 27,
            cfg_scale: s.cfg_scale || 7,
            sampler_name: s.sampler_name || "DPM++ 2M Karras",
            seed: s.seed || -1,
            clip_skip: s.clip_skip || 2,
            isGenerating: false,
            debug_payload: "",
            context_tags: s.context_tags || undefined,
          }));
          setScenes(mapped);
        }
      })
      .catch(() => {
        setMeta({ storyboardId: null });
      })
      .finally(() => setIsLoadingDb(false));
  }, [storyboardId, setMeta, setPlan, setScenes]);

  if (isLoadingDb) {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-50 via-white to-zinc-100 font-[family-name:var(--font-sans)]">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-zinc-200/60 bg-white/80 backdrop-blur-lg">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/")}
              className="text-xs text-zinc-500 hover:text-zinc-700"
            >
              Home
            </button>
            <span className="text-zinc-300">/</span>
            <h1 className="text-sm font-bold text-zinc-900">
              {useStudioStore.getState().storyboardTitle || "New Storyboard"}
            </h1>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-zinc-400">
            {scenes.length > 0 && <span>{scenes.length} scenes</span>}
            {useStudioStore.getState().storyboardId && (
              <span className="rounded bg-zinc-100 px-2 py-0.5">
                ID: {useStudioStore.getState().storyboardId}
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Tab Bar */}
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Tab Content */}
      <main className="mx-auto max-w-5xl px-6 py-4">
        {/* Scenes tab uses display:none for state preservation */}
        <div style={{ display: activeTab === "scenes" ? "block" : "none" }}>
          <ScenesTab />
        </div>

        {activeTab === "plan" && <PlanTab />}
        {activeTab === "output" && <OutputTab />}
        {activeTab === "insights" && <InsightsTab />}
      </main>

      {toast && <Toast message={toast.message} type={toast.type} />}
    </div>
  );
}

export default function StudioPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center">
          <LoadingSpinner size="lg" />
        </div>
      }
    >
      <StudioContent />
    </Suspense>
  );
}
