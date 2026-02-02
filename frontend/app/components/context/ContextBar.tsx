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
      <div className="flex items-center gap-1 min-w-0">
        <ProjectDropdown
          projects={projects}
          currentId={projectId}
          onSelect={selectProject}
          onNew={() => setShowProjectModal(true)}
          onEdit={(p) => setEditingProject(p)}
        />
        <span className="text-zinc-300 text-xs">/</span>
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
            <span className="text-zinc-300 text-xs">/</span>
            <span className="text-sm font-bold text-zinc-900 truncate max-w-[200px] md:max-w-md">
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
