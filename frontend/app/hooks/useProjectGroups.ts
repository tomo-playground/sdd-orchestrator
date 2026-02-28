import { useEffect, useCallback } from "react";
import { useContextStore } from "../store/useContextStore";
import { useStoryboardStore } from "../store/useStoryboardStore";
import { useRenderStore } from "../store/useRenderStore";
import { useUIStore } from "../store/useUIStore";
import { fetchProjects } from "../store/actions/projectActions";
import { fetchGroups, loadGroupDefaults } from "../store/actions/groupActions";
import { ALL_GROUPS_ID } from "../constants";

/**
 * Clear studio URL params (?id, ?new) to prevent stale storyboard loading after context switch.
 * Uses window.history.replaceState instead of Next.js router to avoid hook dependency
 * (this runs inside useCallback, not a component render cycle).
 */
function clearStudioUrlParams() {
  const url = new URL(window.location.href);
  if (url.searchParams.has("id") || url.searchParams.has("new")) {
    url.searchParams.delete("id");
    url.searchParams.delete("new");
    window.history.replaceState({}, "", url.toString());
  }
}

/**
 * Manages project/group lifecycle:
 * - Fetches projects on mount
 * - Fetches groups when projectId changes
 * - Loads group defaults when groupId changes
 * - Auto-selects first item when lists load
 */
export function useProjectGroups() {
  const projectId = useContextStore((s) => s.projectId);
  const groupId = useContextStore((s) => s.groupId);
  const projects = useContextStore((s) => s.projects);
  const groups = useContextStore((s) => s.groups);
  const setContext = useContextStore((s) => s.setContext);
  const setScenes = useStoryboardStore((s) => s.setScenes);
  const clearScenes = useCallback(() => setScenes([]), [setScenes]);

  // Fetch projects on mount
  useEffect(() => {
    fetchProjects();
  }, []);

  // Auto-select first project when projects load and no projectId set
  useEffect(() => {
    if (projects.length > 0 && projectId === null) {
      setContext({ projectId: projects[0].id });
    }
  }, [projects, projectId, setContext]);

  // Fetch groups when projectId changes
  useEffect(() => {
    if (projectId !== null) {
      fetchGroups(projectId);
    }
  }, [projectId]);

  // Recovery: re-fetch groups if lost after transient state reset
  const isLoadingGroups = useContextStore((s) => s.isLoadingGroups);
  useEffect(() => {
    if (projectId !== null && groups.length === 0 && !isLoadingGroups) {
      fetchGroups(projectId);
    }
  }, [projectId, groups.length, isLoadingGroups]);

  // Auto-select first group when groups load and no groupId set
  // Skip when "All Groups" (ALL_GROUPS_ID) is explicitly selected
  useEffect(() => {
    if (
      groups.length > 0 &&
      groupId !== ALL_GROUPS_ID &&
      (groupId === null || !groups.some((g) => g.id === groupId))
    ) {
      setContext({ groupId: groups[0].id });
    }
  }, [groups, groupId, setContext]);

  // Load group render defaults when groupId changes
  useEffect(() => {
    if (groupId !== null && groupId !== ALL_GROUPS_ID) {
      loadGroupDefaults(groupId);
    }
  }, [groupId]);

  const selectProject = useCallback(
    (id: number) => {
      setContext({ projectId: id, groupId: null, storyboardId: null, storyboardTitle: "" });
      clearScenes();
      useStoryboardStore.getState().reset();
      useRenderStore.getState().reset();
      useUIStore.getState().resetUI();
      clearStudioUrlParams();
    },
    [setContext, clearScenes]
  );

  const selectGroup = useCallback(
    (id: number) => {
      setContext({ groupId: id, storyboardId: null, storyboardTitle: "" });
      clearScenes();
      useStoryboardStore.getState().reset();
      useRenderStore.getState().reset();
      useUIStore.getState().resetUI();
      clearStudioUrlParams();
    },
    [setContext, clearScenes]
  );

  return { projectId, groupId, projects, groups, selectProject, selectGroup };
}
