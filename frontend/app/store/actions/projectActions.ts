import axios from "axios";
import { useStudioStore } from "../useStudioStore";
import { API_BASE } from "../../constants";
import type { ProjectItem } from "../../types";

export async function fetchProjects(): Promise<void> {
  const { setContextLoading, setProjects } = useStudioStore.getState();
  setContextLoading({ isLoadingProjects: true });
  try {
    const res = await axios.get<ProjectItem[]>(`${API_BASE}/projects`);
    setProjects(res.data);
  } catch (error) {
    console.error("[fetchProjects] Failed:", error);
  } finally {
    setContextLoading({ isLoadingProjects: false });
  }
}

export async function createProject(data: {
  name: string;
  description?: string;
  handle?: string;
  avatar_media_asset_id?: number | null;
}): Promise<ProjectItem | undefined> {
  const { showToast } = useStudioStore.getState();
  try {
    const res = await axios.post<ProjectItem>(`${API_BASE}/projects`, data);
    await fetchProjects();
    showToast("Project created", "success");
    return res.data;
  } catch (error) {
    console.error("[createProject] Failed:", error);
    showToast("Failed to create project", "error");
    return undefined;
  }
}

export async function updateProject(
  projectId: number,
  data: { name?: string; description?: string; handle?: string; avatar_media_asset_id?: number | null }
): Promise<ProjectItem | undefined> {
  const { showToast } = useStudioStore.getState();
  try {
    const res = await axios.put<ProjectItem>(`${API_BASE}/projects/${projectId}`, data);
    await fetchProjects();
    showToast("Project updated", "success");
    return res.data;
  } catch (error) {
    console.error("[updateProject] Failed:", error);
    showToast("Failed to update project", "error");
    return undefined;
  }
}

export async function deleteProject(projectId: number): Promise<boolean> {
  const { showToast } = useStudioStore.getState();
  try {
    await axios.delete(`${API_BASE}/projects/${projectId}`);
    await fetchProjects();
    showToast("Project deleted", "success");
    return true;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 409) {
      showToast("Cannot delete: project has groups", "error");
    } else {
      console.error("[deleteProject] Failed:", error);
      showToast("Failed to delete project", "error");
    }
    return false;
  }
}
