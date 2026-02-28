import axios from "axios";
import { useContextStore } from "../useContextStore";
import { useRenderStore } from "../useRenderStore";
import { useUIStore } from "../useUIStore";
import { API_BASE } from "../../constants";
import type { EffectiveConfig, GroupItem } from "../../types";
import { loadStyleProfileFromId } from "./styleProfileActions";

/**
 * Load effective config (cascading: Project < Group) and apply to output slice.
 * Called on initial load or when the active group changes.
 */
export async function loadGroupDefaults(
  groupId: number,
  options?: { skipStyleProfile?: boolean }
): Promise<void> {
  const { setEffectiveDefaults, setEffectivePreset } = useContextStore.getState();
  setEffectiveDefaults(null, null, false);

  try {
    const res = await axios.get<EffectiveConfig>(`${API_BASE}/groups/${groupId}/effective-config`);
    const cfg = res.data;

    // Store effective IDs (survives store reset)
    setEffectiveDefaults(cfg.style_profile_id ?? null, null, true);

    // Auto-load style profile if not already loaded (skip if caller already loaded it)
    if (
      cfg.style_profile_id &&
      !options?.skipStyleProfile &&
      !useRenderStore.getState().currentStyleProfile
    ) {
      loadStyleProfileFromId(cfg.style_profile_id, { skipHiResSync: true }).catch((err) => {
        console.error("[loadGroupDefaults] Failed to load style profile:", err);
      });
    }

    const p = cfg.render_preset;
    if (!p) {
      setEffectivePreset(null, null);
      return;
    }
    setEffectivePreset(p.name, cfg.sources?.render_preset_id || "group");

    const updates: Record<string, unknown> = {};
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
    if (p.bgm_mode) {
      const mode = p.bgm_mode === "file" || p.bgm_mode === "ai" ? "manual" : p.bgm_mode;
      updates.bgmMode = mode;
    }
    if (p.music_preset_id != null) updates.musicPresetId = p.music_preset_id;

    // narrator_voice_preset_id from Group
    if (cfg.narrator_voice_preset_id != null) updates.voicePresetId = cfg.narrator_voice_preset_id;

    if (Object.keys(updates).length > 0) {
      useRenderStore.getState().set(updates);
    }
  } catch {
    setEffectiveDefaults(null, null, true);
  }
}

export async function fetchGroups(projectId: number): Promise<void> {
  const { setContextLoading, setGroups } = useContextStore.getState();
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
  style_profile_id?: number;
  narrator_voice_preset_id?: number;
}): Promise<GroupItem | undefined> {
  const { showToast } = useUIStore.getState();
  const { projectId } = useContextStore.getState();
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
  data: Record<string, unknown>
): Promise<GroupItem | undefined> {
  const { showToast } = useUIStore.getState();
  const { projectId } = useContextStore.getState();
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
  const { showToast } = useUIStore.getState();
  const { projectId } = useContextStore.getState();
  try {
    await axios.delete(`${API_BASE}/groups/${groupId}`);
    if (projectId) await fetchGroups(projectId);
    showToast("Group deleted", "success");
    return true;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 409) {
      showToast("Cannot delete: group has storyboards", "error");
    } else {
      console.error("[deleteGroup] Failed:", error);
      showToast("Failed to delete group", "error");
    }
    return false;
  }
}
