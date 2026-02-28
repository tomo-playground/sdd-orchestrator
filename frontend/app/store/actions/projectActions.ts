import axios from "axios";
import { useContextStore } from "../useContextStore";
import { useUIStore } from "../useUIStore";
import { API_BASE } from "../../constants";
import type { ProjectItem } from "../../types";

// Module-level flag: attempt auto-provision only once per session
let _autoProvisionAttempted = false;

/**
 * Auto-provision a default project + group for first-time users.
 * Silent operation — no toast on success.
 * Returns the created project on success, null on failure.
 */
async function autoProvision(): Promise<ProjectItem | null> {
  try {
    const projectRes = await axios.post<ProjectItem>(`${API_BASE}/projects`, {
      name: "내 채널",
    });
    try {
      await axios.post(`${API_BASE}/groups`, {
        project_id: projectRes.data.id,
        name: "기본 시리즈",
      });
    } catch {
      // Rollback: delete orphan project if group creation fails
      await axios.delete(`${API_BASE}/projects/${projectRes.data.id}`).catch(() => {});
      return null;
    }
    return projectRes.data;
  } catch (error) {
    console.error("[autoProvision] Failed:", error);
    return null;
  }
}

export async function fetchProjects(): Promise<void> {
  const { setContextLoading, setProjects, setContext } = useContextStore.getState();
  setContextLoading({ isLoadingProjects: true });
  try {
    let res = await axios.get<ProjectItem[]>(`${API_BASE}/projects`);

    // Auto-provision for first-time users (once per session)
    if (res.data.length === 0 && !_autoProvisionAttempted) {
      _autoProvisionAttempted = true;
      const newProject = await autoProvision();
      if (newProject) {
        res = await axios.get<ProjectItem[]>(`${API_BASE}/projects`);
        // Force-select the new project (overrides stale localStorage projectId)
        setContext({ projectId: newProject.id, groupId: null });
      }
    }

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
  const { showToast } = useUIStore.getState();
  try {
    const res = await axios.post<ProjectItem>(`${API_BASE}/projects`, data);
    await fetchProjects();
    showToast("채널 생성됨", "success");
    return res.data;
  } catch (error) {
    console.error("[createProject] Failed:", error);
    showToast("채널 생성 실패", "error");
    return undefined;
  }
}

export async function updateProject(
  projectId: number,
  data: {
    name?: string;
    description?: string;
    handle?: string;
    avatar_media_asset_id?: number | null;
  }
): Promise<ProjectItem | undefined> {
  const { showToast } = useUIStore.getState();
  try {
    const res = await axios.put<ProjectItem>(`${API_BASE}/projects/${projectId}`, data);
    await fetchProjects();
    showToast("채널 수정됨", "success");
    return res.data;
  } catch (error) {
    console.error("[updateProject] Failed:", error);
    showToast("채널 수정 실패", "error");
    return undefined;
  }
}

export async function deleteProject(projectId: number): Promise<boolean> {
  const { showToast } = useUIStore.getState();
  try {
    await axios.delete(`${API_BASE}/projects/${projectId}`);
    await fetchProjects();
    showToast("채널 삭제됨", "success");
    return true;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 409) {
      showToast("삭제 불가: 시리즈가 존재합니다", "error");
    } else {
      console.error("[deleteProject] Failed:", error);
      showToast("채널 삭제 실패", "error");
    }
    return false;
  }
}
