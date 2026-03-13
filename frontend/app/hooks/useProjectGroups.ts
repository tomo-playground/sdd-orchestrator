import { useEffect, useCallback, useRef } from "react";
import { useContextStore } from "../store/useContextStore";
import { useUIStore } from "../store/useUIStore";
import { fetchProjects } from "../store/actions/projectActions";
import { fetchGroups, loadGroupDefaults } from "../store/actions/groupActions";
import { cancelPendingSave } from "../store/effects/autoSave";
import { resetTransientStores } from "../store/resetAllStores";
import { clearStudioUrlParams } from "../utils/url";
import { ALL_GROUPS_ID } from "../constants";

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

  // Track whether initial group fetch has been triggered to prevent double-fetch
  const groupFetchedForProjectRef = useRef<number | null>(null);
  // Track whether recovery has already been attempted to prevent infinite loop
  // when a project genuinely has no groups (API returns [])
  const recoveryAttemptedRef = useRef<number | null>(null);

  // Fetch groups when projectId changes
  useEffect(() => {
    if (projectId !== null) {
      groupFetchedForProjectRef.current = projectId;
      recoveryAttemptedRef.current = null; // reset recovery on project change
      fetchGroups(projectId);
    }
  }, [projectId]);

  // Recovery: re-fetch groups if lost after transient state reset
  // Only triggers once per project — prevents infinite loop when project has no groups
  const isLoadingGroups = useContextStore((s) => s.isLoadingGroups);
  useEffect(() => {
    if (
      projectId !== null &&
      groups.length === 0 &&
      !isLoadingGroups &&
      groupFetchedForProjectRef.current === projectId &&
      recoveryAttemptedRef.current !== projectId
    ) {
      recoveryAttemptedRef.current = projectId;
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
      cancelPendingSave();
      setContext({ projectId: id, groupId: null, storyboardId: null, storyboardTitle: "" });
      resetTransientStores();
      clearStudioUrlParams();
    },
    [setContext]
  );

  const selectGroup = useCallback(
    (id: number) => {
      cancelPendingSave();
      setContext({ groupId: id, storyboardId: null, storyboardTitle: "" });
      resetTransientStores();
      clearStudioUrlParams();
    },
    [setContext]
  );

  return { projectId, groupId, projects, groups, selectProject, selectGroup };
}
