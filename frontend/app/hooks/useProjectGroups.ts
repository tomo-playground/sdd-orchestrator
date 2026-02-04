import { useEffect, useCallback } from "react";
import { useStudioStore } from "../store/useStudioStore";
import { fetchProjects } from "../store/actions/projectActions";
import { fetchGroups, loadGroupDefaults } from "../store/actions/groupActions";

/**
 * Manages project/group lifecycle:
 * - Fetches projects on mount
 * - Fetches groups when projectId changes
 * - Loads group defaults when groupId changes
 * - Auto-selects first item when lists load
 */
export function useProjectGroups() {
  const projectId = useStudioStore((s) => s.projectId);
  const groupId = useStudioStore((s) => s.groupId);
  const projects = useStudioStore((s) => s.projects);
  const groups = useStudioStore((s) => s.groups);
  const setMeta = useStudioStore((s) => s.setMeta);
  const resetScenes = useStudioStore((s) => s.resetScenes);

  // Fetch projects on mount
  useEffect(() => {
    fetchProjects();
  }, []);

  // Auto-select first project when projects load and no projectId set
  useEffect(() => {
    if (projects.length > 0 && projectId === null) {
      setMeta({ projectId: projects[0].id });
    }
  }, [projects, projectId, setMeta]);

  // Fetch groups when projectId changes
  useEffect(() => {
    if (projectId !== null) {
      fetchGroups(projectId);
    }
  }, [projectId]);

  // Auto-select first group when groups load and no groupId set
  useEffect(() => {
    if (groups.length > 0 && (groupId === null || !groups.some((g) => g.id === groupId))) {
      setMeta({ groupId: groups[0].id });
    }
  }, [groups, groupId, setMeta]);

  // Load group render defaults when groupId changes
  useEffect(() => {
    if (groupId !== null) {
      loadGroupDefaults(groupId);
    }
  }, [groupId]);

  const selectProject = useCallback(
    (id: number) => {
      setMeta({ projectId: id, groupId: null, storyboardId: null, storyboardTitle: "" });
      resetScenes();
    },
    [setMeta, resetScenes]
  );

  const selectGroup = useCallback(
    (id: number) => {
      setMeta({ groupId: id, storyboardId: null, storyboardTitle: "" });
      resetScenes();
    },
    [setMeta, resetScenes]
  );

  return { projectId, groupId, projects, groups, selectProject, selectGroup };
}
