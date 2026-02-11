"use client";

import { useProjectGroups } from "../hooks/useProjectGroups";
import StoryboardsSection from "../components/home/StoryboardsSection";
import CharactersSection from "../components/home/CharactersSection";
import Footer from "../components/ui/Footer";

export default function Home() {
  const { projectId, groupId } = useProjectGroups();

  return (
    <>
      <main className="w-full max-w-5xl flex-1 space-y-8 px-6 py-6">
        <StoryboardsSection projectId={projectId} groupId={groupId} />
        <div className="border-t border-zinc-200" />
        <CharactersSection />
      </main>

      <Footer />
    </>
  );
}
