import axios from "axios";
import { useStudioStore } from "../useStudioStore";
import { API_BASE } from "../../constants";
import type { GroupItem } from "../../types";

/**
 * Load group render defaults from nested render_preset and apply to output slice.
 * Called on initial load or when the active group changes.
 */
export async function loadGroupDefaults(groupId: number): Promise<void> {
  try {
    const res = await axios.get(`${API_BASE}/groups/${groupId}`);
    const p = res.data.render_preset;
    if (!p) return;

    const updates: Record<string, unknown> = {};
    if (p.narrator_voice) updates.narratorVoice = p.narrator_voice;
    if (p.bgm_file) updates.bgmFile = p.bgm_file;
    if (p.bgm_volume != null) updates.bgmVolume = p.bgm_volume;
    if (p.audio_ducking != null) updates.audioDucking = p.audio_ducking;
    if (p.scene_text_font) updates.sceneTextFont = p.scene_text_font;
    if (p.layout_style) updates.layoutStyle = p.layout_style;
    if (p.frame_style) updates.frameStyle = p.frame_style;
    if (p.transition_type) updates.transitionType = p.transition_type;
    if (p.ken_burns_preset) updates.kenBurnsPreset = p.ken_burns_preset;
    if (p.ken_burns_intensity != null) updates.kenBurnsIntensity = p.ken_burns_intensity;
    if (p.speed_multiplier != null) updates.speedMultiplier = p.speed_multiplier;

    if (Object.keys(updates).length > 0) {
      useStudioStore.getState().setOutput(updates);
    }
  } catch {
    // Group defaults are optional; silently ignore failures
  }
}

export async function fetchGroups(projectId: number): Promise<void> {
  const { setContextLoading, setGroups } = useStudioStore.getState();
  setContextLoading({ isLoadingGroups: true });
  try {
    const res = await axios.get<GroupItem[]>(`${API_BASE}/groups`, {
      params: { project_id: projectId },
    });
    setGroups(res.data);
  } catch (error) {
    console.error("[fetchGroups] Failed:", error);
  } finally {
    setContextLoading({ isLoadingGroups: false });
  }
}

export async function createGroup(data: {
  project_id: number;
  name: string;
  description?: string;
  render_preset_id?: number;
}): Promise<GroupItem | undefined> {
  const { showToast, projectId } = useStudioStore.getState();
  try {
    const res = await axios.post<GroupItem>(`${API_BASE}/groups`, data);
    if (projectId) await fetchGroups(projectId);
    showToast("Group created", "success");
    return res.data;
  } catch (error) {
    console.error("[createGroup] Failed:", error);
    showToast("Failed to create group", "error");
    return undefined;
  }
}

export async function updateGroup(
  groupId: number,
  data: Record<string, unknown>,
): Promise<GroupItem | undefined> {
  const { showToast, projectId } = useStudioStore.getState();
  try {
    const res = await axios.put<GroupItem>(`${API_BASE}/groups/${groupId}`, data);
    if (projectId) await fetchGroups(projectId);
    showToast("Group updated", "success");
    return res.data;
  } catch (error) {
    console.error("[updateGroup] Failed:", error);
    showToast("Failed to update group", "error");
    return undefined;
  }
}

export async function deleteGroup(groupId: number): Promise<boolean> {
  const { showToast, projectId } = useStudioStore.getState();
  try {
    await axios.delete(`${API_BASE}/groups/${groupId}`);
    if (projectId) await fetchGroups(projectId);
    showToast("Group deleted", "success");
    return true;
  } catch (error) {
    console.error("[deleteGroup] Failed:", error);
    showToast("Failed to delete group", "error");
    return false;
  }
}
