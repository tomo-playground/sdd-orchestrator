"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useProjectGroups } from "./hooks/useProjectGroups";
import { ProjectDropdown, ProjectFormModal } from "./components/context";
import { createProject, updateProject } from "./store/actions/projectActions";
import type { ProjectItem } from "./types";
import StoryboardsSection from "./components/home/StoryboardsSection";
import CharactersSection from "./components/home/CharactersSection";
import Toast from "./components/ui/Toast";
import Footer from "./components/ui/Footer";
import CommandPalette from "./components/ui/CommandPalette";

type HomeTab = "storyboards" | "characters";

export default function Home() {
  const router = useRouter();
  const [tab, setTab] = useState<HomeTab>("storyboards");
  const { projectId, projects, groups, selectProject, selectGroup } = useProjectGroups();
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [editingProject, setEditingProject] = useState<ProjectItem | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const showToast = useCallback((message: string, type: "success" | "error") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-50 via-white to-zinc-100 font-[family-name:var(--font-sans)]">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-zinc-200/60 bg-white/80 backdrop-blur-lg">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold tracking-tight text-zinc-900">Shorts Producer</h1>
            <span className="text-zinc-300">/</span>
            <ProjectDropdown
              projects={projects}
              currentId={projectId}
              onSelect={selectProject}
              onNew={() => setShowProjectModal(true)}
              onEdit={(p) => setEditingProject(p)}
            />
          </div>
          <div className="flex items-center gap-2">
            <button
              data-testid="manage-link"
              onClick={() => router.push("/manage")}
              className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-xs font-semibold text-zinc-600 hover:bg-zinc-50 transition"
            >
              Manage
            </button>
          </div>
        </div>
      </header>

      {/* Tab Bar */}
      <div className="mx-auto max-w-5xl px-6 pt-4">
        <div className="flex gap-1 rounded-xl bg-zinc-100/60 p-1">
          {(["storyboards", "characters"] as HomeTab[]).map((t) => (
            <button
              key={t}
              data-testid={`home-tab-${t}`}
              onClick={() => setTab(t)}
              className={`flex-1 rounded-lg py-2 text-xs font-semibold transition ${
                tab === t
                  ? "bg-white text-zinc-900 shadow-sm"
                  : "text-zinc-500 hover:text-zinc-700"
              }`}
            >
              {t === "storyboards" ? "Storyboards" : "Characters"}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="mx-auto max-w-5xl px-6 py-6">
        {tab === "storyboards" && (
          <StoryboardsSection
            projectId={projectId}
            groups={groups}
            selectGroup={selectGroup}
            showToast={showToast}
          />
        )}
        {tab === "characters" && (
          <CharactersSection showToast={showToast} />
        )}
      </main>

      <Footer />

      {toast && <Toast message={toast.message} type={toast.type} />}

      {showProjectModal && (
        <ProjectFormModal
          onSave={async (data) => {
            const p = await createProject(data);
            if (p) selectProject(p.id);
          }}
          onClose={() => setShowProjectModal(false)}
        />
      )}

      {editingProject && (
        <ProjectFormModal
          project={editingProject}
          onSave={async (data) => {
            await updateProject(editingProject.id, data);
          }}
          onClose={() => setEditingProject(null)}
        />
      )}

      <CommandPalette />
    </div>
  );
}
