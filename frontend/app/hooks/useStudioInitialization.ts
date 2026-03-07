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
import { generateSceneClientId } from "../utils/uuid";
import { isMultiCharStructure } from "../utils/structure";

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
  const isMountRef = useRef(true);

  useEffect(() => {
    const isNewStoryboard = searchParams.get("new") === "true";
    if (!isNewStoryboard) {
      // After ?new=true URL cleanup, skip one re-render to preserve isNewStoryboardMode
      if (newHandledRef.current) {
        newHandledRef.current = false;
        isMountRef.current = false;
        return;
      }
      // Only on fresh mount (page entry): clear stale isNewStoryboardMode
      // Skips URL changes within session (e.g. ?mode=full toggle)
      if (isMountRef.current && !searchParams.get("id")) {
        useUIStore.getState().set({ isNewStoryboardMode: false });
      }
      isMountRef.current = false;
      return;
    }
    isMountRef.current = false;
    if (newHandledRef.current) return;
    newHandledRef.current = true;

    // Async IIFE to handle resetAllStores (now async)
    (async () => {
      await resetAllStores();
      // Set store flag before URL cleanup (URL-independent new mode)
      useUIStore.getState().set({ isNewStoryboardMode: true });

      const { effectiveCharacterId } = useContextStore.getState();
      if (effectiveCharacterId) {
        setPlan({ selectedCharacterId: effectiveCharacterId });
      }

      // Apply backend generation defaults to freshly reset store
      try {
        const res = await fetch(`${API_BASE}/presets`);
        const data = await res.json();
        if (data?.generation_defaults) {
          useStoryboardStore.getState().applyGenerationDefaults(data.generation_defaults);
        }
      } catch {
        // silent — initialState fallback values are used
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
        updateScene(sc[idx].client_id, updates);
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
        const recentVideos = (data.recent_videos || []).map(
          (v: { url: string; label?: string; createdAt: number; renderHistoryId?: number }) => ({
            url: v.url,
            label: v.label,
            createdAt: v.createdAt,
            renderHistoryId: v.renderHistoryId,
          })
        );
        const latestFull = recentVideos.find((v: { label?: string }) => v.label === "full");
        const latestPost = recentVideos.find((v: { label?: string }) => v.label === "post");
        useRenderStore.getState().set({
          videoUrl: data.video_url || null,
          videoUrlFull: latestFull?.url || data.video_url || null,
          videoUrlPost: latestPost?.url || null,
          recentVideos,
          videoCaption: data.caption || "",
          ...(data.bgm_prompt ? { bgmPrompt: data.bgm_prompt, bgmMode: "auto" as const } : {}),
          ...(data.bgm_mood ? { bgmMood: data.bgm_mood } : {}),
        });
        const structure = data.structure || DEFAULT_STRUCTURE;
        const isMulti = isMultiCharStructure(structure);
        const charBId = isMulti ? data.character_b_id || null : null;
        setPlan({
          selectedCharacterId: data.character_id || null,
          selectedCharacterBId: charBId,
          // Non-Dialogue: 명시적으로 Character B 관련 필드 초기화 (stale 데이터 방지)
          ...(!isMulti && {
            selectedCharacterBName: null,
            basePromptB: "",
            baseNegativePromptB: "",
            characterBLoras: [],
          }),
          structure,
          topic: data.title || "",
          description: data.description || "",
          storyboardVersion: data.version ?? null,
          ...(data.duration != null && { duration: data.duration }),
          ...(data.language != null && { language: data.language }),
          castingRecommendation: data.casting_recommendation ?? null,
        });

        // Parallel load: character A, character B, style profile are independent
        const parallelLoads: Promise<unknown>[] = [];
        if (data.character_id) {
          parallelLoads.push(loadCharacterData(data.character_id, setPlan));
        }
        if (charBId) {
          parallelLoads.push(loadCharacterBData(charBId, setPlan));
        }
        if (data.style_profile_id) {
          setLoadedProfileId(data.style_profile_id);
          parallelLoads.push(
            loadStyleProfileFromId(data.style_profile_id, { skipHiResSync: true })
          );
        } else {
          setLoadedProfileId(null);
          setNeedsStyleProfile(true);
        }
        // Load group render defaults in parallel (independent of character/style)
        if (groupId) {
          parallelLoads.push(
            loadGroupDefaults(groupId, {
              skipStyleProfile: !!data.style_profile_id,
            })
          );
        }
        if (parallelLoads.length > 0) {
          void Promise.allSettled(parallelLoads);
        }

        if (data.scenes?.length > 0) {
          const mapped = mapDbScenes(data.scenes);
          setScenes(mapped);
        }

        // Initialize video metadata (caption/likes) once topic is set
        initializeVideoMetadata(data.title || "");
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
  basePrompt: string;
  baseNegative: string;
};

const CHAR_A_FIELDS: CharacterFieldMap = {
  loras: "characterLoras",
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
    const nameField =
      fields.basePrompt === "basePromptA" ? "selectedCharacterName" : "selectedCharacterBName";
    const updates: Record<string, unknown> = {
      [fields.loras]: char.loras || [],
      [fields.basePrompt]: char.positive_prompt || "",
      [fields.baseNegative]: char.negative_prompt || "",
      [nameField]: char.name || null,
    };
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
// Spread passthrough: DB 필드를 그대로 전달하고, 변환/기본값이 필요한 필드만 오버라이드.
// 신규 필드 추가 시 매핑 누락으로 인한 데이터 소실 방지.
function mapDbScenes(dbScenes: Record<string, unknown>[]): Scene[] {
  return dbScenes.map((s, i) => ({
    ...(s as unknown as Scene),
    // Fallbacks for required fields
    id: (s.id as number) || i,
    client_id: (s.client_id as string) || generateSceneClientId(),
    order: (s.order as number) ?? (s.scene_id as number) ?? i,
    script: (s.script as string) || "",
    speaker: ((s.speaker as string) || "Narrator") as Scene["speaker"],
    duration: (s.duration as number) || 3,
    image_prompt: (s.image_prompt as string) || "",
    image_prompt_ko: (s.image_prompt_ko as string) || "",
    negative_prompt: (s.negative_prompt as string) || "",
    // UI-only fields (always reset)
    isGenerating: false,
    debug_payload: "",
    _auto_pin_previous: (s._auto_pin_previous as boolean) ?? false,
  }));
}
