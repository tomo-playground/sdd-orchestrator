"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import axios from "axios";
import { useStudioStore, resetStudioStore } from "../store/useStudioStore";
import { loadStyleProfileFromId } from "../store/actions/styleProfileActions";
import { createDraftStoryboard } from "../store/actions/storyboardActions";
import type { Scene } from "../types";
import { API_BASE, PROMPT_APPLY_KEY } from "../constants";

/**
 * Handles all studio initialization logic:
 * - Store reset on ?new=true
 * - Storyboard loading from DB on ?id=X
 * - Prompt apply from localStorage
 * - Channel avatar URL loading
 * - Transient data clearing on storyboard ID change
 */
export function useStudioInitialization() {
  const searchParams = useSearchParams();
  const storyboardId = searchParams.get("id");
  const [isLoadingDb, setIsLoadingDb] = useState(false);
  const [loadedProfileId, setLoadedProfileId] = useState<number | null>(null);
  const [needsStyleProfile, setNeedsStyleProfile] = useState(false);

  const setMeta = useStudioStore((s) => s.setMeta);
  const setScenes = useStudioStore((s) => s.setScenes);
  const setPlan = useStudioStore((s) => s.setPlan);
  const channelProfile = useStudioStore((s) => s.channelProfile);
  const setChannelAvatarUrl = useStudioStore((s) => s.setChannelAvatarUrl);

  // Reset store and create draft DB storyboard for ?new=true
  const draftCreatedRef = useRef(false);

  useEffect(() => {
    const isNewStoryboard = searchParams.get("new") === "true";
    if (!isNewStoryboard || draftCreatedRef.current) return;
    draftCreatedRef.current = true;

    resetStudioStore();
    const { effectiveCharacterId } = useStudioStore.getState();
    if (effectiveCharacterId) {
      setPlan({ selectedCharacterId: effectiveCharacterId });
    }

    // Clear URL params first (prevents searchParams re-trigger)
    const url = new URL(window.location.href);
    url.searchParams.delete("new");
    url.searchParams.delete("id");
    window.history.replaceState({}, "", url.toString());

    // Create draft storyboard in DB (async IIFE)
    (async () => {
      const newId = await createDraftStoryboard();
      if (newId) {
        const u = new URL(window.location.href);
        u.searchParams.set("id", String(newId));
        window.history.replaceState({}, "", u.toString());
      }
    })();
  }, [searchParams, setPlan]);

  // Clear transient data when storyboard ID changes
  useEffect(() => {
    if (storyboardId) {
      useStudioStore.getState().setOutput({
        videoUrl: null,
        videoUrlFull: null,
        videoUrlPost: null,
        recentVideos: [],
      });
    }
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
      if (data.steps) plan.baseStepsA = data.steps;
      if (data.cfg_scale) plan.baseCfgScaleA = data.cfg_scale;
      if (data.sampler_name) plan.baseSamplerA = data.sampler_name;
      if (data.seed) plan.baseSeedA = data.seed;
      if (data.clip_skip) plan.baseClipSkipA = data.clip_skip;
      setPlan(plan);

      const {
        scenes: sc,
        currentSceneIndex: idx,
        updateScene,
      } = useStudioStore.getState();
      if (sc.length > 0 && sc[idx]) {
        const updates: Partial<Scene> = {};
        if (data.positive_prompt) updates.image_prompt = data.positive_prompt as string;
        if (data.negative_prompt) updates.negative_prompt = data.negative_prompt as string;
        if (data.steps) updates.steps = data.steps as number;
        if (data.cfg_scale) updates.cfg_scale = data.cfg_scale as number;
        if (data.sampler_name) updates.sampler_name = data.sampler_name as string;
        if (data.seed) updates.seed = data.seed as number;
        if (data.clip_skip) updates.clip_skip = data.clip_skip as number;
        if (data.context_tags)
          updates.context_tags = data.context_tags as Record<string, string[]>;
        if (data.id) updates.prompt_history_id = data.id as number;
        updateScene(sc[idx].id, updates);
      }
      window.localStorage.removeItem(PROMPT_APPLY_KEY);
      useStudioStore.getState().showToast("Prompt applied!", "success");
    } catch {
      window.localStorage.removeItem(PROMPT_APPLY_KEY);
    }
  }, [setPlan]);

  // Load channel avatar URL when profile changes
  useEffect(() => {
    if (!channelProfile?.avatar_key) {
      setChannelAvatarUrl(null);
      return;
    }
    const url = `${API_BASE}/controlnet/ip-adapter/reference/${channelProfile.avatar_key}/image?t=${Date.now()}`;
    setChannelAvatarUrl(url);
  }, [channelProfile?.avatar_key, setChannelAvatarUrl]);

  // Load storyboard from DB if ?id=X
  useEffect(() => {
    if (!storyboardId) return;
    const id = parseInt(storyboardId, 10);
    if (isNaN(id)) return;

    setIsLoadingDb(true);
    axios
      .get(`${API_BASE}/storyboards/${id}`)
      .then((res) => {
        const data = res.data;
        setMeta({
          storyboardId: data.id,
          storyboardTitle: data.title,
          activeTab: data.scenes?.length > 0 ? "scenes" : "plan",
        });
        useStudioStore.getState().setOutput({
          videoUrl: data.video_url || null,
          videoUrlFull: data.video_url || null,
          recentVideos: data.recent_videos || [],
          videoCaption: data.default_caption || "",
        });
        setPlan({
          selectedCharacterId: data.default_character_id || null,
          topic: data.description || "",
        });

        if (data.default_character_id) {
          loadCharacterData(data.default_character_id, setPlan);
        }

        if (data.default_style_profile_id) {
          setLoadedProfileId(data.default_style_profile_id);
          loadStyleProfileFromId(data.default_style_profile_id);
        } else {
          setLoadedProfileId(null);
          setNeedsStyleProfile(true);
        }

        if (data.scenes?.length > 0) {
          const mapped = mapDbScenes(data.scenes);
          setScenes(mapped);
        }
      })
      .catch(() => {
        setMeta({ storyboardId: null });
      })
      .finally(() => setIsLoadingDb(false));
  }, [storyboardId, setMeta, setPlan, setScenes]);

  return {
    isLoadingDb,
    loadedProfileId,
    loadStyleProfileFromId,
    storyboardId,
    needsStyleProfile,
  };
}

// --- Helper: Load character data ---
async function loadCharacterData(
  characterId: number,
  setPlan: (updates: Record<string, unknown>) => void
) {
  try {
    const charRes = await axios.get(`${API_BASE}/characters/${characterId}`);
    const char = charRes.data;
    setPlan({
      characterLoras: char.loras || [],
      characterPromptMode: char.prompt_mode || "auto",
      basePromptA: char.base_prompt || "",
      baseNegativePromptA: char.base_negative || "",
    });
  } catch (err) {
    console.error("Failed to load character:", err);
  }
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
    steps: (s.steps as number) || 27,
    cfg_scale: (s.cfg_scale as number) || 7,
    sampler_name: (s.sampler_name as string) || "DPM++ 2M Karras",
    seed: (s.seed as number) || -1,
    clip_skip: (s.clip_skip as number) || 2,
    isGenerating: false,
    debug_payload: "",
    context_tags: (s.context_tags as Record<string, string[]>) || undefined,
    environment_reference_id: (s.environment_reference_id as number) || null,
    environment_reference_weight:
      (s.environment_reference_weight as number) || undefined,
    use_reference_only: (s.use_reference_only as boolean) || undefined,
    reference_only_weight: (s.reference_only_weight as number) || undefined,
  }));
}
