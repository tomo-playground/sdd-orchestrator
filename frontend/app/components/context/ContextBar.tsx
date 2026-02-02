"use client";

import { useState } from "react";
import ProjectDropdown from "./ProjectDropdown";
import GroupDropdown from "./GroupDropdown";
import ProjectFormModal from "./ProjectFormModal";
import GroupFormModal from "./GroupFormModal";
import { useProjectGroups } from "../../hooks/useProjectGroups";
import { createProject } from "../../store/actions/projectActions";
import { createGroup, updateGroup } from "../../store/actions/groupActions";
import type { GroupItem } from "../../types";

type Props = {
  title?: string;
};

export default function ContextBar({ title }: Props) {
  const { projectId, groupId, projects, groups, selectProject, selectGroup } = useProjectGroups();
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [editingGroup, setEditingGroup] = useState<GroupItem | null>(null);

  return (
    <>
      <div className="flex items-center gap-1 min-w-0">
        <ProjectDropdown
          projects={projects}
          currentId={projectId}
          onSelect={selectProject}
          onNew={() => setShowProjectModal(true)}
        />
        <span className="text-zinc-300 text-xs">/</span>
        <GroupDropdown
          groups={groups}
          currentId={groupId}
          onSelect={selectGroup}
          onNew={() => setShowGroupModal(true)}
          onEdit={(g) => setEditingGroup(g)}
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
    </>
  );
}
