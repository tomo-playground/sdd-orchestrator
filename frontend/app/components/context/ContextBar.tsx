"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import ProjectDropdown from "./ProjectDropdown";
import GroupDropdown from "./GroupDropdown";
import ProjectFormModal from "./ProjectFormModal";
import GroupFormModal from "./GroupFormModal";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import { useProjectGroups } from "../../hooks/useProjectGroups";
import { createProject, updateProject } from "../../store/actions/projectActions";
import { createGroup, updateGroup } from "../../store/actions/groupActions";
import type { GroupItem, ProjectItem } from "../../types";

function Chevron() {
  return (
    <svg className="h-3.5 w-3.5 shrink-0 text-zinc-300" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
    </svg>
  );
}

type Props = {
  title?: string;
};

export default function ContextBar({ title }: Props) {
  const router = useRouter();
  const { projectId, groupId, projects, groups, selectProject, selectGroup } = useProjectGroups();
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [editingProject, setEditingProject] = useState<ProjectItem | null>(null);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [editingGroup, setEditingGroup] = useState<GroupItem | null>(null);
  const [showNewSbModal, setShowNewSbModal] = useState(false);
  const [newSbTitle, setNewSbTitle] = useState("");
  const [pendingGroupId, setPendingGroupId] = useState<number | null>(null);

  const openNewStoryboard = useCallback((gid: number) => {
    setPendingGroupId(gid);
    setNewSbTitle("");
    setShowNewSbModal(true);
  }, []);

  const confirmNewStoryboard = useCallback(() => {
    if (!pendingGroupId) return;
    selectGroup(pendingGroupId);
    const params = new URLSearchParams({ new: "true" });
    if (newSbTitle.trim()) params.set("title", newSbTitle.trim());
    router.push(`/studio?${params.toString()}`);
  }, [pendingGroupId, newSbTitle, selectGroup, router]);

  return (
    <>
      <div className="flex items-center gap-0.5 min-w-0">
        <ProjectDropdown
          projects={projects}
          currentId={projectId}
          onSelect={selectProject}
          onNew={() => setShowProjectModal(true)}
          onEdit={(p) => setEditingProject(p)}
        />
        <Chevron />
        <GroupDropdown
          groups={groups}
          currentId={groupId}
          onSelect={selectGroup}
          onNew={() => setShowGroupModal(true)}
          onEdit={(g) => setEditingGroup(g)}
          onNewStoryboard={openNewStoryboard}
        />
        {title && (
          <>
            <Chevron />
            <span className="text-sm font-bold text-zinc-900 truncate max-w-[160px] md:max-w-xs">
              {title}
            </span>
          </>
        )}
      </div>

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

      {showGroupModal && projectId && (
        <GroupFormModal
          projectId={projectId}
          onSave={async (data) => {
            const g = await createGroup(data as Parameters<typeof createGroup>[0]);
            if (g) selectGroup(g.id);
          }}
          onClose={() => setShowGroupModal(false)}
        />
      )}

      {editingGroup && projectId && (
        <GroupFormModal
          group={editingGroup}
          projectId={projectId}
          onSave={async (data) => {
            await updateGroup(editingGroup.id, data);
          }}
          onClose={() => setEditingGroup(null)}
        />
      )}

      {/* New Storyboard Title Modal */}
      {showNewSbModal && (
        <Modal open onClose={() => setShowNewSbModal(false)} size="sm">
          <Modal.Header>
            <h2 className="text-sm font-bold text-zinc-900">New Storyboard</h2>
            <button onClick={() => setShowNewSbModal(false)} className="text-zinc-400 hover:text-zinc-600 text-xs">x</button>
          </Modal.Header>
          <div className="px-5 py-4">
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
              Title *
            </label>
            <input
              value={newSbTitle}
              onChange={(e) => setNewSbTitle(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && newSbTitle.trim()) confirmNewStoryboard(); }}
              placeholder="e.g. 에어컨 소리 30초 쇼츠"
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none"
              autoFocus
            />
          </div>
          <Modal.Footer>
            <Button variant="ghost" size="sm" onClick={() => setShowNewSbModal(false)}>Cancel</Button>
            <Button size="sm" disabled={!newSbTitle.trim()} onClick={confirmNewStoryboard}>Create</Button>
          </Modal.Footer>
        </Modal>
      )}
    </>
  );
}
