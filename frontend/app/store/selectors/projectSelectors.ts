import { useStudioStore } from "../useStudioStore";
import { API_BASE } from "../../constants";
import type { ProjectItem } from "../../types";

export function getCurrentProject(): ProjectItem | null {
  const { projects, projectId } = useStudioStore.getState();
  return projects.find((p) => p.id === projectId) ?? null;
}

export function hasValidProfile(): boolean {
  const project = getCurrentProject();
  return project?.name != null;
}

export function getChannelAvatarUrl(): string | null {
  const project = getCurrentProject();
  if (!project?.avatar_key) return null;
  return `${API_BASE}/controlnet/ip-adapter/reference/${project.avatar_key}/image`;
}
