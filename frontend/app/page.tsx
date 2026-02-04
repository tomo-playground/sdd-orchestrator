"use client";

import { useState, useCallback } from "react";
import { useProjectGroups } from "./hooks/useProjectGroups";
import StoryboardsSection from "./components/home/StoryboardsSection";
import CharactersSection from "./components/home/CharactersSection";
import Toast from "./components/ui/Toast";
import Footer from "./components/ui/Footer";

type HomeTab = "storyboards" | "characters";

export default function Home() {
  const [tab, setTab] = useState<HomeTab>("storyboards");
  const { projectId, groupId, groups, selectGroup } = useProjectGroups();
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const showToast = useCallback((message: string, type: "success" | "error") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  return (
    <>
      {/* Tab Bar */}
      <div className="w-full max-w-5xl px-6 pt-4">
        <div className="flex gap-1 rounded-xl bg-zinc-100/60 p-1">
          {(["storyboards", "characters"] as HomeTab[]).map((t) => (
            <button
              key={t}
              data-testid={`home-tab-${t}`}
              onClick={() => setTab(t)}
              className={`flex-1 rounded-lg py-2 text-xs font-semibold transition ${
                tab === t ? "bg-white text-zinc-900 shadow-sm" : "text-zinc-500 hover:text-zinc-700"
              }`}
            >
              {t === "storyboards" ? "Storyboards" : "Characters"}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="w-full max-w-5xl flex-1 px-6 py-6">
        {tab === "storyboards" && (
          <StoryboardsSection
            projectId={projectId}
            groupId={groupId}
            groups={groups}
            selectGroup={selectGroup}
            showToast={showToast}
          />
        )}
        {tab === "characters" && <CharactersSection showToast={showToast} />}
      </main>

      <Footer />

      {toast && <Toast message={toast.message} type={toast.type} />}
    </>
  );
}
