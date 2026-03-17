import axios from "axios";
import { useRenderStore } from "../useRenderStore";
import { useContextStore } from "../useContextStore";
import { useStoryboardStore } from "../useStoryboardStore";
import { useUIStore } from "../useUIStore";
import { API_BASE, ADMIN_API_BASE, DEFAULT_STRUCTURE } from "../../constants";
import { buildScenesPayload } from "../../utils/buildScenesPayload";

/** The subset of style profile fields used in the output slice. */
interface StyleProfileSelection {
  id: number;
  name: string;
  display_name: string | null;
  sd_model_name: string | null;
  loras?: { name: string; trigger_words: string[]; weight: number }[];
  negative_embeddings?: { name: string; trigger_word: string }[];
  positive_embeddings?: { name: string; trigger_word: string }[];
  default_positive?: string | null;
  default_negative?: string | null;
  default_enable_hr?: boolean | null;
  default_steps?: number | null;
  default_cfg_scale?: number | null;
  default_sampler_name?: string | null;
  default_clip_skip?: number | null;
}

interface StyleProfileCallbacks {
  setShowStyleProfileModal: (show: boolean) => void;
}

/**
 * Handle style profile selection from the StyleProfileModal.
 *
 * 1. Store profile in output slice
 * 2. Create or update storyboard via API
 * 3. Change SD model in background
 */
export async function handleStyleProfileComplete(
  profile: StyleProfileSelection,
  callbacks: StyleProfileCallbacks
): Promise<void> {
  const { showToast } = useUIStore.getState();
  const { groupId } = useContextStore.getState();
  const { setEffectiveDefaults } = useContextStore.getState();

  // 1. Store profile in output slice
  useRenderStore.getState().set({
    currentStyleProfile: {
      id: profile.id,
      name: profile.name,
      display_name: profile.display_name,
      sd_model_name: profile.sd_model_name,
      loras: profile.loras || [],
      negative_embeddings: profile.negative_embeddings || [],
      positive_embeddings: profile.positive_embeddings || [],
      default_positive: profile.default_positive || null,
      default_negative: profile.default_negative || null,
      default_steps: profile.default_steps ?? null,
      default_cfg_scale: profile.default_cfg_scale ?? null,
      default_sampler_name: profile.default_sampler_name ?? null,
      default_clip_skip: profile.default_clip_skip ?? null,
    },
  });
  callbacks.setShowStyleProfileModal(false);

  // Auto-enable Hi-Res from StyleProfile default
  if (profile.default_enable_hr) {
    useStoryboardStore.getState().set({ hiResEnabled: true });
  }

  // 2. Persist style_profile_id to Group (SSOT for generation)
  if (groupId) {
    try {
      await axios.put(`${API_BASE}/groups/${groupId}`, {
        style_profile_id: profile.id,
      });
      setEffectiveDefaults(profile.id, null, true);
    } catch (err) {
      console.error("[StyleProfile] Failed to update Group:", err);
      showToast("화풍이 로컬에 저장되었으나 시리즈 업데이트에 실패했습니다", "error");
    }
  }

  // 3. Create or update storyboard
  await saveStoryboardWithProfile(profile, showToast);

  // 4. Change SD model in background
  await changeSdModel(profile, showToast);
}

// --- Helper: Save/update storyboard with profile ---

async function saveStoryboardWithProfile(
  profile: StyleProfileSelection,
  showToast: (msg: string, type: "success" | "error") => void
) {
  const sbState = useStoryboardStore.getState();
  const ctxState = useContextStore.getState();
  const { scenes, topic, structure, selectedCharacterId, selectedCharacterBId, description } =
    sbState;
  const { storyboardId, groupId: currentGroupId } = ctxState;

  const validId =
    storyboardId && typeof storyboardId === "number" && !isNaN(storyboardId) && storyboardId > 0;

  const scenesPayload = buildScenesPayload(scenes);
  const commonPayload = {
    description: description || null,
    group_id: currentGroupId,
    structure: structure || DEFAULT_STRUCTURE,
    character_id: selectedCharacterId || undefined,
    character_b_id: selectedCharacterBId || undefined,
    scenes: scenesPayload,
  };

  if (validId) {
    await updateExistingStoryboard(storyboardId, profile, topic, commonPayload, showToast);
  } else {
    await createNewStoryboard(profile, topic, commonPayload, showToast);
  }
}

