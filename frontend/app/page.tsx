"use client";

import { useState, useCallback } from "react";
import { useProjectGroups } from "./hooks/useProjectGroups";
import { ProjectDropdown, ProjectFormModal } from "./components/context";
import { createProject, updateProject } from "./store/actions/projectActions";
import type { ProjectItem } from "./types";
import StoryboardsSection from "./components/home/StoryboardsSection";
import CharactersSection from "./components/home/CharactersSection";
import Toast from "./components/ui/Toast";
import Footer from "./components/ui/Footer";

type HomeTab = "storyboards" | "characters";

export default function Home() {
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
    <>
      {/* Project context bar */}
      <div className="mx-auto flex max-w-5xl items-center gap-2 px-6 pt-4">
        <ProjectDropdown
          projects={projects}
          currentId={projectId}
          onSelect={selectProject}
          onNew={() => setShowProjectModal(true)}
          onEdit={(p) => setEditingProject(p)}
        />
      </div>

      {/* Tab Bar */}
      <div className="mx-auto w-full max-w-5xl px-6 pt-4">
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
      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-6">
        {tab === "storyboards" && (
          <StoryboardsSection
            projectId={projectId}
            groups={groups}
            selectGroup={selectGroup}
            showToast={showToast}
          />
        )}
        {tab === "characters" && <CharactersSection showToast={showToast} />}
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
    </>
  );
}
