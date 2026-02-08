import axios from "axios";
import { useStudioStore } from "../useStudioStore";
import { API_BASE } from "../../constants";

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
  const { setOutput, showToast, setMeta, groupId, setEffectiveDefaults } =
    useStudioStore.getState();

  // 1. Store profile in output slice
  console.log("[StyleProfileModal] Selected profile:", profile);
  setOutput({
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
  await saveStoryboardWithProfile(profile, setMeta, showToast);

  // 4. Change SD model in background
  await changeSdModel(profile, showToast);
}

// --- Helper: Save/update storyboard with profile ---

async function saveStoryboardWithProfile(
  profile: StyleProfileSelection,
  setMeta: (updates: Record<string, unknown>) => void,
  showToast: (msg: string, type: "success" | "error") => void
) {
  const { storyboardId, scenes, topic, selectedCharacterId } = useStudioStore.getState();

  const validId =
    storyboardId && typeof storyboardId === "number" && !isNaN(storyboardId) && storyboardId > 0;

  const scenesPayload = buildScenesPayload(scenes);

  if (validId) {
    await updateExistingStoryboard(
      storyboardId,
      profile,
      scenesPayload,
      topic,
      selectedCharacterId,
      showToast
    );
  } else {
    await createNewStoryboard(
      profile,
      scenesPayload,
      topic,
      selectedCharacterId,
      setMeta,
      showToast
    );
  }
}

function buildScenesPayload(scenes: ReturnType<typeof useStudioStore.getState>["scenes"]) {
  return scenes.map((s, i) => ({
    scene_id: i,
    script: s.script,
    speaker: s.speaker,
    duration: s.duration,
    image_prompt: s.image_prompt,
    image_prompt_ko: s.image_prompt_ko,
    image_url: s.image_asset_id ? null : s.image_url,
    description: s.description,
    width: s.width || 512,
    height: s.height || 768,
    negative_prompt: s.negative_prompt,
    context_tags: s.context_tags,
  }));
}

async function updateExistingStoryboard(
  storyboardId: number,
  profile: StyleProfileSelection,
  scenesPayload: ReturnType<typeof buildScenesPayload>,
  topic: string,
  selectedCharacterId: number | null,
  showToast: (msg: string, type: "success" | "error") => void
) {
  try {
    await axios.put(`${API_BASE}/storyboards/${storyboardId}`, {
      title: topic || "Untitled",
      description: useStudioStore.getState().description || null,
      character_id: selectedCharacterId,
      scenes: scenesPayload,
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
  scenesPayload: ReturnType<typeof buildScenesPayload>,
  topic: string,
  selectedCharacterId: number | null,
  setMeta: (updates: Record<string, unknown>) => void,
  showToast: (msg: string, type: "success" | "error") => void
) {
  try {
    const res = await axios.post(`${API_BASE}/storyboards`, {
      title: topic || "Draft Storyboard",
      description: useStudioStore.getState().description || null,
      character_id: selectedCharacterId,
      scenes: scenesPayload,
    });
    setMeta({ storyboardId: res.data.storyboard_id });
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
  const { setOutput, showToast } = useStudioStore.getState();
  const res = await axios.get(`${API_BASE}/style-profiles/${profileId}/full`);
  const profile = res.data;

  setOutput({
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