async function updateExistingStoryboard(
  storyboardId: number,
  profile: StyleProfileSelection,
  topic: string,
  payload: Record<string, unknown>,
  showToast: (msg: string, type: "success" | "error") => void
) {
  try {
    await axios.put(`${API_BASE}/storyboards/${storyboardId}`, {
      title: topic || "Untitled",
      ...payload,
    });
    showToast("영상 업데이트 완료", "success");
  } catch (err) {
    console.error("[StyleProfileModal] Failed to update storyboard:", err);
    showToast("영상 업데이트에 실패했습니다", "error");
  }
}

async function createNewStoryboard(
  profile: StyleProfileSelection,
  topic: string,
  payload: Record<string, unknown>,
  showToast: (msg: string, type: "success" | "error") => void
) {
  try {
    const res = await axios.post(`${API_BASE}/storyboards`, {
      title: topic || "Draft Storyboard",
      ...payload,
    });
    useContextStore.getState().setContext({ storyboardId: res.data.storyboard_id });
    showToast("영상 생성 완료", "success");
  } catch (err) {
    console.error("[StyleProfileModal] Failed to create storyboard:", err);
    showToast("영상 생성에 실패했습니다: " + (err as Error).message, "error");
  }
}

/**
 * Load a style profile by ID and apply it to the store.
 * Shared by useStudioInitialization (DB load) and useStudioOnboarding (cascade default).
 * Deduplicates concurrent calls for the same profileId (async race condition guard).
 */
let _loadingProfileId: number | null = null;

export async function loadStyleProfileFromId(
  profileId: number,
  options?: { skipHiResSync?: boolean }
): Promise<void> {
  if (_loadingProfileId === profileId) return;
  _loadingProfileId = profileId;

  try {
    const { showToast } = useUIStore.getState();
    const res = await axios.get(`${API_BASE}/style-profiles/${profileId}/full`);
    const profile = res.data;

    useRenderStore.getState().set({
      currentStyleProfile: {
        id: profile.id,
        name: profile.name,
        display_name: profile.display_name,
        sd_model_name: profile.sd_model?.name || profile.sd_model?.display_name || null,
        loras: profile.loras || [],
        negative_embeddings: profile.negative_embeddings || [],
        positive_embeddings: profile.positive_embeddings || [],
        default_positive: profile.default_positive,
        default_negative: profile.default_negative,
        default_steps: profile.default_steps ?? null,
        default_cfg_scale: profile.default_cfg_scale ?? null,
        default_sampler_name: profile.default_sampler_name ?? null,
        default_clip_skip: profile.default_clip_skip ?? null,
      },
    });

    // Sync Hi-Res toggle from StyleProfile default (skip during DB storyboard reload)
    if (!options?.skipHiResSync) {
      useStoryboardStore.getState().set({ hiResEnabled: !!profile.default_enable_hr });
    }

    // Fire-and-forget: don't block profile loading on SD model switch
    changeSdModel(
      {
        ...profile,
        sd_model_name: profile.sd_model?.name || null,
      },
      showToast
    );
  } finally {
    _loadingProfileId = null;
  }
}

// --- Helper: Change SD model in background ---

let _lastSdModel: string | null = null;

async function changeSdModel(
  profile: StyleProfileSelection,
  showToast: (msg: string, type: "success" | "error") => void
) {
  const profileLabel = profile.display_name || profile.name;
  if (!profile.sd_model_name) {
    showToast(`화풍 "${profileLabel}" 선택됨`, "success");
    return;
  }

  // Skip if same model is already loaded
  if (_lastSdModel === profile.sd_model_name) {
    showToast(`화풍 "${profileLabel}" 로드됨 (모델 변경 없음)`, "success");
    return;
  }

  try {
    await axios.post(`${ADMIN_API_BASE}/sd/options`, {
      sd_model_checkpoint: profile.sd_model_name,
    });
    _lastSdModel = profile.sd_model_name;
    showToast(
      `화풍 "${profileLabel}" 로드됨\n` +
        `모델: ${profile.sd_model_name}\n` +
        `LoRA: ${profile.loras?.length || 0}\n` +
        `임베딩: ${(profile.negative_embeddings?.length || 0) + (profile.positive_embeddings?.length || 0)}`,
      "success"
    );
  } catch (err) {
    console.error("Failed to change SD model:", err);
    showToast(`화풍 로드됨, 모델 변경 실패: ${profile.sd_model_name}`, "error");
  }
}
