"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import axios from "axios";
import { resetAllStores } from "../store/resetAllStores";
import { useContextStore } from "../store/useContextStore";
import { useStoryboardStore } from "../store/useStoryboardStore";
import { useRenderStore } from "../store/useRenderStore";
import { useUIStore } from "../store/useUIStore";
import { loadStyleProfileFromId } from "../store/actions/styleProfileActions";
import { initializeVideoMetadata } from "../store/actions/outputActions";
import { loadGroupDefaults } from "../store/actions/groupActions";
import type { Scene } from "../types";
import { API_BASE, DEFAULT_STRUCTURE, PROMPT_APPLY_KEY } from "../constants";

/**
 * Handles all studio initialization logic:
 * - Store reset on ?new=true
 * - Storyboard loading from DB on ?id=X
 * - Prompt apply from localStorage
 * - Transient data clearing on storyboard ID change
 */
export function useStudioInitialization() {
  const searchParams = useSearchParams();
  const storyboardId = searchParams.get("id");
  const [isLoadingDb, setIsLoadingDb] = useState(false);
  const [loadedProfileId, setLoadedProfileId] = useState<number | null>(null);
  const [needsStyleProfile, setNeedsStyleProfile] = useState(false);

  const setContext = useContextStore((s) => s.setContext);
  const setScenes = useStoryboardStore((s) => s.setScenes);
  const setPlan = useStoryboardStore((s) => s.set);

  // Reset store for ?new=true (DB creation deferred to first save/generate)
  const newHandledRef = useRef(false);

  useEffect(() => {
    const isNewStoryboard = searchParams.get("new") === "true";
    if (!isNewStoryboard) {
      newHandledRef.current = false;
      return;
    }
    if (newHandledRef.current) return;
    newHandledRef.current = true;

    // Async IIFE to handle resetAllStores (now async)
    (async () => {
      await resetAllStores();
      const { effectiveCharacterId } = useContextStore.getState();
      if (effectiveCharacterId) {
        setPlan({ selectedCharacterId: effectiveCharacterId });
      }

      // Clear URL params (prevents searchParams re-trigger)
      const url = new URL(window.location.href);
      url.searchParams.delete("new");
      url.searchParams.delete("id");
      window.history.replaceState({}, "", url.toString());
    })();
  }, [searchParams, setPlan]);

  // Clear transient data when switching between storyboards (not on initial mount)
  const prevStoryboardIdRef = useRef<string | null>(null);
  useEffect(() => {
    if (
      storyboardId &&
      prevStoryboardIdRef.current &&
      prevStoryboardIdRef.current !== storyboardId
    ) {
      useRenderStore.getState().set({
        videoUrl: null,
        videoUrlFull: null,
        videoUrlPost: null,
        recentVideos: [],
      });
    }
    prevStoryboardIdRef.current = storyboardId;
  }, [storyboardId]);

  // Apply prompt from localStorage (from /manage Prompts tab)
  useEffect(() => {
    const stored = window.localStorage.getItem(PROMPT_APPLY_KEY);
    if (!stored) return;
    try {
      const data = JSON.parse(stored) as Record<string, unknown>;
      const plan: Record<string, unknown> = {};
      if (data.positive_prompt) plan.basePromptA = data.positive_prompt;
      if (data.negative_prompt) plan.baseNegativePromptA = data.negative_prompt;
      setPlan(plan);

      const { scenes: sc, currentSceneIndex: idx, updateScene } = useStoryboardStore.getState();
      if (sc.length > 0 && sc[idx]) {
        const updates: Partial<Scene> = {};
        if (data.positive_prompt) updates.image_prompt = data.positive_prompt as string;
        if (data.negative_prompt) updates.negative_prompt = data.negative_prompt as string;
        if (data.context_tags) updates.context_tags = data.context_tags as Record<string, string[]>;
        if (data.id) updates.prompt_history_id = data.id as number;
        updateScene(sc[idx].id, updates);
      }
      window.localStorage.removeItem(PROMPT_APPLY_KEY);
      useUIStore.getState().showToast("Prompt applied!", "success");
    } catch {
      window.localStorage.removeItem(PROMPT_APPLY_KEY);
    }
  }, [setPlan]);

  // Load storyboard from DB if ?id=X
  useEffect(() => {
    if (!storyboardId) return;
    const id = parseInt(storyboardId, 10);
    if (isNaN(id)) return;

    setIsLoadingDb(true); // eslint-disable-line react-hooks/set-state-in-effect
    axios
      .get(`${API_BASE}/storyboards/${id}`)
      .then((res) => {
        const data = res.data;
        // Sync groupId and projectId from storyboard response
        const groupId = data.group_id ?? null;
        const projectId = data.project_id ?? null;
        setContext({
          storyboardId: data.id,
          storyboardTitle: data.title,
          ...(groupId ? { groupId } : {}),
          ...(projectId ? { projectId } : {}),
        });
        // Restore video data from DB, mapping label to correct slot
        const recentVideos = data.recent_videos || [];
        const latestFull = recentVideos.find((v: { label?: string }) => v.label === "full");
        const latestPost = recentVideos.find((v: { label?: string }) => v.label === "post");
        useRenderStore.getState().set({
          videoUrl: data.video_url || null,
          videoUrlFull: latestFull?.url || data.video_url || null,
          videoUrlPost: latestPost?.url || null,
          recentVideos,
          videoCaption: data.caption || "",
        });
        setPlan({
          selectedCharacterId: data.character_id || null,
          selectedCharacterBId: data.character_b_id || null,
          structure: data.structure || DEFAULT_STRUCTURE,
          topic: data.title || "",
          description: data.description || "",
          ...(data.duration != null && { duration: data.duration }),
          ...(data.language != null && { language: data.language }),
        });

        if (data.character_id) {
          loadCharacterData(data.character_id, setPlan);
        }
        if (data.character_b_id) {
          loadCharacterBData(data.character_b_id, setPlan);
        }

        if (data.style_profile_id) {
          setLoadedProfileId(data.style_profile_id);
          loadStyleProfileFromId(data.style_profile_id);
        } else {
          setLoadedProfileId(null);
          setNeedsStyleProfile(true);
        }

        if (data.scenes?.length > 0) {
          const mapped = mapDbScenes(data.scenes);
          setScenes(mapped);
        }

        // Initialize video metadata (caption/likes) once topic is set
        initializeVideoMetadata(data.title || "");

        // Load group render defaults (bgmFile, speedMultiplier, voicePresetId, etc.)
        // Skip content defaults (structure/language/duration) since storyboard already has them
        if (groupId) {
          loadGroupDefaults(groupId, { skipContentDefaults: true });
        }
      })
      .catch(async (err) => {
        if (err?.response?.status === 404) {
          await resetAllStores();
          useUIStore.getState().showToast("삭제되었거나 존재하지 않는 스토리보드입니다.", "error");
          const url = new URL(window.location.href);
          url.searchParams.delete("id");
          window.history.replaceState({}, "", url.toString());
        } else {
          setContext({ storyboardId: null });
        }
      })
      .finally(() => setIsLoadingDb(false));
  }, [storyboardId, setContext, setPlan, setScenes]);

  return {
    isLoadingDb,
    loadedProfileId,
    loadStyleProfileFromId,
    storyboardId,
    needsStyleProfile,
  };
}

