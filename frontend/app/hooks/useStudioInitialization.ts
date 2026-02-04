"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import axios from "axios";
import { useStudioStore, resetStudioStore } from "../store/useStudioStore";
import { loadStyleProfileFromId } from "../store/actions/styleProfileActions";
import { initializeVideoMetadata } from "../store/actions/outputActions";
import type { Scene } from "../types";
import { API_BASE, PROMPT_APPLY_KEY } from "../constants";
import { updateProject } from "../store/actions/projectActions";

/**
 * Handles all studio initialization logic:
 * - Store reset on ?new=true
 * - Storyboard loading from DB on ?id=X
 * - Prompt apply from localStorage
 * - One-time channelProfile → Project migration
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

    resetStudioStore();
    const { effectiveCharacterId } = useStudioStore.getState();
    if (effectiveCharacterId) {
      setPlan({ selectedCharacterId: effectiveCharacterId });
    }

    const storyTitle = searchParams.get("title") || undefined;
    if (storyTitle) {
      setPlan({ topic: storyTitle });
    }

    // Clear URL params (prevents searchParams re-trigger)
    const url = new URL(window.location.href);
    url.searchParams.delete("new");
    url.searchParams.delete("title");
    url.searchParams.delete("id");
    window.history.replaceState({}, "", url.toString());
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
      setPlan(plan);

      const { scenes: sc, currentSceneIndex: idx, updateScene } = useStudioStore.getState();
      if (sc.length > 0 && sc[idx]) {
        const updates: Partial<Scene> = {};
        if (data.positive_prompt) updates.image_prompt = data.positive_prompt as string;
        if (data.negative_prompt) updates.negative_prompt = data.negative_prompt as string;
        if (data.context_tags) updates.context_tags = data.context_tags as Record<string, string[]>;
        if (data.id) updates.prompt_history_id = data.id as number;
        updateScene(sc[idx].id, updates);
      }
      window.localStorage.removeItem(PROMPT_APPLY_KEY);
      useStudioStore.getState().showToast("Prompt applied!", "success");
    } catch {
      window.localStorage.removeItem(PROMPT_APPLY_KEY);
    }
  }, [setPlan]);

  // One-time migration: localStorage channelProfile → Project.avatar_key
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (localStorage.getItem("channel_profile_migrated")) return;

    try {
      const raw = localStorage.getItem("shorts-producer:studio:v1");
      if (!raw) return;
      const persisted = JSON.parse(raw)?.state;
      const profile = persisted?.channelProfile;
      if (!profile?.avatar_key) return;

      const { projectId } = useStudioStore.getState();
      if (!projectId) return;

      updateProject(projectId, { avatar_key: profile.avatar_key });
      localStorage.setItem("channel_profile_migrated", "true");
    } catch {
      // Silently ignore migration errors
    }
  }, []);

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
        // Sync groupId and projectId from storyboard's group
        const groupId = data.group_id ?? null;
        let projectId: number | null = null;
        if (groupId) {
          const { groups } = useStudioStore.getState();
          const group = groups.find((g) => g.id === groupId);
          if (group) projectId = group.project_id;
        }
        setMeta({
          storyboardId: data.id,
          storyboardTitle: data.title,
          activeTab: data.scenes?.length > 0 ? "scenes" : "plan",
          ...(groupId ? { groupId } : {}),
          ...(projectId ? { projectId } : {}),
        });
        useStudioStore.getState().setOutput({
          videoUrl: data.video_url || null,
          videoUrlFull: data.video_url || null,
          recentVideos: data.recent_videos || [],
          videoCaption: data.caption || "",
        });
        setPlan({
          selectedCharacterId: data.character_id || null,
          topic: data.title || "",
          description: data.description || "",
        });

        if (data.character_id) {
          loadCharacterData(data.character_id, setPlan);
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
      })
      .catch((err) => {
        if (err?.response?.status === 404) {
          resetStudioStore();
          useStudioStore
            .getState()
            .showToast("삭제되었거나 존재하지 않는 스토리보드입니다.", "error");
          const url = new URL(window.location.href);
          url.searchParams.delete("id");
          window.history.replaceState({}, "", url.toString());
        } else {
          setMeta({ storyboardId: null });
        }
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
    isGenerating: false,
    debug_payload: "",
    context_tags: (s.context_tags as Record<string, string[]>) || undefined,
    environment_reference_id: (s.environment_reference_id as number) || null,
    environment_reference_weight: (s.environment_reference_weight as number) || undefined,
    use_reference_only: (s.use_reference_only as boolean) || undefined,
    reference_only_weight: (s.reference_only_weight as number) || undefined,
  }));
}
