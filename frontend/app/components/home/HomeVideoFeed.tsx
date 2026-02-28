"use client";

import { Clapperboard } from "lucide-react";
import WelcomeBar from "./WelcomeBar";
import QuickStatsBar from "./QuickStatsBar";
import ContinueWorkingSection from "./ContinueWorkingSection";
import ShowcaseSection from "./ShowcaseSection";
import Footer from "../ui/Footer";
import { useContextStore } from "../../store/useContextStore";
import { useUIStore } from "../../store/useUIStore";

export default function HomeVideoFeed() {
  const projects = useContextStore((s) => s.projects);
  const isLoadingProjects = useContextStore((s) => s.isLoadingProjects);
  const setUI = useUIStore((s) => s.set);

  // Empty state: no projects after loading completes
  if (!isLoadingProjects && projects.length === 0) {
    return (
      <div className="flex min-h-screen flex-col p-8">
        <div className="flex flex-1 items-center justify-center">
          <div className="w-full max-w-md rounded-2xl border border-dashed border-zinc-200 bg-zinc-50/50 p-12 text-center">
            <div className="mb-4 inline-flex rounded-full bg-zinc-100 p-4">
              <Clapperboard className="h-8 w-8 text-zinc-400" />
            </div>
            <h2 className="mb-2 text-lg font-bold text-zinc-900">첫 영상을 만들어보세요</h2>
            <p className="mb-6 text-sm text-zinc-500">
              채널과 시리즈를 설정하면 바로 영상 제작을 시작할 수 있습니다
            </p>
            <button
              onClick={() => setUI({ showSetupWizard: true, setupWizardInitialStep: 1 })}
              className="inline-flex items-center gap-2 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-800"
            >
              시작하기
            </button>
          </div>
        </div>
        <Footer />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col p-8">
      <div className="space-y-6">
        <WelcomeBar />
        <QuickStatsBar />
        <ContinueWorkingSection />
        <ShowcaseSection />
      </div>
      <Footer />
    </div>
  );
}
