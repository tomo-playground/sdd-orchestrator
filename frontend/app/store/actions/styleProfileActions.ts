import axios from "axios";
import { useRenderStore } from "../useRenderStore";
import { useContextStore } from "../useContextStore";
import { useStoryboardStore } from "../useStoryboardStore";
import { useUIStore } from "../useUIStore";
import { API_BASE, DEFAULT_STRUCTURE } from "../../constants";
import { sanitizeCandidatesForDb } from "./storyboardActions";
import type { Scene } from "../../types";

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
  console.log("[StyleProfileModal] Selected profile:", profile);
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
    },
  });
  callbacks.setShowStyleProfileModal(false);

  // 2. Persist style_profile_id to GroupConfig (SSOT for generation)
  if (groupId) {
    try {
      await axios.put(`${API_BASE}/groups/${groupId}/config`, {
        style_profile_id: profile.id,
      });
      setEffectiveDefaults(profile.id, null, true);
      console.log("[StyleProfile] GroupConfig updated with style_profile_id:", profile.id);
    } catch (err) {
      console.error("[StyleProfile] Failed to update GroupConfig:", err);
      showToast("Style saved locally but GroupConfig update failed", "error");
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

function buildScenesPayload(scenes: Scene[]) {
  return scenes.map((s, i) => ({
    scene_id: i,
    script: s.script,
    speaker: s.speaker,
    duration: s.duration,
    image_prompt: s.image_prompt,
    image_prompt_ko: s.image_prompt_ko,
    description: s.description,
    width: s.width || 512,
    height: s.height || 768,
    negative_prompt: s.negative_prompt,
    context_tags: s.context_tags,
    image_asset_id: s.image_asset_id ?? null,
    environment_reference_id: s.environment_reference_id ?? null,
    environment_reference_weight: s.environment_reference_weight ?? 0.3,
    use_reference_only: s.use_reference_only ?? true,
    reference_only_weight: s.reference_only_weight ?? 0.5,
    candidates: sanitizeCandidatesForDb(s.candidates),
    // Per-scene generation settings override
    use_controlnet: s.use_controlnet ?? null,
    controlnet_weight: s.controlnet_weight ?? null,
    use_ip_adapter: s.use_ip_adapter ?? null,
    ip_adapter_reference: s.ip_adapter_reference ?? null,
    ip_adapter_weight: s.ip_adapter_weight ?? null,
    multi_gen_enabled: s.multi_gen_enabled ?? null,
  }));
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
    console.log("[StyleProfileModal] Storyboard updated with profile ID:", profile.id);
    showToast("Storyboard updated", "success");
  } catch (err) {
    console.error("[StyleProfileModal] Failed to update storyboard:", err);
    showToast("Storyboard update failed", "error");
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
    console.log(
      "[StyleProfileModal] Storyboard created with ID:",
      res.data.storyboard_id,
      "profile ID:",
      profile.id
    );
    showToast("Storyboard created", "success");
  } catch (err) {
    console.error("[StyleProfileModal] Failed to create storyboard:", err);
    showToast("Storyboard creation failed: " + (err as Error).message, "error");
  }
}

/**
 * Load a style profile by ID and apply it to the store.
 * Shared by useStudioInitialization (DB load) and useStudioOnboarding (cascade default).
 */
export async function loadStyleProfileFromId(profileId: number): Promise<void> {
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
    },
  });

  await changeSdModel(
    {
      ...profile,
      sd_model_name: profile.sd_model?.name || null,
    },
    showToast
  );
}

// --- Helper: Change SD model in background ---

async function changeSdModel(
  profile: StyleProfileSelection,
  showToast: (msg: string, type: "success" | "error") => void
) {
  if (profile.sd_model_name) {
    try {
      await axios.post(`${API_BASE}/sd/options`, {
        sd_model_checkpoint: profile.sd_model_name,
      });
      showToast(
        `Style profile "${profile.display_name || profile.name}" loaded\n` +
          `Model: ${profile.sd_model_name}\n` +
          `LoRAs: ${profile.loras?.length || 0}\n` +
          `Embeddings: ${(profile.negative_embeddings?.length || 0) + (profile.positive_embeddings?.length || 0)}`,
        "success"
      );
    } catch (err) {
      console.error("Failed to change SD model:", err);
      showToast(`Profile loaded but model change failed: ${profile.sd_model_name}`, "error");
    }
  } else {
    showToast(`Style profile "${profile.display_name || profile.name}" selected`, "success");
  }
}
