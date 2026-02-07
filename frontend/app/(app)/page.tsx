"use client";

import { useState, useCallback } from "react";
import { useProjectGroups } from "../hooks/useProjectGroups";
import StoryboardsSection from "../components/home/StoryboardsSection";
import CharactersSection from "../components/home/CharactersSection";
import Toast from "../components/ui/Toast";
import Footer from "../components/ui/Footer";

export default function Home() {
  const { projectId, groupId, groups } = useProjectGroups();
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const showToast = useCallback((message: string, type: "success" | "error") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  return (
    <>
      <main className="w-full max-w-5xl flex-1 space-y-8 px-6 py-6">
        <StoryboardsSection
          projectId={projectId}
          groupId={groupId}
          groups={groups}
          showToast={showToast}
        />
        <div className="border-t border-zinc-200" />
        <CharactersSection showToast={showToast} />
      </main>

      <Footer />

      {toast && <Toast message={toast.message} type={toast.type} />}
    </>
  );
}
