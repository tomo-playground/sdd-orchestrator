"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import axios from "axios";
import { API_BASE, CATEGORY_DESCRIPTIONS, OVERLAY_STYLES, PROMPT_APPLY_KEY } from "../constants";
import { useCharacters, useTags } from "../hooks";
import LoadingSpinner from "../components/ui/LoadingSpinner";
import CharacterEditModal from "./CharacterEditModal";
import DeprecatedTagsPanel from "./DeprecatedTagsPanel";

import type { LoRA, SDModelEntry, Embedding, StyleProfile, StyleProfileFull, Character, Tag, PromptHistory } from "../types";

type AudioItem = { name: string; url: string };
type FontItem = { name: string };
type LoraItem = { name: string; alias?: string };
type ManageTab = "assets" | "style" | "tags" | "prompts" | "evaluation" | "settings";



export default function ManagePage() {
  const router = useRouter();
  const { characters, reload: fetchCharacters } = useCharacters();
  const { tags: allTags, tagsByGroup: tagGroupsByCategory, reload: fetchTagsData } = useTags(null);

  const [manageTab, setManageTab] = useState<ManageTab>("tags");
  const [isRegeneratingChar, setIsRegeneratingChar] = useState<Record<number, boolean>>({});
  const [charImageTimestamps, setCharImageTimestamps] = useState<Record<number, number>>({});

  const [enlargedImage, setEnlargedImage] = useState<{ url: string; title: string } | null>(null);
  const [bgmList, setBgmList] = useState<AudioItem[]>([]);
  const [fontList, setFontList] = useState<FontItem[]>([]);
  const [loraList, setLoraList] = useState<LoraItem[]>([]);
  const [isPreviewingBgm, setIsPreviewingBgm] = useState(false);

  // Style tab state
  const [editingCharacter, setEditingCharacter] = useState<Character | null>(null);
  const [isCreatingCharacter, setIsCreatingCharacter] = useState(false);
  const [styleProfiles, setStyleProfiles] = useState<StyleProfile[]>([]);
  const [loraEntries, setLoraEntries] = useState<LoRA[]>([]);
  const [sdModels, setSdModels] = useState<SDModelEntry[]>([]);
  const [embeddings, setEmbeddings] = useState<Embedding[]>([]);
  const [isStyleLoading, setIsStyleLoading] = useState(false);

  // Tags tab state
  type TagGroup = { category: string; group_name: string; count: number };
  const [tagGroups, setTagGroups] = useState<TagGroup[]>([]);
  const [isTagsLoading, setIsTagsLoading] = useState(false);
  const [tagGroupFilter, setTagGroupFilter] = useState<string>("");
  const [tagCategoryFilter, setTagCategoryFilter] = useState<string>("");
  const [civitaiSearch, setCivitaiSearch] = useState("");
  const [civitaiResults, setCivitaiResults] = useState<LoRA[]>([]);
  const [isSearchingCivitai, setIsSearchingCivitai] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState<StyleProfileFull | null>(null);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const previewTimeoutRef = useRef<number | null>(null);

  // Pending classifications state (15.7.5)
  type PendingTag = {
    id: number;
    name: string;
    category: string;
    group_name: string | null;
    classification_source: string | null;
    classification_confidence: number | null;
  };
  const [pendingTags, setPendingTags] = useState<PendingTag[]>([]);
  const [isPendingLoading, setIsPendingLoading] = useState(false);
  const [pendingGroupSelection, setPendingGroupSelection] = useState<Record<number, string>>({});
  const [pendingApproving, setPendingApproving] = useState<Record<number, boolean>>({});
  const [showPendingSection, setShowPendingSection] = useState(true);
  const [editingLora, setEditingLora] = useState<LoRA | null>(null);
  const [isUpdatingLora, setIsUpdatingLora] = useState(false);

  // Storage state
  type StorageStats = {
    total_size_mb: number;
    total_count: number;
    directories: Record<string, { count: number; size_mb: number }>;
  };
  type CleanupResult = {
    deleted_count: number;
    freed_mb: number;
    dry_run: boolean;
    details: Record<string, { deleted: number; freed_mb: number; files?: string[] }>;
  };
  const [storageStats, setStorageStats] = useState<StorageStats | null>(null);
  const [isLoadingStorage, setIsLoadingStorage] = useState(false);
  const [cleanupResult, setCleanupResult] = useState<CleanupResult | null>(null);
  const [isCleaningUp, setIsCleaningUp] = useState(false);
  const [cleanupOptions, setCleanupOptions] = useState({
    cleanup_videos: true,
    video_max_age_days: 7,
    cleanup_cache: true,
    cleanup_test_folders: true,
    cleanup_candidates: false,
  });

  // Prompt History state
  const [promptHistories, setPromptHistories] = useState<PromptHistory[]>([]);
  const [isPromptsLoading, setIsPromptsLoading] = useState(false);
  const [promptsFilter, setPromptsFilter] = useState<"all" | "favorites">("all");
  const [promptsCharacterFilter, setPromptsCharacterFilter] = useState<number | null>(null);
  const [promptsSearch, setPromptsSearch] = useState("");
  const [promptsSort, setPromptsSort] = useState<"created_at" | "use_count" | "avg_match_rate">("created_at");
  const [deletingPromptId, setDeletingPromptId] = useState<number | null>(null);

  // Evaluation state (15.6)
  type TestPromptInfo = { name: string; description: string; tokens: string[]; subject: string };
  type EvalTestSummary = {
    test_name: string;
    standard_avg?: number;
    standard_count?: number;
    lora_avg?: number;
    lora_count?: number;
    diff: number;
    winner: "standard" | "lora" | "tie";
  };
  type EvalSummary = {
    tests: EvalTestSummary[];
    overall: { standard_avg: number; lora_avg: number; diff: number; winner: string };
  };
  const [testPrompts, setTestPrompts] = useState<TestPromptInfo[]>([]);
  const [evalSummary, setEvalSummary] = useState<EvalSummary | null>(null);
  const [isEvalLoading, setIsEvalLoading] = useState(false);
  const [isEvalRunning, setIsEvalRunning] = useState(false);
  const [selectedTests, setSelectedTests] = useState<Set<string>>(new Set());
  const [evalCharacterId, setEvalCharacterId] = useState<number | null>(null);
  const [evalRepetitions, setEvalRepetitions] = useState(3);
  const [evalLastBatchId, setEvalLastBatchId] = useState<string | null>(null);

  const handleSaveCharacter = async (data: Partial<Character>, id?: number) => {
    try {
      if (id) {
        // Update existing character
        await axios.put(`${API_BASE}/characters/${id}`, data);
        alert("Character updated successfully!");
      } else {
        // Create new character
        await axios.post(`${API_BASE}/characters`, data);
        alert("Character created successfully!");
      }
      await fetchStyleData();
      setEditingCharacter(null);
      setIsCreatingCharacter(false);
    } catch (error) {
      console.error("Failed to save character", error);
      alert("Failed to save character");
      throw error;
    }
  };

  const handleRegenerateReference = async (charId: number) => {
    if (!confirm("Regenerate reference image for this character? This will overwrite the existing image.")) return;
    setIsRegeneratingChar((prev) => ({ ...prev, [charId]: true }));
    try {
      await axios.post(`${API_BASE}/characters/${charId}/regenerate-reference`);
      // Update timestamp to bust cache
      setCharImageTimestamps((prev) => ({ ...prev, [charId]: Date.now() }));
      await fetchStyleData();
      alert("Reference regenerated successfully!");
    } catch {
      alert("Failed to regenerate reference");
    } finally {
      setIsRegeneratingChar((prev) => ({ ...prev, [charId]: false }));
    }
  };

  useEffect(() => {
    axios
      .get(`${API_BASE}/audio/list`)
      .then((res) => setBgmList(res.data.audios || []))
      .catch(() => setBgmList([]));
  }, []);

  useEffect(() => {
    axios
      .get(`${API_BASE}/sd/loras`)
      .then((res) => setLoraList(res.data.loras || []))
      .catch(() => setLoraList([]));
  }, []);

  useEffect(() => {
    axios
      .get(`${API_BASE}/fonts/list`)
      .then((res) => {
        const list = (res.data.fonts || []).map((name: string) => ({ name }));
        setFontList(list);
      })
      .catch(() => setFontList([]));
  }, []);

  const fetchStorageStats = async () => {
    setIsLoadingStorage(true);
    try {
      const res = await axios.get(`${API_BASE}/storage/stats`);
      setStorageStats(res.data);
    } catch {
      setStorageStats(null);
    } finally {
      setIsLoadingStorage(false);
    }
  };

  const handleCleanup = async (dryRun: boolean) => {
    setIsCleaningUp(true);
    setCleanupResult(null);
    try {
      const res = await axios.post(`${API_BASE}/storage/cleanup`, {
        ...cleanupOptions,
        dry_run: dryRun,
      });
      setCleanupResult(res.data);
      if (!dryRun) {
        await fetchStorageStats();
      }
    } catch {
      alert("Cleanup failed.");
    } finally {
      setIsCleaningUp(false);
    }
  };

  useEffect(() => {
    if (manageTab === "settings") {
      void fetchStorageStats();
    }
  }, [manageTab]);

  // Prompt History tab data fetching
  const fetchPromptHistories = async () => {
    setIsPromptsLoading(true);
    try {
      const params: Record<string, string | number | boolean> = { sort: promptsSort };
      if (promptsFilter === "favorites") params.favorite = true;
      if (promptsCharacterFilter) params.character_id = promptsCharacterFilter;
      if (promptsSearch) params.search = promptsSearch;
      const res = await axios.get(`${API_BASE}/prompt-histories`, { params });
      setPromptHistories(res.data || []);
    } catch {
      console.error("Failed to fetch prompt histories");
    } finally {
      setIsPromptsLoading(false);
    }
  };

  const togglePromptFavorite = async (id: number) => {
    try {
      await axios.post(`${API_BASE}/prompt-histories/${id}/toggle-favorite`);
      await fetchPromptHistories();
    } catch {
      console.error("Failed to toggle favorite");
    }
  };

  const deletePromptHistory = async (id: number) => {
    if (!confirm("Delete this prompt history?")) return;
    setDeletingPromptId(id);
    try {
      await axios.delete(`${API_BASE}/prompt-histories/${id}`);
      await fetchPromptHistories();
    } catch {
      console.error("Failed to delete prompt history");
    } finally {
      setDeletingPromptId(null);
    }
  };

  const applyPromptHistory = async (id: number) => {
    try {
      const res = await axios.post(`${API_BASE}/prompt-histories/${id}/apply`);
      localStorage.setItem(PROMPT_APPLY_KEY, JSON.stringify(res.data));
      router.push("/studio");
    } catch {
      console.error("Failed to apply prompt history");
    }
  };

  useEffect(() => {
    if (manageTab === "prompts") {
      void fetchPromptHistories();
      // Load characters for filter dropdown via hook
      void fetchCharacters();
    }
  }, [manageTab, promptsFilter, promptsCharacterFilter, promptsSort, fetchCharacters]);

  // Evaluation tab data fetching
  const fetchEvalData = async () => {
    setIsEvalLoading(true);
    try {
      const [testsRes, summaryRes] = await Promise.all([
        axios.get(`${API_BASE}/eval/tests`),
        axios.get(`${API_BASE}/eval/summary`, {
          params: evalCharacterId ? { character_id: evalCharacterId } : {},
        }),
      ]);
      setTestPrompts(testsRes.data || []);
      setEvalSummary(summaryRes.data || null);
    } catch (err) {
      console.error("Failed to fetch eval data", err);
    } finally {
      setIsEvalLoading(false);
    }
  };

  const runEvaluation = async () => {
    if (selectedTests.size === 0) return;
    setIsEvalRunning(true);
    try {
      const res = await axios.post(`${API_BASE}/eval/run`, {
        test_names: Array.from(selectedTests),
        character_id: evalCharacterId,
        modes: ["standard", "lora"],
        repetitions: evalRepetitions,
      });
      setEvalLastBatchId(res.data.batch_id);
      // Refresh summary
      await fetchEvalData();
    } catch (err) {
      console.error("Evaluation failed", err);
    } finally {
      setIsEvalRunning(false);
    }
  };

  useEffect(() => {
    if (manageTab === "evaluation") {
      void fetchEvalData();
      // Load characters via hook
      void fetchCharacters();
    }
  }, [manageTab, evalCharacterId, fetchCharacters]);

  // Style tab data fetching
  const fetchStyleData = async () => {
    setIsStyleLoading(true);
    try {
      const [profilesRes, lorasRes, modelsRes, embsRes] = await Promise.all([
        axios.get(`${API_BASE}/style-profiles`),
        axios.get(`${API_BASE}/loras`),
        axios.get(`${API_BASE}/sd-models`),
        axios.get(`${API_BASE}/embeddings`),
      ]);
      setStyleProfiles(profilesRes.data || []);
      setLoraEntries(lorasRes.data || []);
      setSdModels(modelsRes.data || []);
      setEmbeddings(embsRes.data || []);

      // Sync hooks
      void fetchCharacters();
      void fetchTagsData();
    } catch {
      console.error("Failed to fetch style data");
    } finally {
      setIsStyleLoading(false);
    }
  };

  const fetchProfileFull = async (profileId: number) => {
    try {
      const res = await axios.get(`${API_BASE}/style-profiles/${profileId}/full`);
      setSelectedProfile(res.data);
    } catch {
      setSelectedProfile(null);
    }
  };

  const searchCivitai = async () => {
    if (!civitaiSearch.trim()) return;
    setIsSearchingCivitai(true);
    try {
      const res = await axios.get(`${API_BASE}/loras/search-civitai?query=${encodeURIComponent(civitaiSearch)}&limit=10`);
      setCivitaiResults(res.data.results || []);
    } catch {
      setCivitaiResults([]);
    } finally {
      setIsSearchingCivitai(false);
    }
  };

  const importFromCivitai = async (civitaiId: number) => {
    try {
      await axios.post(`${API_BASE}/loras/import-civitai/${civitaiId}`);
      await fetchStyleData();
      alert("LoRA imported successfully!");
    } catch {
      alert("Failed to import LoRA");
    }
  };

  const setDefaultProfile = async (profileId: number) => {
    try {
      await axios.put(`${API_BASE}/style-profiles/${profileId}`, { is_default: true });
      await fetchStyleData();
    } catch {
      alert("Failed to set default profile");
    }
  };

  const deleteStyleProfile = async (profileId: number) => {
    if (!confirm("Delete this style profile?")) return;
    try {
      await axios.delete(`${API_BASE}/style-profiles/${profileId}`);
      await fetchStyleData();
      if (selectedProfile?.id === profileId) setSelectedProfile(null);
    } catch {
      alert("Failed to delete profile");
    }
  };

  const deleteLoRA = async (loraId: number) => {
    if (!confirm("Delete this LoRA?")) return;
    try {
      await axios.delete(`${API_BASE}/loras/${loraId}`);
      await fetchStyleData();
    } catch {
      alert("Failed to delete LoRA");
    }
  };

  const handleUpdateLora = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingLora) return;
    setIsUpdatingLora(true);
    try {
      await axios.put(`${API_BASE}/loras/${editingLora.id}`, {
        display_name: editingLora.display_name,
        trigger_words: editingLora.trigger_words,
        optimal_weight: editingLora.optimal_weight,
        default_weight: editingLora.default_weight,
        weight_min: editingLora.weight_min,
        weight_max: editingLora.weight_max,
      });
      await fetchStyleData();
      setEditingLora(null);
      alert("LoRA updated and rules synchronized!");
    } catch {
      alert("Failed to update LoRA");
    } finally {
      setIsUpdatingLora(false);
    }
  };

  const deleteCharacter = async (charId: number) => {
    if (!confirm("Delete this character?")) return;
    try {
      await axios.delete(`${API_BASE}/characters/${charId}`);
      await fetchStyleData();
    } catch {
      alert("Failed to delete character");
    }
  };

  useEffect(() => {
    if (manageTab === "style") {
      void fetchStyleData();
    }
  }, [manageTab]);

  useEffect(() => {
    if (manageTab === "tags") {
      void fetchTagsData();
      void fetchPendingTags();
    }
  }, [manageTab, fetchTagsData]);

  // Pending classifications functions (15.7.5)
  const fetchPendingTags = async () => {
    setIsPendingLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/tags/pending?limit=50`);
      setPendingTags(res.data.tags || []);
      // Pre-populate group selections with existing values
      const selections: Record<number, string> = {};
      (res.data.tags || []).forEach((tag: PendingTag) => {
        if (tag.group_name) {
          selections[tag.id] = tag.group_name;
        }
      });
      setPendingGroupSelection(selections);
    } catch {
      console.error("Failed to fetch pending tags");
    } finally {
      setIsPendingLoading(false);
    }
  };

  const handleApprovePendingTag = async (tagId: number) => {
    const groupName = pendingGroupSelection[tagId];
    if (!groupName) {
      alert("Please select a group first");
      return;
    }
    setPendingApproving((prev) => ({ ...prev, [tagId]: true }));
    try {
      await axios.post(`${API_BASE}/tags/approve-classification`, {
        tag_id: tagId,
        group_name: groupName,
      });
      setPendingTags((prev) => prev.filter((t) => t.id !== tagId));
      setPendingGroupSelection((prev) => {
        const next = { ...prev };
        delete next[tagId];
        return next;
      });
    } catch {
      alert("Failed to approve tag");
    } finally {
      setPendingApproving((prev) => ({ ...prev, [tagId]: false }));
    }
  };

  // Available groups for classification
  const availableGroups = useMemo(() => {
    const groups = new Set<string>();
    allTags.forEach((tag: Tag) => {
      if (tag.group_name) groups.add(tag.group_name);
    });
    return Array.from(groups).sort();
  }, [allTags]);

  // Computed values for tags tab
  const filteredTags = useMemo(() => {
    return allTags.filter((tag: Tag) => {
      if (tagCategoryFilter && tag.category !== tagCategoryFilter) return false;
      if (tagGroupFilter && tag.group_name !== tagGroupFilter) return false;
      return true;
    });
  }, [allTags, tagCategoryFilter, tagGroupFilter]);

  const tagCategories = useMemo(() => {
    return [...new Set(allTags.map((t: Tag) => t.category))].sort();
  }, [allTags]);

  const SCENE_TAG_GROUPS = ["expression", "gaze", "pose", "action", "camera", "environment", "mood"];

  const stopBgmPreview = () => {
    if (previewTimeoutRef.current) {
      window.clearTimeout(previewTimeoutRef.current);
      previewTimeoutRef.current = null;
    }
    if (previewAudioRef.current) {
      previewAudioRef.current.pause();
      previewAudioRef.current.currentTime = 0;
    }
    setIsPreviewingBgm(false);
  };

  const handlePreviewBgm = (url: string) => {
    if (!url) return;
    stopBgmPreview();
    const audio = new Audio(url);
    audio.onerror = () => {
      stopBgmPreview();
      alert(`BGM load failed: ${url}`);
    };
    previewAudioRef.current = audio;
    setIsPreviewingBgm(true);
    audio.play().catch((err) => {
      stopBgmPreview();
      alert(`BGM preview failed: ${err.message || err}`);
    });
    previewTimeoutRef.current = window.setTimeout(() => {
      stopBgmPreview();
    }, 10000);
  };

  useEffect(() => {
    return () => {
      stopBgmPreview();
    };
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-50 via-white to-zinc-100 text-zinc-900">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-zinc-200/60 bg-white/80 backdrop-blur-lg">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <h1 className="text-lg font-bold tracking-tight text-zinc-900">
            Manage
          </h1>
          <Link
            href="/"
            className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-xs font-semibold text-zinc-600 hover:bg-zinc-50 transition"
          >
            Home
          </Link>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-6 py-6">

        <div className="flex flex-wrap items-center gap-2">
          {[
            { id: "tags", label: "Tags" },
            { id: "style", label: "Style" },
            { id: "prompts", label: "Prompts" },
            { id: "evaluation", label: "Eval" },
            { id: "assets", label: "Assets" },
            { id: "settings", label: "Settings" },
          ].map((tab) => {
            const active = manageTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setManageTab(tab.id as typeof manageTab)}
                className={`rounded-full px-4 py-2 text-[10px] font-semibold tracking-[0.2em] uppercase transition ${active
                  ? "bg-zinc-900 text-white"
                  : "border border-zinc-200 bg-white text-zinc-600"
                  }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {manageTab === "tags" && (
          <section className="grid gap-6 rounded-2xl border border-zinc-200/60 bg-white p-6 text-xs text-zinc-600 shadow-sm">
            {/* Deprecated Tags */}
            <DeprecatedTagsPanel />

            <div className="flex items-center justify-between">
              <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                Tag Analysis
              </span>
              <button
                type="button"
                onClick={fetchTagsData}
                disabled={isTagsLoading}
                className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase hover:bg-zinc-50 disabled:opacity-50"
              >
                {isTagsLoading ? (
                  <div className="flex items-center gap-2">
                    <LoadingSpinner size="sm" color="text-zinc-400" />
                    <span>Loading...</span>
                  </div>
                ) : (
                  "Refresh"
                )}
              </button>
            </div>

            {/* Group Statistics Overview */}
            <div className="grid gap-4">
              <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">
                Scene Tag Groups (7 Categories)
              </span>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
                {SCENE_TAG_GROUPS.map((group: string) => {
                  const count = allTags.filter(
                    (t: Tag) => t.category === "scene" && t.group_name === group
                  ).length;
                  const isActive = tagGroupFilter === group && tagCategoryFilter === "scene";
                  return (
                    <button
                      key={group}
                      type="button"
                      onClick={() => {
                        if (isActive) {
                          setTagGroupFilter("");
                          setTagCategoryFilter("");
                        } else {
                          setTagGroupFilter(group);
                          setTagCategoryFilter("scene");
                        }
                      }}
                      className={`rounded-xl border p-3 text-center transition ${isActive
                        ? "border-indigo-300 bg-indigo-50"
                        : "border-zinc-200 bg-white hover:border-zinc-300"
                        }`}
                    >
                      <div className={`text-lg font-bold ${isActive ? "text-indigo-600" : "text-zinc-700"}`}>
                        {count}
                      </div>
                      <div className={`text-[9px] font-medium uppercase tracking-wider ${isActive ? "text-indigo-500" : "text-zinc-400"}`}>
                        {group}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Character Tag Groups */}
            <div className="grid gap-4">
              <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">
                Character Tag Groups
              </span>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-5">
                {[...new Set(allTags.filter(t => t.category === "character").map(t => t.group_name || "other"))].map((group: string) => {
                  const count = allTags.filter(
                    (t: Tag) => t.category === "character" && (group === "other" ? !t.group_name : t.group_name === group)
                  ).length;
                  if (count === 0) return null;
                  const isActive = tagGroupFilter === group && tagCategoryFilter === "character";
                  return (
                    <button
                      key={group}
                      type="button"
                      onClick={() => {
                        if (isActive) {
                          setTagGroupFilter("");
                          setTagCategoryFilter("");
                        } else {
                          setTagGroupFilter(group);
                          setTagCategoryFilter("character");
                        }
                      }}
                      className={`rounded-xl border p-3 text-center transition ${isActive
                        ? "border-violet-300 bg-violet-50"
                        : "border-zinc-200 bg-white hover:border-zinc-300"
                        }`}
                    >
                      <div className={`text-lg font-bold ${isActive ? "text-violet-600" : "text-zinc-700"}`}>
                        {count}
                      </div>
                      <div className={`text-[9px] font-medium uppercase tracking-wider ${isActive ? "text-violet-500" : "text-zinc-400"}`}>
                        {group}
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Meta Tag Groups (Quality, Style) */}
              <div className="grid gap-4">
                <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">
                  Meta Tag Groups (Quality & Style)
                </span>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-5">
                  {[...new Set(allTags.filter(t => t.category === "meta").map(t => t.group_name || "other"))].map((group: string) => {
                    const count = allTags.filter(
                      (t: Tag) => t.category === "meta" && (group === "other" ? !t.group_name : t.group_name === group)
                    ).length;
                    if (count === 0) return null;
                    const isActive = tagGroupFilter === group && tagCategoryFilter === "meta";
                    return (
                      <button
                        key={group}
                        type="button"
                        onClick={() => {
                          if (isActive) {
                            setTagGroupFilter("");
                            setTagCategoryFilter("");
                          } else {
                            setTagGroupFilter(group);
                            setTagCategoryFilter("meta");
                          }
                        }}
                        className={`rounded-xl border p-3 text-center transition ${isActive
                          ? "border-emerald-300 bg-emerald-50"
                          : "border-zinc-200 bg-white hover:border-zinc-300"
                          }`}
                      >
                        <div className={`text-lg font-bold ${isActive ? "text-emerald-600" : "text-zinc-700"}`}>
                          {count}
                        </div>
                        <div className={`text-[9px] font-medium uppercase tracking-wider ${isActive ? "text-emerald-500" : "text-zinc-400"}`}>
                          {group}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Pending Classifications (15.7.5) */}
            <div className="grid gap-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-semibold tracking-[0.2em] text-amber-600 uppercase">
                    Pending Classifications
                  </span>
                  {pendingTags.length > 0 && (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[9px] font-semibold text-amber-700">
                      {pendingTags.length}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setShowPendingSection(!showPendingSection)}
                    className="rounded-full border border-zinc-200 bg-white px-2 py-1 text-[9px] font-semibold text-zinc-500"
                  >
                    {showPendingSection ? "Hide" : "Show"}
                  </button>
                  <button
                    type="button"
                    onClick={fetchPendingTags}
                    disabled={isPendingLoading}
                    className="rounded-full border border-zinc-200 bg-white px-2 py-1 text-[9px] font-semibold text-zinc-500 disabled:opacity-50"
                  >
                    {isPendingLoading ? "..." : "Refresh"}
                  </button>
                </div>
              </div>

              {showPendingSection && (
                <>
                  {isPendingLoading ? (
                    <div className="flex items-center justify-center py-4">
                      <LoadingSpinner size="sm" color="text-zinc-400" />
                    </div>
                  ) : pendingTags.length === 0 ? (
                    <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center">
                      <span className="text-xs text-emerald-600">All tags are classified!</span>
                    </div>
                  ) : (
                    <div className="grid gap-2 max-h-[400px] overflow-y-auto">
                      {pendingTags.map((tag) => (
                        <div
                          key={tag.id}
                          className="flex items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50/50 p-3"
                        >
                          <div className="flex items-center gap-3">
                            <div>
                              <span className="text-xs font-semibold text-zinc-700">{tag.name}</span>
                              <div className="flex items-center gap-2 mt-0.5">
                                <span className="text-[9px] text-zinc-400">
                                  {tag.classification_source || "unknown"}
                                </span>
                                {tag.classification_confidence !== null && (
                                  <span className="text-[9px] text-zinc-400">
                                    ({Math.round(tag.classification_confidence * 100)}%)
                                  </span>
                                )}
                                {tag.group_name && (
                                  <span className="rounded-full bg-zinc-100 px-1.5 py-0.5 text-[9px] text-zinc-500">
                                    {tag.group_name}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <select
                              value={pendingGroupSelection[tag.id] || ""}
                              onChange={(e) =>
                                setPendingGroupSelection((prev) => ({
                                  ...prev,
                                  [tag.id]: e.target.value,
                                }))
                              }
                              className="rounded-lg border border-zinc-200 bg-white px-2 py-1 text-[10px] outline-none focus:border-zinc-400"
                            >
                              <option value="">Select group</option>
                              {availableGroups.map((group) => (
                                <option key={group} value={group}>
                                  {group}
                                </option>
                              ))}
                            </select>
                            <button
                              type="button"
                              onClick={() => handleApprovePendingTag(tag.id)}
                              disabled={!pendingGroupSelection[tag.id] || pendingApproving[tag.id]}
                              className="rounded-full bg-amber-500 px-3 py-1 text-[9px] font-semibold text-white disabled:bg-zinc-300"
                            >
                              {pendingApproving[tag.id] ? "..." : "Approve"}
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Total Stats */}
            <div className="flex flex-wrap gap-4 rounded-xl border border-zinc-200 bg-zinc-50 p-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-zinc-700">{allTags.length}</div>
                <div className="text-[9px] font-medium uppercase tracking-wider text-zinc-400">Total Tags</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-indigo-600">
                  {allTags.filter((t: Tag) => t.category === "scene").length}
                </div>
                <div className="text-[9px] font-medium uppercase tracking-wider text-zinc-400">Scene Tags</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-violet-600">
                  {allTags.filter((t: Tag) => t.category === "character").length}
                </div>
                <div className="text-[9px] font-medium uppercase tracking-wider text-zinc-400">Character Tags</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-teal-600">
                  {allTags.filter((t: Tag) => t.category === "meta" && t.group_name === "quality").length}
                </div>
                <div className="text-[9px] font-medium uppercase tracking-wider text-zinc-400">Quality Tags</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-emerald-600">
                  {allTags.filter((t: Tag) => t.category === "meta" && t.group_name === "style").length}
                </div>
                <div className="text-[9px] font-medium uppercase tracking-wider text-zinc-400">Style Tags</div>
              </div>
            </div>

            {/* Filtered Tags List */}
            {(tagGroupFilter || tagCategoryFilter) && (
              <div className="grid gap-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">
                    {tagCategoryFilter} / {tagGroupFilter} ({filteredTags.length} tags)
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      setTagGroupFilter("");
                      setTagCategoryFilter("");
                    }}
                    className="text-[10px] text-zinc-400 hover:text-zinc-600"
                  >
                    Clear Filter
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {filteredTags.map((tag: Tag) => (
                    <span
                      key={tag.id}
                      className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-[10px] text-zinc-600"
                      title={`Priority: ${tag.priority}`}
                    >
                      {tag.name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* All Tags by Group (collapsed by default) */}
            {!tagGroupFilter && !tagCategoryFilter && (
              <div className="grid gap-4">
                <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">
                  All Tags by Category
                </span>
                {tagCategories.map((category: string) => (
                  <details key={category} className="rounded-xl border border-zinc-200 bg-white">
                    <summary className="cursor-pointer px-4 py-3 text-[10px] font-semibold uppercase tracking-wider text-zinc-500 hover:bg-zinc-50">
                      {category} ({allTags.filter((t: Tag) => t.category === category).length} tags)
                    </summary>
                    <div className="border-t border-zinc-100 p-4">
                      <div className="flex flex-wrap gap-2 mt-2">
                        {allTags.filter((t: Tag) => t.category === category).slice(0, 500).map((tag: Tag) => (
                          <span
                            key={tag.id}
                            className="rounded-full border border-zinc-100 bg-zinc-50 px-2 py-0.5 text-[9px] text-zinc-500"
                          >
                            {tag.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  </details>
                ))}
              </div>
            )}
          </section>
        )}

        {manageTab === "assets" && (
          <section className="grid gap-8 rounded-2xl border border-zinc-200/60 bg-white p-8 shadow-sm">
            {/* Overlay Styles */}
            <div className="grid gap-4">
              <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                  Overlay Architectures
                </span>
                <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[9px] font-bold text-indigo-500 uppercase">
                  {OVERLAY_STYLES.length} Styles
                </span>
              </div>
              <div className="grid gap-4 grid-cols-2 md:grid-cols-4 lg:grid-cols-6">
                {OVERLAY_STYLES.map((style) => (
                  <div
                    key={style.id}
                    className="group relative flex flex-col gap-2 rounded-2xl border border-zinc-200 bg-white p-2 transition-all duration-300 hover:border-indigo-300 hover:shadow-lg"
                  >
                    <div className="aspect-[9/16] overflow-hidden rounded-xl bg-zinc-50 border border-zinc-100">
                      <img
                        src={`${API_BASE}/assets/overlay/${style.id}`}
                        alt={style.label}
                        className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110"
                      />
                    </div>
                    <span className="text-[10px] font-bold text-zinc-600 text-center truncate px-1">
                      {style.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-8">
              {/* Fonts */}
              <div className="grid gap-4">
                <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                  <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                    Subtitle Typography
                  </span>
                </div>
                {fontList.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-zinc-200 p-8 text-center bg-zinc-50/30">
                    <p className="text-xs text-zinc-400 font-medium">No fonts available.</p>
                  </div>
                ) : (
                  <div className="grid gap-2 grid-cols-1">
                    {fontList.map((font) => (
                      <div
                        key={font.name}
                        className="flex items-center gap-3 rounded-2xl border border-zinc-200 bg-white px-4 py-3 transition-all duration-300 hover:border-indigo-200 hover:bg-indigo-50/10"
                      >
                        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-zinc-50 text-zinc-400 font-bold">
                          Ag
                        </div>
                        <span className="text-xs font-bold text-zinc-700">{font.name}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* BGM */}
              <div className="grid gap-4">
                <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                  <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                    Background Audio
                  </span>
                </div>
                {bgmList.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-zinc-200 p-8 text-center bg-zinc-50/30">
                    <p className="text-xs text-zinc-400 font-medium">No soundtracks found.</p>
                  </div>
                ) : (
                  <div className="grid gap-2">
                    {bgmList.map((bgm) => (
                      <div
                        key={bgm.name}
                        className="group flex items-center justify-between gap-4 rounded-2xl border border-zinc-200 bg-white px-4 py-3 transition-all duration-300 hover:border-indigo-200 hover:bg-indigo-50/10"
                      >
                        <div className="flex-1 min-w-0 flex items-center gap-3">
                          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-50 text-indigo-400">
                            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                            </svg>
                          </div>
                          <span className="truncate text-xs font-bold text-zinc-700">{bgm.name}</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => handlePreviewBgm(bgm.url)}
                          disabled={isPreviewingBgm}
                          className="shrink-0 rounded-full bg-zinc-900 px-4 py-1.5 text-[9px] font-bold uppercase tracking-wider text-white transition hover:bg-indigo-600 disabled:bg-zinc-300"
                        >
                          {isPreviewingBgm ? "Playing..." : "Preview"}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* LoRA Files (Internal Only) */}
            <div className="grid gap-4">
              <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                  Internal Model Weights (LoRA)
                </span>
              </div>
              {loraList.length === 0 ? (
                <p className="text-xs text-zinc-400 font-medium text-center py-8">No weight files found.</p>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {loraList.map((lora) => {
                    const name = lora.alias || lora.name;
                    return (
                      <div
                        key={name}
                        className="flex items-center justify-between gap-4 rounded-2xl border border-zinc-200 bg-white px-4 py-3 transition-all duration-300 hover:border-zinc-300 shadow-sm"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-orange-50 text-orange-400 font-bold text-[10px]">
                            L
                          </div>
                          <span className="truncate text-[11px] font-bold text-zinc-700">{name}</span>
                        </div>
                        <code className="shrink-0 rounded-lg bg-zinc-50 border border-zinc-100 px-2 py-1 text-[8px] font-bold text-zinc-400 uppercase">
                          {name}
                        </code>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </section>
        )}

        {manageTab === "style" && (
          <section className="grid gap-6 rounded-2xl border border-zinc-200/60 bg-white p-6 shadow-sm">
            {/* Header with Refresh */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-zinc-900">Style Profiles</h2>
                <p className="text-xs text-zinc-500 mt-0.5">
                  Model + LoRAs + Embeddings as cohesive sets
                </p>
              </div>
              <button
                onClick={fetchStyleData}
                disabled={isStyleLoading}
                className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-semibold tracking-[0.15em] text-zinc-600 uppercase disabled:text-zinc-400"
              >
                {isStyleLoading ? (
                  <div className="flex items-center gap-2">
                    <LoadingSpinner size="sm" color="text-zinc-400" />
                  </div>
                ) : (
                  "Refresh"
                )}
              </button>
            </div>

            {/* Style Profiles (Main Content - Always Visible) */}
            <div className="grid gap-4">
                {styleProfiles.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-zinc-200 p-12 text-center">
                    <p className="text-xs text-zinc-400">No style profiles found.</p>
                  </div>
                ) : (
                  <div className="grid gap-4 md:grid-cols-2">
                    {styleProfiles.map((profile) => (
                      <div
                        key={profile.id}
                        className={`group relative rounded-2xl border p-5 transition-all duration-300 cursor-pointer overflow-hidden ${profile.is_default
                          ? "border-indigo-200 bg-indigo-50/30 ring-1 ring-indigo-100"
                          : "border-zinc-200 bg-white hover:border-indigo-300 hover:shadow-xl hover:shadow-indigo-500/5 hover:-translate-y-0.5"
                          }`}
                        onClick={() => fetchProfileFull(profile.id)}
                      >
                        <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity">
                          {!profile.is_default && (
                            <button
                              onClick={(e) => { e.stopPropagation(); setDefaultProfile(profile.id); }}
                              className="rounded-full bg-emerald-500 p-2 text-white shadow-lg shadow-emerald-500/20 hover:bg-emerald-600 transition-colors"
                              title="Set as Default"
                            >
                              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                              </svg>
                            </button>
                          )}
                        </div>

                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1.5">
                              <h3 className="text-sm font-bold text-zinc-900">
                                {profile.display_name || profile.name}
                              </h3>
                              {profile.is_default && (
                                <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[8px] font-bold text-emerald-600 uppercase tracking-wider">
                                  Default
                                </span>
                              )}
                            </div>
                            <p className="text-[11px] leading-relaxed text-zinc-500 line-clamp-2">{profile.description || "No description provided."}</p>
                          </div>
                        </div>

                        <div className="mt-5 flex items-center justify-between border-t border-zinc-100 pt-4">
                          <div className="flex gap-2">
                            <span className="rounded-full bg-zinc-100 px-2.5 py-1 text-[9px] font-medium text-zinc-500 group-hover:bg-indigo-50 group-hover:text-indigo-600 transition-colors">
                              SD 1.5
                            </span>
                          </div>
                          <button
                            onClick={(e) => { e.stopPropagation(); deleteStyleProfile(profile.id); }}
                            className="text-[10px] font-bold text-rose-400 hover:text-rose-600 hover:underline px-2 transition-colors"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Selected Profile Details */}
                {selectedProfile && (
                  <div className="mt-4 rounded-2xl border border-zinc-200 bg-zinc-50 p-4">
                    <h4 className="mb-3 text-xs font-semibold text-zinc-700">
                      {selectedProfile.display_name || selectedProfile.name} Details
                    </h4>
                    <div className="grid gap-3 text-xs">
                      <div>
                        <span className="text-[10px] font-semibold text-zinc-500 uppercase">SD Model</span>
                        <p className="text-zinc-700">{selectedProfile.sd_model?.display_name || selectedProfile.sd_model?.name || "None"}</p>
                      </div>
                      <div>
                        <span className="text-[10px] font-semibold text-zinc-500 uppercase">LoRAs</span>
                        {selectedProfile.loras.length > 0 ? (
                          <div className="mt-1 flex flex-wrap gap-1">
                            {selectedProfile.loras.map((lora) => (
                              <span key={lora.id} className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] text-blue-700">
                                {lora.display_name || lora.name} ({lora.weight})
                              </span>
                            ))}
                          </div>
                        ) : (
                          <p className="text-zinc-400">None</p>
                        )}
                      </div>
                      <div>
                        <span className="text-[10px] font-semibold text-zinc-500 uppercase">Negative Embeddings</span>
                        {selectedProfile.negative_embeddings.length > 0 ? (
                          <div className="mt-1 flex flex-wrap gap-1">
                            {selectedProfile.negative_embeddings.map((emb) => (
                              <span key={emb.id} className="rounded-full bg-rose-100 px-2 py-0.5 text-[10px] text-rose-700">
                                {emb.name}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <p className="text-zinc-400">None</p>
                        )}
                      </div>
                      <div>
                        <span className="text-[10px] font-semibold text-zinc-500 uppercase">Default Positive</span>
                        <p className="mt-1 text-zinc-600 font-mono text-[10px] bg-white p-2 rounded border border-zinc-200">
                          {selectedProfile.default_positive || "None"}
                        </p>
                      </div>
                      <div>
                        <span className="text-[10px] font-semibold text-zinc-500 uppercase">Default Negative</span>
                        <p className="mt-1 text-zinc-600 font-mono text-[10px] bg-white p-2 rounded border border-zinc-200">
                          {selectedProfile.default_negative || "None"}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
            </div>

            {/* Available Assets (Collapsible Secondary Content) */}
            <details className="group rounded-2xl border border-zinc-200 bg-white/80">
              <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase">
                Available Assets
                <span className="text-zinc-400 transition group-open:rotate-180">▼</span>
              </summary>
              <div className="border-t border-zinc-100 p-4 grid gap-6">

                {/* LoRAs Section */}
                <div className="grid gap-4">
                  <h3 className="text-sm font-semibold text-zinc-700">LoRAs</h3>

                  {/* Civitai Search */}
                  <div className="rounded-2xl border border-zinc-200 bg-white p-4">
                  <span className="mb-2 block text-[10px] font-semibold tracking-[0.15em] text-zinc-500 uppercase">
                    Search Civitai
                  </span>
                  <div className="flex gap-2">
                    <input
                      value={civitaiSearch}
                      onChange={(e) => setCivitaiSearch(e.target.value)}
                      placeholder="Search LoRA name..."
                      className="flex-1 rounded-full border border-zinc-200 px-3 py-2 text-xs outline-none focus:border-zinc-400"
                      onKeyDown={(e) => e.key === "Enter" && searchCivitai()}
                    />
                    <button
                      onClick={searchCivitai}
                      disabled={isSearchingCivitai}
                      className="rounded-full bg-zinc-800 px-4 py-2 text-[10px] font-semibold text-white disabled:bg-zinc-400"
                    >
                      {isSearchingCivitai ? (
                        <div className="flex items-center gap-2">
                          <LoadingSpinner size="sm" color="text-white/70" />
                          <span>Searching...</span>
                        </div>
                      ) : (
                        "Search"
                      )}
                    </button>
                  </div>
                  {civitaiResults.length > 0 && (
                    <div className="mt-3 grid gap-2">
                      {civitaiResults.map((result) => (
                        <div key={result.civitai_id} className="flex items-center justify-between rounded-xl border border-zinc-100 bg-zinc-50 p-3">
                          <div className="flex items-center gap-3 overflow-hidden">
                            {result.preview_image_url && (
                              <img src={result.preview_image_url} alt="" className="h-12 w-12 rounded-lg object-cover shrink-0" />
                            )}
                            <div className="min-w-0">
                              <p className="text-xs font-semibold text-zinc-700 truncate">{result.display_name || result.name}</p>
                              <p className="text-[10px] text-zinc-400 truncate">
                                {result.trigger_words?.slice(0, 3).join(", ") || "No trigger words"}
                              </p>
                              <a
                                href={`https://civitai.com/models/${result.civitai_id}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="mt-1 flex items-center gap-1 text-[9px] font-bold text-indigo-500 hover:text-indigo-600 transition-colors uppercase tracking-widest"
                              >
                                <span>View on Civitai</span>
                                <svg className="h-2 w-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                </svg>
                              </a>
                            </div>
                          </div>
                          <button
                            onClick={() => importFromCivitai(result.civitai_id!)}
                            className="shrink-0 rounded-full bg-emerald-500 px-4 py-1.5 text-[10px] font-bold text-white shadow-lg shadow-emerald-500/10 hover:bg-emerald-600 transition-all active:scale-95"
                          >
                            Import
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Registered LoRAs */}
                <div>
                  <span className="mb-2 block text-[10px] font-semibold tracking-[0.15em] text-zinc-500 uppercase">
                    Registered LoRAs ({loraEntries.length})
                  </span>
                  {loraEntries.length === 0 ? (
                    <p className="text-xs text-zinc-400">No LoRAs registered yet.</p>
                  ) : (
                    <div className="grid gap-2 md:grid-cols-2">
                      {loraEntries.map((lora) => (
                        <div key={lora.id} className="group relative flex items-center gap-4 rounded-2xl border border-zinc-200 bg-white p-4 transition-all duration-300 hover:border-indigo-300 hover:shadow-xl hover:shadow-indigo-500/5">
                          <div className="relative shrink-0">
                            {lora.preview_image_url ? (
                              <img
                                src={lora.preview_image_url.startsWith('http') ? lora.preview_image_url : `${API_BASE}${lora.preview_image_url}`}
                                alt=""
                                className="h-16 w-16 rounded-2xl object-cover shadow-sm group-hover:scale-105 transition-transform duration-300"
                              />
                            ) : (
                              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-zinc-50 text-zinc-300 border border-zinc-100 font-bold text-xl">
                                {lora.name.charAt(0).toUpperCase()}
                              </div>
                            )}
                          </div>

                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <h3 className="truncate text-sm font-bold text-zinc-900">{lora.display_name || lora.name}</h3>
                              {lora.civitai_url && (
                                <a
                                  href={lora.civitai_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="shrink-0 p-1 text-zinc-400 hover:text-indigo-500 transition-colors"
                                  title="Open in Civitai"
                                >
                                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                  </svg>
                                </a>
                              )}
                            </div>

                            <div className="flex flex-wrap items-center gap-2">
                              <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[9px] font-bold text-zinc-500 uppercase tracking-tighter">
                                Weight: {lora.default_weight.toFixed(1)}
                              </span>
                              {lora.optimal_weight !== null ? (
                                <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[9px] font-bold text-emerald-600 uppercase tracking-tighter">
                                  Calibrated ({lora.calibration_score}%)
                                </span>
                              ) : (
                                <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[9px] font-bold text-amber-500 uppercase tracking-tighter">
                                  Not Calibrated
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="flex flex-col gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={() => setEditingLora(lora)}
                              className="rounded-full bg-zinc-900 p-2 text-white shadow-lg hover:bg-indigo-600 transition-colors"
                              title="Edit"
                            >
                              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                              </svg>
                            </button>
                            <button
                              onClick={() => deleteLoRA(lora.id)}
                              className="rounded-full bg-white border border-rose-100 p-2 text-rose-500 shadow-sm hover:border-rose-300 transition-colors"
                              title="Delete"
                            >
                              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

                {/* SD Models Section */}
                <div className="grid gap-4">
                  <h3 className="text-sm font-semibold text-zinc-700">SD Models</h3>
                {sdModels.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-zinc-200 p-12 text-center">
                    <p className="text-xs text-zinc-400">No models registered yet.</p>
                  </div>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2">
                    {sdModels.map((model) => (
                      <div key={model.id} className="group relative flex items-center justify-between rounded-2xl border border-zinc-200 bg-white p-5 transition-all duration-300 hover:border-indigo-300 hover:shadow-xl hover:shadow-indigo-500/5">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="text-sm font-bold text-zinc-900 truncate">{model.display_name || model.name}</h3>
                            {model.is_active && (
                              <span className="flex h-2 w-2 rounded-full bg-emerald-500 shadow-sm shadow-emerald-500/50" />
                            )}
                          </div>
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[9px] font-bold text-zinc-500 uppercase tracking-tighter">
                              {model.base_model || "SD 1.5"}
                            </span>
                            <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[9px] font-bold text-indigo-500 uppercase tracking-tighter">
                              {model.model_type}
                            </span>
                          </div>
                          {model.description && (
                            <p className="mt-2 text-[10px] text-zinc-400 line-clamp-1">{model.description}</p>
                          )}
                        </div>
                        <div className="shrink-0 ml-4">
                          <span className={`rounded-xl px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider ${model.is_active
                            ? "bg-emerald-50 text-emerald-600 border border-emerald-100"
                            : "bg-zinc-50 text-zinc-400 border border-zinc-100"
                            }`}>
                            {model.is_active ? "Active" : "Inactive"}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                </div>

                {/* Embeddings Section */}
                <div className="grid gap-4">
                  <h3 className="text-sm font-semibold text-zinc-700">Embeddings</h3>
                {embeddings.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-zinc-200 p-12 text-center">
                    <p className="text-xs text-zinc-400">No embeddings found.</p>
                  </div>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                    {embeddings.map((emb) => (
                      <div key={emb.id} className={`group flex flex-col rounded-2xl border p-4 transition-all duration-300 hover:shadow-lg ${emb.embedding_type === "negative"
                        ? "border-zinc-200 hover:border-rose-200 bg-white"
                        : "border-zinc-200 hover:border-emerald-200 bg-white"
                        }`}>
                        <div className="flex items-start justify-between mb-3">
                          <div className="min-w-0">
                            <h3 className="text-sm font-bold text-zinc-900 truncate">{emb.display_name || emb.name}</h3>
                            {emb.trigger_word && (
                              <code className="mt-1 block font-mono text-[9px] text-zinc-400 font-bold bg-zinc-50 px-1.5 py-0.5 rounded-md truncate">
                                {emb.trigger_word}
                              </code>
                            )}
                          </div>
                          <span className={`shrink-0 rounded-full px-2 py-0.5 text-[8px] font-bold uppercase tracking-wider ${emb.embedding_type === "negative"
                            ? "bg-rose-50 text-rose-600 border border-rose-100"
                            : "bg-emerald-50 text-emerald-600 border border-emerald-100"
                            }`}>
                            {emb.embedding_type}
                          </span>
                        </div>
                        {emb.description && (
                          <p className="text-[10px] text-zinc-500 leading-relaxed line-clamp-2">{emb.description}</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                </div>

              </div>
            </details>
          </section>
        )}


        {manageTab === "prompts" && (
          <section className="grid gap-4 rounded-2xl border border-zinc-200/60 bg-white p-6 shadow-sm">
            {/* Filters */}
            <div className="flex flex-wrap items-center gap-2">
              <select
                value={promptsFilter}
                onChange={(e) => setPromptsFilter(e.target.value as "all" | "favorites")}
                className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-medium text-zinc-600 shadow-sm transition outline-none focus:border-zinc-400"
              >
                <option value="all">All Prompts</option>
                <option value="favorites">Favorites Only</option>
              </select>
              <select
                value={promptsCharacterFilter ?? ""}
                onChange={(e) => setPromptsCharacterFilter(e.target.value ? Number(e.target.value) : null)}
                className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-medium text-zinc-600 shadow-sm transition outline-none focus:border-zinc-400"
              >
                <option value="">All Characters</option>
                {characters.map((char: Character) => (
                  <option key={char.id} value={char.id}>{char.name}</option>
                ))}
              </select>
              <select
                value={promptsSort}
                onChange={(e) => setPromptsSort(e.target.value as typeof promptsSort)}
                className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase shadow-sm transition outline-none focus:border-zinc-400"
              >
                <option value="created_at">Newest</option>
                <option value="use_count">Most Used</option>
                <option value="avg_match_rate">Highest Score</option>
              </select>
              <input
                value={promptsSearch}
                onChange={(e) => setPromptsSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && fetchPromptHistories()}
                placeholder="Search prompts..."
                className="min-w-[140px] flex-1 rounded-full border border-zinc-200 bg-white px-4 py-2 text-[11px] outline-none focus:border-zinc-400"
              />
              <button
                type="button"
                onClick={fetchPromptHistories}
                disabled={isPromptsLoading}
                className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-700 uppercase shadow-sm transition disabled:cursor-not-allowed disabled:text-zinc-400"
              >
                {isPromptsLoading ? (
                  <div className="flex items-center gap-2">
                    <LoadingSpinner size="sm" color="text-zinc-400" />
                    <span>Loading...</span>
                  </div>
                ) : (
                  "Search"
                )}
              </button>
            </div>

            {/* Prompt List */}
            {isPromptsLoading && promptHistories.length === 0 && (
              <div className="flex items-center justify-center py-12">
                <LoadingSpinner size="lg" color="text-zinc-400" />
              </div>
            )}

            {!isPromptsLoading && promptHistories.length === 0 && (
              <div className="rounded-2xl border border-dashed border-zinc-300 bg-zinc-50 p-12 text-center">
                <div className="text-3xl mb-3">📝</div>
                <div className="text-sm font-medium text-zinc-600 mb-1">No saved prompts yet</div>
                <div className="text-[11px] text-zinc-400">
                  Save prompts from SceneCard using the &quot;Save&quot; button
                </div>
              </div>
            )}

            {promptHistories.length > 0 && (
              <div className="grid gap-3">
                {promptHistories.map((prompt) => (
                  <div
                    key={prompt.id}
                    className="rounded-2xl border border-zinc-200 bg-white p-4 transition hover:border-zinc-300"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-semibold text-sm text-zinc-800 truncate">
                            {prompt.name}
                          </span>
                          {prompt.is_favorite && (
                            <span className="text-amber-500 text-xs">★</span>
                          )}
                          {prompt.avg_match_rate != null && (
                            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                              {prompt.avg_match_rate.toFixed(1)}%
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-zinc-500 line-clamp-2 mb-2">
                          {prompt.positive_prompt}
                        </p>
                        <div className="flex flex-wrap items-center gap-2 text-[10px] text-zinc-400">
                          <span>Used {prompt.use_count}x</span>
                          {prompt.character_id && (
                            <span className="rounded-full bg-violet-50 px-2 py-0.5 text-violet-600">
                              {characters.find((c: Character) => c.id === prompt.character_id)?.name ?? `Character #${prompt.character_id}`}
                            </span>
                          )}
                          {prompt.lora_settings && prompt.lora_settings.length > 0 && (
                            <span className="rounded-full bg-blue-50 px-2 py-0.5 text-blue-600">
                              {prompt.lora_settings.length} LoRA
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          type="button"
                          onClick={() => applyPromptHistory(prompt.id)}
                          className="rounded-full bg-emerald-500 px-3 py-1.5 text-[10px] font-semibold text-white transition hover:bg-emerald-600"
                          title="Apply to current scene"
                        >
                          Apply
                        </button>
                        <button
                          type="button"
                          onClick={() => togglePromptFavorite(prompt.id)}
                          className={`rounded-full p-2 text-xs transition ${prompt.is_favorite
                            ? "bg-amber-50 text-amber-500 hover:bg-amber-100"
                            : "bg-zinc-50 text-zinc-400 hover:bg-zinc-100"
                            }`}
                          title={prompt.is_favorite ? "Remove from favorites" : "Add to favorites"}
                        >
                          {prompt.is_favorite ? "★" : "☆"}
                        </button>
                        <button
                          type="button"
                          onClick={() => deletePromptHistory(prompt.id)}
                          disabled={deletingPromptId === prompt.id}
                          className="rounded-full bg-rose-50 p-2 text-xs text-rose-500 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-50"
                          title="Delete"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {manageTab === "evaluation" && (
          <section className="grid gap-6 rounded-2xl border border-zinc-200/60 bg-white p-6 text-xs text-zinc-600 shadow-sm">
            {/* Controls */}
            <div className="flex flex-wrap items-center gap-3">
              <select
                value={evalCharacterId ?? ""}
                onChange={(e) => setEvalCharacterId(e.target.value ? Number(e.target.value) : null)}
                className="rounded-full border border-zinc-200 bg-white px-3 py-2 text-xs"
              >
                <option value="">All Characters</option>
                {characters.map((c: Character) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
              <div className="flex items-center gap-1">
                <span className="text-[10px] text-zinc-500">Reps:</span>
                <input
                  type="number"
                  value={evalRepetitions}
                  onChange={(e) => setEvalRepetitions(Math.max(1, Math.min(10, Number(e.target.value))))}
                  min={1}
                  max={10}
                  className="w-12 rounded border border-zinc-200 px-2 py-1 text-center text-xs"
                />
              </div>
              <button
                type="button"
                onClick={runEvaluation}
                disabled={isEvalRunning || selectedTests.size === 0}
                className="rounded-full bg-indigo-600 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-white uppercase disabled:bg-indigo-300"
              >
                {isEvalRunning ? (
                  <span className="flex items-center gap-2">
                    <LoadingSpinner size="sm" color="text-white" />
                    Running...
                  </span>
                ) : (
                  `Run (${selectedTests.size})`
                )}
              </button>
              <button
                type="button"
                onClick={fetchEvalData}
                disabled={isEvalLoading}
                className="rounded-full border border-zinc-200 bg-white px-3 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
              >
                Refresh
              </button>
            </div>

            {/* Test Selection */}
            <div className="grid gap-3">
              <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                Test Prompts
              </span>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {testPrompts.map((test) => (
                  <label
                    key={test.name}
                    className={`flex cursor-pointer items-start gap-2 rounded-xl border p-3 transition ${selectedTests.has(test.name)
                      ? "border-indigo-300 bg-indigo-50"
                      : "border-zinc-200 bg-white hover:border-zinc-300"
                      }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedTests.has(test.name)}
                      onChange={(e) => {
                        const newSet = new Set(selectedTests);
                        if (e.target.checked) newSet.add(test.name);
                        else newSet.delete(test.name);
                        setSelectedTests(newSet);
                      }}
                      className="mt-0.5 rounded border-zinc-300"
                    />
                    <div className="flex-1">
                      <div className="text-xs font-medium text-zinc-800">{test.name.replace(/_/g, " ")}</div>
                      <div className="text-[10px] text-zinc-500">{test.description}</div>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {test.tokens.slice(0, 4).map((t) => (
                          <span key={t} className="rounded bg-zinc-100 px-1.5 py-0.5 text-[9px] text-zinc-600">
                            {t}
                          </span>
                        ))}
                        {test.tokens.length > 4 && (
                          <span className="text-[9px] text-zinc-400">+{test.tokens.length - 4}</span>
                        )}
                      </div>
                    </div>
                  </label>
                ))}
              </div>
              {testPrompts.length > 0 && (
                <button
                  type="button"
                  onClick={() => {
                    if (selectedTests.size === testPrompts.length) {
                      setSelectedTests(new Set());
                    } else {
                      setSelectedTests(new Set(testPrompts.map((t) => t.name)));
                    }
                  }}
                  className="text-[10px] text-indigo-600 hover:underline"
                >
                  {selectedTests.size === testPrompts.length ? "Deselect All" : "Select All"}
                </button>
              )}
            </div>

            {/* Results Summary */}
            {evalSummary && evalSummary.tests.length > 0 && (
              <div className="grid gap-3">
                <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                  Results Summary
                </span>

                {/* Overall Stats */}
                <div className="rounded-2xl border border-zinc-200 bg-white p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <span className="text-xs font-semibold text-zinc-800">Overall</span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${evalSummary.overall.winner === "lora"
                        ? "bg-emerald-100 text-emerald-700"
                        : evalSummary.overall.winner === "standard"
                          ? "bg-blue-100 text-blue-700"
                          : "bg-zinc-100 text-zinc-600"
                        }`}
                    >
                      {evalSummary.overall.winner === "tie"
                        ? "Tie"
                        : `${evalSummary.overall.winner.toUpperCase()} +${Math.abs(evalSummary.overall.diff * 100).toFixed(1)}%`}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="rounded-xl bg-blue-50 p-3 text-center">
                      <div className="text-[10px] font-semibold tracking-[0.2em] text-blue-600 uppercase">Standard</div>
                      <div className="text-lg font-bold text-blue-700">
                        {(evalSummary.overall.standard_avg * 100).toFixed(1)}%
                      </div>
                    </div>
                    <div className="rounded-xl bg-emerald-50 p-3 text-center">
                      <div className="text-[10px] font-semibold tracking-[0.2em] text-emerald-600 uppercase">LoRA</div>
                      <div className="text-lg font-bold text-emerald-700">
                        {(evalSummary.overall.lora_avg * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                </div>

                {/* Per-Test Results */}
                <div className="grid gap-2">
                  {evalSummary.tests.map((test) => (
                    <div
                      key={test.test_name}
                      className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white px-4 py-3"
                    >
                      <span className="text-xs font-medium text-zinc-700">
                        {test.test_name.replace(/_/g, " ")}
                      </span>
                      <div className="flex items-center gap-3">
                        <div className="text-right">
                          <span className="text-[10px] text-blue-600">STD</span>
                          <span className="ml-1 text-xs font-semibold text-zinc-700">
                            {test.standard_avg !== undefined ? `${(test.standard_avg * 100).toFixed(1)}%` : "-"}
                          </span>
                        </div>
                        <div className="text-right">
                          <span className="text-[10px] text-emerald-600">LoRA</span>
                          <span className="ml-1 text-xs font-semibold text-zinc-700">
                            {test.lora_avg !== undefined ? `${(test.lora_avg * 100).toFixed(1)}%` : "-"}
                          </span>
                        </div>
                        <span
                          className={`w-16 rounded-full px-2 py-0.5 text-center text-[10px] font-semibold ${test.winner === "lora"
                            ? "bg-emerald-100 text-emerald-700"
                            : test.winner === "standard"
                              ? "bg-blue-100 text-blue-700"
                              : "bg-zinc-100 text-zinc-500"
                            }`}
                        >
                          {test.winner === "tie" ? "Tie" : test.winner.toUpperCase()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>

                {evalLastBatchId && (
                  <div className="text-[10px] text-zinc-400">
                    Last batch: {evalLastBatchId}
                  </div>
                )}
              </div>
            )}

            {/* Empty State */}
            {!isEvalLoading && (!evalSummary || evalSummary.tests.length === 0) && (
              <div className="rounded-2xl border border-dashed border-zinc-300 bg-zinc-50 p-8 text-center">
                <div className="text-sm text-zinc-500">No evaluation data yet</div>
                <div className="mt-1 text-[10px] text-zinc-400">
                  Select tests above and click Run to compare Mode A vs B
                </div>
              </div>
            )}
          </section>
        )}

        {manageTab === "settings" && (
          <section className="grid gap-8 rounded-2xl border border-zinc-200/60 bg-white p-8 text-xs text-zinc-600 shadow-sm">
            {/* Storage Section */}
            <div className="grid gap-6">
              <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                  Workspace Storage
                </span>
                <button
                  type="button"
                  onClick={fetchStorageStats}
                  disabled={isLoadingStorage}
                  className="rounded-full bg-white border border-zinc-200 px-4 py-1.5 text-[10px] font-bold text-zinc-600 shadow-sm hover:bg-zinc-50 transition-colors disabled:opacity-50"
                >
                  {isLoadingStorage ? "Syncing..." : "Sync Stats"}
                </button>
              </div>

              {storageStats && (
                <div className="grid gap-6">
                  <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
                    <div className="mb-6 flex items-end justify-between">
                      <div>
                        <div className="text-3xl font-black text-zinc-900">
                          {storageStats.total_size_mb.toFixed(1)} <span className="text-sm font-bold text-zinc-400">MB</span>
                        </div>
                        <p className="mt-1 text-[11px] font-medium text-zinc-400 uppercase tracking-widest">Aggregate Usage</p>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-bold text-indigo-600">{storageStats.total_count}</div>
                        <p className="text-[10px] font-medium text-zinc-400">TOTAL OBJECTS</p>
                      </div>
                    </div>

                    {/* Visual Progress Bar */}
                    <div className="h-3 w-full flex rounded-full bg-zinc-100 overflow-hidden mb-8">
                      {Object.entries(storageStats.directories).map(([name, stats], idx) => {
                        const percent = (stats.size_mb / (storageStats.total_size_mb || 1)) * 100;
                        const colors = ["bg-indigo-500", "bg-emerald-500", "bg-amber-500", "bg-rose-500", "bg-sky-500"];
                        return (
                          <div
                            key={name}
                            style={{ width: `${percent}%` }}
                            className={`${colors[idx % colors.length]} h-full border-r border-white/20 last:border-0`}
                            title={`${name}: ${stats.size_mb.toFixed(1)} MB`}
                          />
                        );
                      })}
                    </div>

                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                      {Object.entries(storageStats.directories).map(([name, stats], idx) => {
                        const colors = ["bg-indigo-500", "bg-emerald-500", "bg-amber-500", "bg-rose-500", "bg-sky-500"];
                        return (
                          <div key={name} className="flex items-center gap-3 p-3 rounded-2xl border border-zinc-50 bg-zinc-50/50">
                            <div className={`h-2 w-2 rounded-full ${colors[idx % colors.length]}`} />
                            <div className="flex-1 min-w-0">
                              <p className="text-[10px] font-bold text-zinc-700 uppercase tracking-tighter truncate">{name}</p>
                              <p className="text-[11px] font-medium text-zinc-400">
                                {stats.size_mb.toFixed(1)} MB · {stats.count} items
                              </p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Cleanup Matrix */}
                  <div className="grid md:grid-cols-2 gap-6">
                    <div className="rounded-2xl border border-zinc-200 bg-white p-6">
                      <h4 className="mb-4 text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">Retention Policies</h4>
                      <div className="space-y-4">
                        <div className="flex items-center justify-between p-3 rounded-2xl bg-zinc-50/50 border border-zinc-50">
                          <label className="flex items-center gap-3 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={cleanupOptions.cleanup_videos}
                              onChange={(e) => setCleanupOptions(p => ({ ...p, cleanup_videos: e.target.checked }))}
                              className="h-4 w-4 rounded-lg border-zinc-300 text-indigo-600 focus:ring-indigo-500"
                            />
                            <div>
                              <p className="text-xs font-bold text-zinc-700">Video Retention</p>
                              <p className="text-[10px] text-zinc-400">Purge old video files from exports</p>
                            </div>
                          </label>
                          <div className="flex items-center gap-2 bg-white border border-zinc-200 rounded-xl px-2 py-1">
                            <input
                              type="number"
                              value={cleanupOptions.video_max_age_days}
                              onChange={(e) => setCleanupOptions(p => ({ ...p, video_max_age_days: Math.max(1, parseInt(e.target.value) || 1) }))}
                              className="w-8 text-center text-[10px] font-bold text-zinc-700 outline-none"
                            />
                            <span className="text-[9px] font-bold text-zinc-400">DAYS</span>
                          </div>
                        </div>

                        <label className="flex items-center justify-between p-3 rounded-2xl bg-zinc-50/50 border border-zinc-50 cursor-pointer">
                          <div className="flex items-center gap-3">
                            <input
                              type="checkbox"
                              checked={cleanupOptions.cleanup_cache}
                              onChange={(e) => setCleanupOptions(p => ({ ...p, cleanup_cache: e.target.checked }))}
                              className="h-4 w-4 rounded-lg border-zinc-300 text-indigo-600"
                            />
                            <div>
                              <p className="text-xs font-bold text-zinc-700">Cache Expiration</p>
                              <p className="text-[10px] text-zinc-400">Wipe transient data and temporary assets</p>
                            </div>
                          </div>
                        </label>

                        <label className="flex items-center justify-between p-3 rounded-2xl bg-zinc-50/50 border border-zinc-50 cursor-pointer">
                          <div className="flex items-center gap-3">
                            <input
                              type="checkbox"
                              checked={cleanupOptions.cleanup_test_folders}
                              onChange={(e) => setCleanupOptions(p => ({ ...p, cleanup_test_folders: e.target.checked }))}
                              className="h-4 w-4 rounded-lg border-zinc-300 text-indigo-600"
                            />
                            <div>
                              <p className="text-xs font-bold text-zinc-700">Test Artifacts</p>
                              <p className="text-[10px] text-zinc-400">Clean up experiment and test directories</p>
                            </div>
                          </div>
                        </label>
                      </div>

                      <div className="mt-6 flex gap-3">
                        <button
                          onClick={() => handleCleanup(true)}
                          disabled={isCleaningUp}
                          className="flex-1 rounded-2xl border border-zinc-200 px-4 py-3 text-[10px] font-bold uppercase tracking-widest text-zinc-500 hover:bg-zinc-50 transition-all"
                        >
                          Dry Run
                        </button>
                        <button
                          onClick={() => handleCleanup(false)}
                          disabled={isCleaningUp}
                          className="flex-1 rounded-2xl bg-zinc-900 px-4 py-3 text-[10px] font-bold uppercase tracking-widest text-white shadow-lg shadow-zinc-200 hover:bg-rose-600 transition-all disabled:bg-zinc-300"
                        >
                          {isCleaningUp ? "Cleaning..." : "Execute Purge"}
                        </button>
                      </div>
                    </div>

                    {/* Cleanup Result Box */}
                    <div className="rounded-2xl border border-zinc-200 bg-zinc-50/50 p-6">
                      <h4 className="mb-4 text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">Operation Result</h4>
                      {cleanupResult ? (
                        <div className="space-y-4">
                          <div className="rounded-2xl bg-white p-4 border border-zinc-100 shadow-sm">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-[10px] font-bold text-zinc-400 uppercase">Space Freed</span>
                              <span className="text-lg font-black text-emerald-600">{cleanupResult.freed_mb.toFixed(1)} MB</span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-bold text-zinc-400 uppercase">Objects Removed</span>
                              <span className="text-lg font-black text-indigo-600">{cleanupResult.deleted_count}</span>
                            </div>
                            {cleanupResult.dry_run && (
                              <div className="mt-3 rounded-lg bg-amber-50 p-2 text-center text-[9px] font-bold text-amber-600 uppercase tracking-tighter">
                                Simulated Results (Dry Run)
                              </div>
                            )}
                          </div>
                          <div className="max-h-[160px] overflow-y-auto pr-2 custom-scrollbar">
                            {Object.entries(cleanupResult.details).map(([dir, info]) => (
                              <div key={dir} className="flex items-center justify-between py-1.5 border-b border-zinc-100 last:border-0">
                                <span className="text-[10px] font-bold text-zinc-500 uppercase">{dir}</span>
                                <span className="text-[10px] font-medium text-zinc-400">-{info.freed_mb.toFixed(1)} MB</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <div className="flex h-full flex-col items-center justify-center py-12 text-center">
                          <div className="mb-3 text-2xl opacity-20">🍃</div>
                          <p className="text-[11px] font-medium text-zinc-400">Ready for maintenance cycle</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Render Settings Link */}
            <div className="grid gap-3 pt-4 border-t border-zinc-100">
              <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                Studio Configuration
              </span>
              <div className="flex flex-wrap items-center gap-4">
                <p className="text-[11px] text-zinc-500 italic max-w-sm">
                  Core rendering parameters and global stylization settings are managed within the main studio interface.
                </p>
                <Link
                  href="/"
                  className="rounded-full border border-indigo-200 bg-indigo-50/30 px-6 py-2.5 text-[10px] font-bold tracking-[0.1em] text-indigo-600 uppercase transition hover:bg-indigo-100"
                >
                  Return to Studio
                </Link>
              </div>
            </div>
          </section>
        )}

        {/* Enlarged Image Modal */}
        {enlargedImage && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm cursor-pointer"
            onClick={() => setEnlargedImage(null)}
          >
            <div
              className="relative max-w-[90vw] max-h-[90vh] cursor-default"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                onClick={() => setEnlargedImage(null)}
                className="absolute -top-3 -right-3 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-white text-zinc-600 shadow-lg hover:bg-zinc-100"
              >
                ✕
              </button>
              <img
                src={enlargedImage.url}
                alt={enlargedImage.title}
                className="max-w-[90vw] max-h-[85vh] rounded-2xl object-contain shadow-2xl"
              />
              <p className="mt-3 text-center text-sm font-medium text-white">{enlargedImage.title}</p>
            </div>
          </div>
        )}
        {/* Character Edit Modal */}
        {(editingCharacter || isCreatingCharacter) && (
          <CharacterEditModal
            character={editingCharacter || undefined}
            allTags={allTags}
            allLoras={loraEntries}
            onClose={() => {
              setEditingCharacter(null);
              setIsCreatingCharacter(false);
            }}
            onSave={handleSaveCharacter}
          />
        )}
        {/* LoRA Edit Modal */}
        {editingLora && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
            <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
              <div className="mb-6 flex items-center justify-between">
                <h2 className="text-xl font-bold text-zinc-800">Edit LoRA Settings</h2>
                <button onClick={() => setEditingLora(null)} className="text-zinc-400 hover:text-zinc-600">✕</button>
              </div>
              <form onSubmit={handleUpdateLora} className="space-y-4">
                <div>
                  <label className="block text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Display Name</label>
                  <input
                    type="text"
                    value={editingLora.display_name || ""}
                    onChange={(e) => setEditingLora({ ...editingLora, display_name: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-zinc-200 p-2 text-sm outline-none focus:border-indigo-400"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Trigger Words</label>
                  <textarea
                    rows={2}
                    placeholder="comma, separated, triggers"
                    defaultValue={editingLora.trigger_words?.join(", ") || ""}
                    onChange={(e) => {
                      const words = e.target.value.split(",").map(w => w.trim()).filter(w => w.length > 0);
                      setEditingLora(prev => prev ? ({ ...prev, trigger_words: words }) : null);
                    }}
                    className="mt-1 w-full rounded-xl border border-zinc-200 p-2 text-sm outline-none focus:border-indigo-400"
                  />
                  <p className="mt-1 text-[10px] text-zinc-400">Keywords that automatically activate this LoRA.</p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Calibrated (Optimal)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={editingLora.optimal_weight ?? ""}
                      onChange={(e) => setEditingLora({ ...editingLora, optimal_weight: parseFloat(e.target.value) })}
                      className="mt-1 w-full rounded-xl border border-zinc-200 p-2 text-sm outline-none focus:border-indigo-400"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Default Weight</label>
                    <input
                      type="number"
                      step="0.01"
                      value={editingLora.default_weight}
                      onChange={(e) => setEditingLora({ ...editingLora, default_weight: parseFloat(e.target.value) })}
                      className="mt-1 w-full rounded-xl border border-zinc-200 p-2 text-sm outline-none focus:border-indigo-400"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Min Weight</label>
                    <input
                      type="number"
                      step="0.1"
                      value={editingLora.weight_min}
                      onChange={(e) => setEditingLora({ ...editingLora, weight_min: parseFloat(e.target.value) })}
                      className="mt-1 w-full rounded-xl border border-zinc-200 p-2 text-sm outline-none focus:border-indigo-400"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Max Weight</label>
                    <input
                      type="number"
                      step="0.1"
                      value={editingLora.weight_max}
                      onChange={(e) => setEditingLora({ ...editingLora, weight_max: parseFloat(e.target.value) })}
                      className="mt-1 w-full rounded-xl border border-zinc-200 p-2 text-sm outline-none focus:border-indigo-400"
                    />
                  </div>
                </div>
                <div className="flex gap-2 pt-4">
                  <button
                    type="button"
                    onClick={() => setEditingLora(null)}
                    className="flex-1 rounded-xl border border-zinc-200 py-3 text-sm font-semibold text-zinc-600 hover:bg-zinc-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isUpdatingLora}
                    className="flex-1 rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-600/20 hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {isUpdatingLora ? "Updating..." : "Save Changes"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div >
  );
}
