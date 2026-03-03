import { useContextStore } from "../useContextStore";
import { API_ROOT, API_BASE } from "../../constants";
import type { ProjectItem } from "../../types";

export function getCurrentProject(): ProjectItem | null {
  const { projects, projectId } = useContextStore.getState();
  return projects.find((p) => p.id === projectId) ?? null;
}

export function hasValidProfile(): boolean {
  const project = getCurrentProject();
  return project?.name != null;
}

export function getChannelAvatarUrl(): string | null {
  const project = getCurrentProject();
  if (!project?.avatar_key) return null;
  return resolveAvatarUrl(project.avatar_key);
}

/** Resolve avatar_key to full URL. Handles both character preview paths and legacy IP-Adapter keys. */
export function resolveAvatarUrl(avatarKey: string): string {
  if (avatarKey.startsWith("/")) return `${API_ROOT}${avatarKey}`;
  if (avatarKey.startsWith("http")) return avatarKey;
  return `${API_BASE}/controlnet/ip-adapter/reference/${avatarKey}/image`;
}