// --- Helper: Load character data (A or B) ---
type CharacterFieldMap = {
  loras: string;
  promptMode?: string;
  basePrompt: string;
  baseNegative: string;
};

const CHAR_A_FIELDS: CharacterFieldMap = {
  loras: "characterLoras",
  promptMode: "characterPromptMode",
  basePrompt: "basePromptA",
  baseNegative: "baseNegativePromptA",
};

const CHAR_B_FIELDS: CharacterFieldMap = {
  loras: "characterBLoras",
  basePrompt: "basePromptB",
  baseNegative: "baseNegativePromptB",
};

async function loadCharacterForRole(
  characterId: number,
  fields: CharacterFieldMap,
  setPlan: (updates: Record<string, unknown>) => void
) {
  try {
    const charRes = await axios.get(`${API_BASE}/characters/${characterId}`);
    const char = charRes.data;
    const updates: Record<string, unknown> = {
      [fields.loras]: char.loras || [],
      [fields.basePrompt]: char.base_prompt || "",
      [fields.baseNegative]: char.base_negative || "",
    };
    if (fields.promptMode) {
      updates[fields.promptMode] = char.prompt_mode || "auto";
    }
    setPlan(updates);
  } catch (err) {
    console.error(`Failed to load character (${fields.basePrompt}):`, err);
  }
}

function loadCharacterData(
  characterId: number,
  setPlan: (updates: Record<string, unknown>) => void
) {
  return loadCharacterForRole(characterId, CHAR_A_FIELDS, setPlan);
}

function loadCharacterBData(
  characterId: number,
  setPlan: (updates: Record<string, unknown>) => void
) {
  return loadCharacterForRole(characterId, CHAR_B_FIELDS, setPlan);
}

// --- Helper: Map DB scenes to frontend Scene type ---
function mapDbScenes(dbScenes: Record<string, unknown>[]): Scene[] {
  return dbScenes.map((s, i) => ({
    id: (s.id as number) || i,
    order: (s.order as number) ?? (s.scene_id as number) ?? i,
    script: (s.script as string) || "",
    speaker: ((s.speaker as string) || "Narrator") as Scene["speaker"],
    duration: (s.duration as number) || 3,
    image_prompt: (s.image_prompt as string) || "",
    image_prompt_ko: (s.image_prompt_ko as string) || "",
    image_url: (s.image_url as string) || null,
    image_asset_id: (s.image_asset_id as number) || null,
    description: (s.description as string) || "",
    width: (s.width as number) || 512,
    height: (s.height as number) || 768,
    candidates: (s.candidates as Scene["candidates"]) || undefined,
    negative_prompt: (s.negative_prompt as string) || "",
    isGenerating: false,
    debug_payload: "",
    context_tags: (s.context_tags as Record<string, string[]>) || undefined,
    environment_reference_id: (s.environment_reference_id as number) || null,
    environment_reference_weight: (s.environment_reference_weight as number) || undefined,
    use_reference_only: (s.use_reference_only as boolean) || undefined,
    reference_only_weight: (s.reference_only_weight as number) || undefined,
    // Per-scene generation settings override (null = inherit global)
    use_controlnet: (s.use_controlnet as boolean | null) ?? null,
    controlnet_weight: (s.controlnet_weight as number | null) ?? null,
    use_ip_adapter: (s.use_ip_adapter as boolean | null) ?? null,
    ip_adapter_reference: (s.ip_adapter_reference as string | null) ?? null,
    ip_adapter_weight: (s.ip_adapter_weight as number | null) ?? null,
    multi_gen_enabled: (s.multi_gen_enabled as boolean | null) ?? null,
    _auto_pin_previous: (s._auto_pin_previous as boolean) ?? false,
    character_actions: (s.character_actions as Scene["character_actions"]) || undefined,
  }));
}
