"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import axios from "axios";
import { API_BASE, CATEGORY_DESCRIPTIONS, PROMPT_APPLY_KEY } from "../constants";
import { useCharacters, useTags } from "../hooks";
import LoadingSpinner from "../components/ui/LoadingSpinner";
import QualityDashboard from "../components/quality/QualityDashboard";
import AnalyticsDashboard from "../components/analytics/AnalyticsDashboard";
import CharacterEditModal from "./CharacterEditModal";

import type { LoRA, SDModelEntry, Embedding, StyleProfile, StyleProfileFull, Character, Tag, PromptHistory } from "../types";

type KeywordSuggestion = {
  tag: string;
  count: number;
  suggested_category?: string;
  confidence?: number;
};
type KeywordCategories = Record<string, string[]>;
type AudioItem = { name: string; url: string };
type FontItem = { name: string };
type LoraItem = { name: string; alias?: string };
type ManageTab = "keywords" | "assets" | "style" | "tags" | "prompts" | "evaluation" | "quality" | "analytics" | "settings";

const OVERLAY_STYLES = [{ id: "overlay_minimal.png", label: "Minimal" }];

export default function ManagePage() {
  const router = useRouter();
  const { characters, reload: fetchCharacters } = useCharacters();
  const { tags: allTags, tagsByGroup: tagGroupsByCategory, reload: fetchTagsData } = useTags();

  const [manageTab, setManageTab] = useState<ManageTab>("keywords");
  const [keywordSuggestions, setKeywordSuggestions] = useState<KeywordSuggestion[]>([]);
  const [keywordCategories, setKeywordCategories] = useState<KeywordCategories>({});
  const [keywordCategorySelection, setKeywordCategorySelection] = useState<Record<string, string>>(
    {}
  );
  const [keywordCategoryFilter, setKeywordCategoryFilter] = useState("");
  const [keywordSearch, setKeywordSearch] = useState("");
  const [keywordSort, setKeywordSort] = useState<"count_desc" | "count_asc" | "alpha">(
    "count_desc"
  );
  const [keywordPanelOpen, setKeywordPanelOpen] = useState(true);
  const [isKeywordLoading, setIsKeywordLoading] = useState(false);
  const [keywordError, setKeywordError] = useState("");
  const [keywordApproving, setKeywordApproving] = useState<Record<string, boolean>>({});
  const [isRegeneratingChar, setIsRegeneratingChar] = useState<Record<number, boolean>>({});
  const [charImageTimestamps, setCharImageTimestamps] = useState<Record<number, number>>({});

  // Batch approval state
  type BatchPreview = {
    ready_count: number;
    skip_count: number;
    manual_count: number;
    ready_by_category: Record<string, Array<{ tag: string; confidence: number; suggested_category: string }>>;
    skip: Array<{ tag: string }>;
  };
  const [batchModalOpen, setBatchModalOpen] = useState(false);
  const [batchPreview, setBatchPreview] = useState<BatchPreview | null>(null);
  const [batchSelected, setBatchSelected] = useState<Set<string>>(new Set());
  const [isBatchLoading, setIsBatchLoading] = useState(false);
  const [isBatchApproving, setIsBatchApproving] = useState(false);
  const [enlargedImage, setEnlargedImage] = useState<{ url: string; title: string } | null>(null);
  const [bgmList, setBgmList] = useState<AudioItem[]>([]);
  const [fontList, setFontList] = useState<FontItem[]>([]);
  const [loraList, setLoraList] = useState<LoraItem[]>([]);
  const [isPreviewingBgm, setIsPreviewingBgm] = useState(false);

  // Style tab state
  type StyleSubTab = "profiles" | "loras" | "characters" | "models" | "embeddings";
  const [styleSubTab, setStyleSubTab] = useState<StyleSubTab>("profiles");
  const [editingCharacter, setEditingCharacter] = useState<Character | null>(null);
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

  const handleSaveCharacter = async (id: number, data: Partial<Character>) => {
    try {
      await axios.put(`${API_BASE}/characters/${id}`, data);
      await fetchStyleData();
      alert("Character updated successfully!");
    } catch (error) {
      console.error("Failed to update character", error);
      alert("Failed to update character");
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
      router.push("/");
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

  const normalizeKeyword = (value: string) =>
    value
      .toLowerCase()
      .replace(/[_-]/g, " ")
      .replace(/[^a-z0-9 ]/g, "")
      .trim();

  const compressKeyword = (value: string) => normalizeKeyword(value).replace(/\s+/g, "");

  const suggestCategoryForTag = (tag: string, categories: KeywordCategories) => {
    const normalizedTag = normalizeKeyword(tag);
    const compressedTag = compressKeyword(tag);
    const tagWords = normalizedTag.split(" ").filter(Boolean);
    let bestCategory = "";
    let bestScore = 0;

    Object.entries(categories).forEach(([category, values]) => {
      let categoryScore = 0;
      values.forEach((value) => {
        const normalizedValue = normalizeKeyword(value);
        const compressedValue = compressKeyword(value);
        if (!normalizedValue) return;
        if (normalizedTag === normalizedValue) categoryScore = Math.max(categoryScore, 4);
        if (compressedTag && compressedTag === compressedValue)
          categoryScore = Math.max(categoryScore, 3);
        if (compressedTag && compressedValue.includes(compressedTag))
          categoryScore = Math.max(categoryScore, 2);
        const valueWords = normalizedValue.split(" ").filter(Boolean);
        const overlap = tagWords.filter((word) => valueWords.includes(word)).length;
        if (overlap > 0) categoryScore = Math.max(categoryScore, 1 + overlap * 0.1);
      });
      if (categoryScore > bestScore) {
        bestScore = categoryScore;
        bestCategory = category;
      }
    });

    return bestScore > 0 ? bestCategory : "";
  };

  const refreshKeywordSuggestions = async () => {
    setIsKeywordLoading(true);
    setKeywordError("");
    try {
      const [suggestionsRes, categoriesRes] = await Promise.all([
        axios.get(`${API_BASE}/keywords/suggestions`),
        axios.get(`${API_BASE}/keywords/categories`),
      ]);
      const suggestions = (suggestionsRes.data.suggestions || []) as KeywordSuggestion[];
      const categories = (categoriesRes.data.categories || {}) as KeywordCategories;
      setKeywordSuggestions(suggestions);
      setKeywordCategories(categories);
      setKeywordCategorySelection((prev) => {
        const next = { ...prev };
        suggestions.forEach((item) => {
          if (!next[item.tag]) {
            // Use backend's suggested_category instead of frontend logic
            // Backend handles SKIP_TAGS and has more accurate patterns
            const suggested = item.suggested_category;
            // Don't auto-select "skip" category - leave as empty for manual review
            next[item.tag] = suggested === "skip" ? "" : (suggested || "");
          }
        });
        return next;
      });
    } catch {
      setKeywordError("Failed to load keyword suggestions.");
    } finally {
      setIsKeywordLoading(false);
    }
  };

  useEffect(() => {
    if (manageTab === "keywords") {
      void refreshKeywordSuggestions();
    }
  }, [manageTab]);

  const filteredKeywordSuggestions = useMemo(() => {
    const search = keywordSearch.trim().toLowerCase();
    let list = keywordSuggestions;
    if (keywordCategoryFilter) {
      list = list.filter((item) => keywordCategorySelection[item.tag] === keywordCategoryFilter);
    }
    if (search) {
      list = list.filter((item) => item.tag.toLowerCase().includes(search));
    }
    const sorted = [...list];
    if (keywordSort === "alpha") {
      sorted.sort((a, b) => a.tag.localeCompare(b.tag));
    } else if (keywordSort === "count_asc") {
      sorted.sort((a, b) => a.count - b.count);
    } else {
      sorted.sort((a, b) => b.count - a.count);
    }
    return sorted;
  }, [
    keywordCategoryFilter,
    keywordCategorySelection,
    keywordSearch,
    keywordSort,
    keywordSuggestions,
  ]);

  const handleApproveKeyword = async (tag: string) => {
    const suggestion = keywordSuggestions.find((s) => s.tag === tag);
    const category = keywordCategorySelection[tag] || suggestion?.suggested_category;
    if (!category || category === "skip") {
      alert("Select a valid category first (not skip).");
      return;
    }
    setKeywordApproving((prev) => ({ ...prev, [tag]: true }));
    try {
      await axios.post(`${API_BASE}/keywords/approve`, { tag, category });
      setKeywordSuggestions((prev) => prev.filter((item) => item.tag !== tag));
      setKeywordCategorySelection((prev) => {
        const next = { ...prev };
        delete next[tag];
        return next;
      });
      setKeywordCategories((prev) => {
        const next = { ...prev };
        const existing = Array.isArray(next[category]) ? next[category] : [];
        if (!existing.includes(tag)) {
          next[category] = [...existing, tag];
        }
        return next;
      });
    } catch {
      alert("Keyword approval failed.");
    } finally {
      setKeywordApproving((prev) => ({ ...prev, [tag]: false }));
    }
  };

  const openBatchModal = async () => {
    setIsBatchLoading(true);
    setBatchModalOpen(true);
    try {
      const res = await axios.get(`${API_BASE}/keywords/batch-approve/preview?limit=300`);
      setBatchPreview(res.data);
      // Pre-select all ready tags
      const allReady = new Set<string>();
      Object.values(res.data.ready_by_category || {}).forEach((items: unknown) => {
        (items as Array<{ tag: string }>).forEach((item) => allReady.add(item.tag));
      });
      setBatchSelected(allReady);
    } catch {
      alert("Failed to load batch preview");
      setBatchModalOpen(false);
    } finally {
      setIsBatchLoading(false);
    }
  };

  const handleBatchApprove = async () => {
    if (batchSelected.size === 0) return;
    setIsBatchApproving(true);
    try {
      const res = await axios.post(`${API_BASE}/keywords/batch-approve`, {
        tags: Array.from(batchSelected),
      });
      const { approved_count } = res.data;
      alert(`${approved_count} tags approved successfully!`);
      setBatchModalOpen(false);
      setBatchPreview(null);
      setBatchSelected(new Set());
      void refreshKeywordSuggestions();
    } catch {
      alert("Batch approval failed");
    } finally {
      setIsBatchApproving(false);
    }
  };

  const toggleBatchTag = (tag: string) => {
    setBatchSelected((prev) => {
      const next = new Set(prev);
      if (next.has(tag)) {
        next.delete(tag);
      } else {
        next.add(tag);
      }
      return next;
    });
  };

  const toggleCategorySelection = (category: string, items: Array<{ tag: string }>) => {
    const categoryTags = items.map((i) => i.tag);
    const allSelected = categoryTags.every((t) => batchSelected.has(t));
    setBatchSelected((prev) => {
      const next = new Set(prev);
      categoryTags.forEach((t) => {
        if (allSelected) {
          next.delete(t);
        } else {
          next.add(t);
        }
      });
      return next;
    });
  };

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
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#fff3db,_#f7f1ff_45%,_#e6f7ff_100%)] text-zinc-900">
      <main className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-6 py-10">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs tracking-[0.3em] text-zinc-500 uppercase">Workspace Tools</p>
            <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">Manage</h1>
            <p className="max-w-xl text-sm text-zinc-600">
              Review keyword suggestions and manage assets.
            </p>
          </div>
          <Link
            href="/"
            className="rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase shadow-sm"
          >
            Back to Studio
          </Link>
        </header>

        <div className="flex flex-wrap items-center gap-2">
          {[
            { id: "keywords", label: "Keywords" },
            { id: "assets", label: "Assets" },
            { id: "style", label: "Style" },
            { id: "tags", label: "Tags" },
            { id: "prompts", label: "Prompts" },
            { id: "evaluation", label: "Eval" },
            { id: "quality", label: "Quality" },
            { id: "analytics", label: "Analytics" },
            { id: "settings", label: "Settings" },
          ].map((tab) => {
            const active = manageTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setManageTab(tab.id as typeof manageTab)}
                className={`rounded-full px-4 py-2 text-[10px] font-semibold tracking-[0.2em] uppercase transition ${
                  active
                    ? "bg-zinc-900 text-white"
                    : "border border-zinc-200 bg-white text-zinc-600"
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {manageTab === "keywords" && (
          <section className="grid gap-4 rounded-3xl border border-white/60 bg-white/80 p-6 shadow-xl shadow-slate-200/40 backdrop-blur">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setKeywordPanelOpen((prev) => !prev)}
                className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase shadow-sm transition"
              >
                {keywordPanelOpen ? "Collapse" : "Expand"}
              </button>
              <select
                value={keywordCategoryFilter}
                onChange={(e) => setKeywordCategoryFilter(e.target.value)}
                className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-medium text-zinc-600 shadow-sm transition outline-none focus:border-zinc-400"
              >
                <option value="">All categories</option>
                {Object.keys(keywordCategories).map((category) => (
                  <option key={category} value={category}>
                    {category} {CATEGORY_DESCRIPTIONS?.[category] ? `- ${CATEGORY_DESCRIPTIONS[category]}` : ""}
                  </option>
                ))}
              </select>
              <select
                value={keywordSort}
                onChange={(e) =>
                  setKeywordSort(e.target.value as "count_desc" | "count_asc" | "alpha")
                }
                className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase shadow-sm transition outline-none focus:border-zinc-400"
              >
                <option value="count_desc">Count ↓</option>
                <option value="count_asc">Count ↑</option>
                <option value="alpha">A–Z</option>
              </select>
              <input
                value={keywordSearch}
                onChange={(e) => setKeywordSearch(e.target.value)}
                placeholder="Search tags"
                className="min-w-[140px] flex-1 rounded-full border border-zinc-200 bg-white px-4 py-2 text-[11px] outline-none focus:border-zinc-400"
              />
              <button
                onClick={refreshKeywordSuggestions}
                disabled={isKeywordLoading}
                className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-700 uppercase shadow-sm transition disabled:cursor-not-allowed disabled:text-zinc-400"
              >
                {isKeywordLoading ? (
                  <div className="flex items-center gap-2">
                    <LoadingSpinner size="sm" color="text-zinc-400" />
                    <span>Loading...</span>
                  </div>
                ) : (
                  "Refresh"
                )}
              </button>
              <button
                onClick={openBatchModal}
                className="rounded-full border border-emerald-300 bg-emerald-50 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-emerald-700 uppercase shadow-sm transition hover:bg-emerald-100"
              >
                Batch Approve
              </button>
            </div>

            {keywordPanelOpen && (
              <>
                {keywordError && (
                  <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-2 text-xs text-rose-600">
                    {keywordError}
                  </p>
                )}

                {!isKeywordLoading && keywordSuggestions.length === 0 && (
                  <p className="text-xs text-zinc-500">No keyword suggestions yet.</p>
                )}

                {!isKeywordLoading &&
                  keywordSuggestions.length > 0 &&
                  filteredKeywordSuggestions.length === 0 && (
                    <p className="text-xs text-zinc-500">
                      No suggestions match the selected category.
                    </p>
                  )}

                {filteredKeywordSuggestions.length > 0 && (
                  <div className="grid gap-3">
                    {filteredKeywordSuggestions.map((item) => {
                      const categoryOptions = Object.keys(keywordCategories);
                      const selected = keywordCategorySelection[item.tag] ?? item.suggested_category ?? "";
                      const isSkip = selected === "skip";
                      const canApprove = selected && !isSkip && !keywordApproving[item.tag];
                      return (
                        <div
                          key={item.tag}
                          className={`grid gap-3 rounded-2xl border p-4 md:grid-cols-[1.4fr_1fr_auto] ${
                            isSkip
                              ? "border-rose-200 bg-rose-50/50 opacity-60"
                              : "border-zinc-200 bg-white"
                          }`}
                        >
                          <div className="flex flex-col gap-1">
                            <div className="flex items-center gap-2">
                              <span className={`text-xs font-semibold ${isSkip ? "text-rose-600 line-through" : "text-zinc-800"}`}>
                                {item.tag}
                              </span>
                              {isSkip && (
                                <span className="rounded-full bg-rose-100 px-2 py-0.5 text-[9px] font-semibold text-rose-600 uppercase">
                                  Skip
                                </span>
                              )}
                            </div>
                            <span className="text-[10px] tracking-[0.2em] text-zinc-400 uppercase">
                              {item.count} hits
                            </span>
                          </div>
                          <div className="flex items-center">
                            <select
                              value={selected}
                              onChange={(e) =>
                                setKeywordCategorySelection((prev) => ({
                                  ...prev,
                                  [item.tag]: e.target.value,
                                }))
                              }
                              className="w-full rounded-2xl border border-zinc-200 bg-white px-3 py-2 text-xs outline-none focus:border-zinc-400"
                            >
                              <option value="">카테고리 선택</option>
                              {categoryOptions.map((category) => (
                                <option key={category} value={category}>
                                  {category} {CATEGORY_DESCRIPTIONS[category] ? `- ${CATEGORY_DESCRIPTIONS[category]}` : ""}
                                </option>
                              ))}
                            </select>
                          </div>
                          <div className="flex items-center">
                            <button
                              onClick={() => handleApproveKeyword(item.tag)}
                              disabled={!canApprove}
                              className="rounded-full bg-zinc-900 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-white uppercase shadow-lg shadow-zinc-900/20 transition disabled:cursor-not-allowed disabled:bg-zinc-400"
                            >
                              {keywordApproving[item.tag] ? "Approving..." : "Approve"}
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </>
            )}
          </section>
        )}

        {/* Batch Approve Modal */}
        {batchModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
            <div className="mx-4 max-h-[80vh] w-full max-w-2xl overflow-hidden rounded-3xl bg-white shadow-2xl">
              <div className="flex items-center justify-between border-b border-zinc-100 px-6 py-4">
                <div>
                  <h2 className="text-lg font-semibold text-zinc-900">Batch Approve Tags</h2>
                  {batchPreview && (
                    <p className="text-xs text-zinc-500">
                      {batchSelected.size} selected / {batchPreview.ready_count} ready / {batchPreview.skip_count} skip / {batchPreview.manual_count} manual
                    </p>
                  )}
                </div>
                <button
                  onClick={() => setBatchModalOpen(false)}
                  className="rounded-full p-2 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
                >
                  ✕
                </button>
              </div>

              <div className="max-h-[60vh] overflow-y-auto px-6 py-4">
                {isBatchLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <span className="text-sm text-zinc-500">Loading preview...</span>
                  </div>
                ) : batchPreview ? (
                  <div className="space-y-4">
                    {Object.entries(batchPreview.ready_by_category).map(([category, items]) => {
                      const categoryTags = items.map((i) => i.tag);
                      const allSelected = categoryTags.every((t) => batchSelected.has(t));
                      const someSelected = categoryTags.some((t) => batchSelected.has(t));
                      return (
                        <div key={category} className="rounded-xl border border-zinc-200 p-3">
                          <div className="mb-2 flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={allSelected}
                              ref={(el) => { if (el) el.indeterminate = someSelected && !allSelected; }}
                              onChange={() => toggleCategorySelection(category, items)}
                              className="h-4 w-4 rounded border-zinc-300"
                            />
                            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-700">
                              {category}
                            </span>
                            {CATEGORY_DESCRIPTIONS[category] && (
                              <span className="text-[10px] text-zinc-500">{CATEGORY_DESCRIPTIONS[category]}</span>
                            )}
                            <span className="text-[10px] text-zinc-400">({items.length})</span>
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {items.map((item) => (
                              <label
                                key={item.tag}
                                className={`flex cursor-pointer items-center gap-1 rounded-full border px-2 py-1 text-[10px] transition ${
                                  batchSelected.has(item.tag)
                                    ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                                    : "border-zinc-200 bg-zinc-50 text-zinc-500"
                                }`}
                              >
                                <input
                                  type="checkbox"
                                  checked={batchSelected.has(item.tag)}
                                  onChange={() => toggleBatchTag(item.tag)}
                                  className="sr-only"
                                />
                                {item.tag}
                                <span className="text-[9px] opacity-60">
                                  {Math.round(item.confidence * 100)}%
                                </span>
                              </label>
                            ))}
                          </div>
                        </div>
                      );
                    })}

                    {batchPreview.skip.length > 0 && (
                      <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-3">
                        <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
                          Auto-skipped ({batchPreview.skip.length})
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {batchPreview.skip.slice(0, 20).map((item) => (
                            <span
                              key={item.tag}
                              className="rounded-full border border-zinc-200 bg-white px-2 py-1 text-[10px] text-zinc-400"
                            >
                              {item.tag}
                            </span>
                          ))}
                          {batchPreview.skip.length > 20 && (
                            <span className="text-[10px] text-zinc-400">
                              +{batchPreview.skip.length - 20} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ) : null}
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-zinc-100 px-6 py-4">
                <button
                  onClick={() => setBatchModalOpen(false)}
                  className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-600"
                >
                  Cancel
                </button>
                <button
                  onClick={handleBatchApprove}
                  disabled={batchSelected.size === 0 || isBatchApproving}
                  className="rounded-full bg-emerald-600 px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isBatchApproving ? "Approving..." : `Approve ${batchSelected.size} Tags`}
                </button>
              </div>
            </div>
          </div>
        )}

        {manageTab === "assets" && (
          <section className="grid gap-6 rounded-3xl border border-white/60 bg-white/80 p-6 shadow-xl shadow-slate-200/40 backdrop-blur">
            <div className="grid gap-2">
              <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                Overlay Styles
              </span>
              <div className="grid gap-3 grid-cols-3 sm:grid-cols-4 lg:grid-cols-6">
                {OVERLAY_STYLES.map((style) => (
                  <div
                    key={style.id}
                    className="flex flex-col gap-1 rounded-xl border border-zinc-200 bg-white p-2"
                  >
                    <div className="aspect-[9/16] max-h-32 overflow-hidden rounded-lg bg-zinc-100">
                      <img
                        src={`${API_BASE}/assets/overlay/${style.id}`}
                        alt={`${style.label} frame`}
                        className="h-full w-full object-cover"
                      />
                    </div>
                    <span className="text-[9px] font-medium text-zinc-600 text-center truncate">
                      {style.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid gap-2">
              <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                Subtitle Fonts
              </span>
              {fontList.length === 0 ? (
                <p className="text-xs text-zinc-500">No fonts found.</p>
              ) : (
                <div className="grid gap-2 sm:grid-cols-2">
                  {fontList.map((font) => (
                    <div
                      key={font.name}
                      className="rounded-2xl border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-700"
                    >
                      {font.name}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="grid gap-2">
              <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                BGM Library
              </span>
              {bgmList.length === 0 ? (
                <p className="text-xs text-zinc-500">No audio files found.</p>
              ) : (
                <div className="grid gap-2">
                  {bgmList.map((bgm) => (
                    <div
                      key={bgm.name}
                      className="flex items-center justify-between gap-3 rounded-2xl border border-zinc-200 bg-white px-3 py-2"
                    >
                      <span className="text-xs text-zinc-700">{bgm.name}</span>
                      <button
                        type="button"
                        onClick={() => handlePreviewBgm(bgm.url)}
                        disabled={isPreviewingBgm}
                        className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase disabled:cursor-not-allowed disabled:text-zinc-400"
                      >
                        {isPreviewingBgm ? "Playing..." : "Preview 10s"}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="grid gap-2">
              <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                LoRA Library
              </span>
              {loraList.length === 0 ? (
                <p className="text-xs text-zinc-500">No LoRA files found.</p>
              ) : (
                <div className="grid gap-2 sm:grid-cols-2">
                  {loraList.map((lora) => {
                    const name = lora.alias || lora.name;
                    return (
                      <div
                        key={name}
                        className="flex items-center justify-between gap-3 rounded-2xl border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-700"
                      >
                        <span className="truncate">{name}</span>
                        <span className="rounded-full border border-zinc-200 px-2 py-0.5 text-[10px] text-zinc-500">
                          {`<lora:${name}:1.0>`}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </section>
        )}

        {manageTab === "style" && (
          <section className="grid gap-4 rounded-3xl border border-white/60 bg-white/80 p-6 shadow-xl shadow-slate-200/40 backdrop-blur">
            {/* Style Sub-tabs */}
            <div className="flex flex-wrap items-center gap-2 border-b border-zinc-200 pb-4">
              {[
                { id: "profiles", label: "Style Profiles" },
                { id: "loras", label: "LoRAs" },
                { id: "characters", label: "Characters" },
                { id: "models", label: "SD Models" },
                { id: "embeddings", label: "Embeddings" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setStyleSubTab(tab.id as StyleSubTab)}
                  className={`rounded-full px-3 py-1.5 text-[10px] font-semibold tracking-[0.15em] uppercase transition ${
                    styleSubTab === tab.id
                      ? "bg-zinc-800 text-white"
                      : "border border-zinc-200 bg-white text-zinc-500 hover:border-zinc-300"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
              <button
                onClick={fetchStyleData}
                disabled={isStyleLoading}
                className="ml-auto rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-[10px] font-semibold tracking-[0.15em] text-zinc-600 uppercase disabled:text-zinc-400"
              >
                {isStyleLoading ? (
                  <div className="flex items-center gap-2">
                    <LoadingSpinner size="sm" color="text-zinc-400" />
                    <span>Loading...</span>
                  </div>
                ) : (
                  "Refresh"
                )}
              </button>
            </div>

            {/* Style Profiles Sub-tab */}
            {styleSubTab === "profiles" && (
              <div className="grid gap-4">
                <p className="text-xs text-zinc-500">
                  Style profiles bundle SD model, LoRAs, embeddings, and default prompts.
                </p>
                {styleProfiles.length === 0 ? (
                  <p className="text-xs text-zinc-400">No style profiles found.</p>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2">
                    {styleProfiles.map((profile) => (
                      <div
                        key={profile.id}
                        className={`rounded-2xl border p-4 transition cursor-pointer ${
                          profile.is_default
                            ? "border-emerald-300 bg-emerald-50"
                            : "border-zinc-200 bg-white hover:border-zinc-300"
                        }`}
                        onClick={() => fetchProfileFull(profile.id)}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <h3 className="text-sm font-semibold text-zinc-800">
                              {profile.display_name || profile.name}
                            </h3>
                            <p className="mt-1 text-[10px] text-zinc-500">{profile.description || "No description"}</p>
                          </div>
                          <div className="flex flex-col gap-1">
                            {profile.is_default && (
                              <span className="rounded-full bg-emerald-500 px-2 py-0.5 text-[9px] font-semibold text-white">
                                DEFAULT
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="mt-3 flex flex-wrap items-center gap-2">
                          {!profile.is_default && (
                            <button
                              onClick={(e) => { e.stopPropagation(); setDefaultProfile(profile.id); }}
                              className="rounded-full border border-zinc-200 bg-white px-2 py-1 text-[9px] font-semibold text-zinc-600 hover:bg-zinc-50"
                            >
                              Set Default
                            </button>
                          )}
                          <button
                            onClick={(e) => { e.stopPropagation(); deleteStyleProfile(profile.id); }}
                            className="rounded-full border border-rose-200 bg-white px-2 py-1 text-[9px] font-semibold text-rose-600 hover:bg-rose-50"
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
            )}

            {/* LoRAs Sub-tab */}
            {styleSubTab === "loras" && (
              <div className="grid gap-4">
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
                          <div className="flex items-center gap-3">
                            {result.preview_image_url && (
                              <img src={result.preview_image_url} alt="" className="h-12 w-12 rounded-lg object-cover" />
                            )}
                            <div>
                              <p className="text-xs font-semibold text-zinc-700">{result.display_name || result.name}</p>
                              <p className="text-[10px] text-zinc-400">
                                {result.trigger_words?.slice(0, 3).join(", ") || "No trigger words"}
                              </p>
                            </div>
                          </div>
                          <button
                            onClick={() => importFromCivitai(result.civitai_id!)}
                            className="rounded-full bg-emerald-500 px-3 py-1.5 text-[9px] font-semibold text-white"
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
                        <div key={lora.id} className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-white p-3">
                          <div className="flex items-center gap-3">
                            {lora.preview_image_url ? (
                              <img src={`${API_BASE}${lora.preview_image_url}`} alt="" className="h-10 w-10 rounded-lg object-cover" />
                            ) : (
                              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-zinc-100 text-zinc-400">
                                <span className="text-lg">L</span>
                              </div>
                            )}
                            <div>
                              <p className="text-xs font-semibold text-zinc-700">{lora.display_name || lora.name}</p>
                              <p className="text-[10px] text-zinc-400">
                                Weight: {lora.weight_min}~{lora.weight_max} (default: {lora.default_weight})
                              </p>
                              {lora.optimal_weight !== null && (
                                <p className="text-[10px] text-emerald-600">
                                  ✅ Calibrated: {lora.optimal_weight} ({lora.calibration_score}%)
                                </p>
                              )}
                              {lora.optimal_weight === null && (
                                <p className="text-[10px] text-amber-500">
                                  ⚠️ Not calibrated
                                </p>
                              )}
                            </div>
                          </div>
                          <button
                            onClick={() => deleteLoRA(lora.id)}
                            className="rounded-full border border-rose-200 px-2 py-1 text-[9px] font-semibold text-rose-600"
                          >
                            Delete
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Characters Sub-tab */}
            {styleSubTab === "characters" && (
              <div className="grid gap-4">
                <p className="text-xs text-zinc-500">
                  Character presets bundle identity tags, clothing, and LoRA settings.
                </p>
                {characters.length === 0 ? (
                  <p className="text-xs text-zinc-400">No characters created yet.</p>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                    {characters.map((char: Character) => {
                      const charLoras = char.loras?.map((cl: any) => {
                        const lora = loraEntries.find((l) => l.id === cl.lora_id);
                        return lora ? { ...lora, weight: cl.weight } : null;
                      }).filter(Boolean) || [];
                      const identityTagNames = char.identity_tags?.map((id: number) => allTags.find((t: Tag) => t.id === id)?.name).filter(Boolean) || [];
                      const clothingTagNames = char.clothing_tags?.map((id: number) => allTags.find((t: Tag) => t.id === id)?.name).filter(Boolean) || [];
                      return (
                        <div key={char.id} className="rounded-2xl border border-zinc-200 bg-white p-4">
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-3">
                              {char.preview_image_url ? (
                                <img
                                  src={`${API_BASE}${char.preview_image_url}${charImageTimestamps[char.id] ? `?t=${charImageTimestamps[char.id]}` : ""}`}
                                  alt=""
                                  className="h-14 w-14 rounded-xl object-cover cursor-pointer hover:ring-2 hover:ring-indigo-400 transition-all"
                                  onClick={() => setEnlargedImage({ url: `${API_BASE}${char.preview_image_url}${charImageTimestamps[char.id] ? `?t=${charImageTimestamps[char.id]}` : ""}`, title: char.name })}
                                />
                              ) : (
                                <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-purple-100 to-pink-100 text-2xl">
                                  {char.name.charAt(0).toUpperCase()}
                                </div>
                              )}
                              <div>
                                <h3 className="text-sm font-semibold text-zinc-800">{char.name}</h3>
                                {char.description && (
                                  <p className="text-[10px] text-zinc-400">{char.description}</p>
                                )}
                                {charLoras.length > 0 && (
                                  <p className="text-[10px] text-zinc-500">
                                    LoRA: {charLoras.map((l: any) => `${l?.display_name || l?.name}:${l?.weight}`).join(" + ")}
                                  </p>
                                )}
                              </div>
                            </div>
                            <div className="flex flex-col gap-2 items-end">
                              <button
                                onClick={() => setEditingCharacter(char)}
                                className="text-[9px] text-zinc-500 hover:text-zinc-800 hover:underline"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleRegenerateReference(char.id)}
                                disabled={isRegeneratingChar[char.id]}
                                className="text-[9px] text-indigo-500 hover:underline disabled:opacity-50"
                              >
                                {isRegeneratingChar[char.id] ? "Regen..." : "Regenerate"}
                              </button>
                              <button
                                onClick={() => deleteCharacter(char.id)}
                                className="text-[9px] text-rose-500 hover:underline"
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                          <div className="mt-3 space-y-2">
                            {identityTagNames.length > 0 && (
                              <div>
                                <span className="text-[9px] font-semibold text-zinc-400 uppercase">Identity</span>
                                <div className="mt-1 flex flex-wrap gap-1">
                                  {identityTagNames.map((tag) => (
                                    <span key={tag!} className="rounded-full bg-purple-100 px-2 py-0.5 text-[9px] text-purple-700">
                                      {tag}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                            {clothingTagNames.length > 0 && (
                              <div>
                                <span className="text-[9px] font-semibold text-zinc-400 uppercase">Clothing</span>
                                <div className="mt-1 flex flex-wrap gap-1">
                                  {clothingTagNames.map((tag) => (
                                    <span key={tag!} className="rounded-full bg-amber-100 px-2 py-0.5 text-[9px] text-amber-700">
                                      {tag}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* SD Models Sub-tab */}
            {styleSubTab === "models" && (
              <div className="grid gap-4">
                <p className="text-xs text-zinc-500">
                  Registered SD model checkpoints.
                </p>
                {sdModels.length === 0 ? (
                  <p className="text-xs text-zinc-400">No SD models registered.</p>
                ) : (
                  <div className="grid gap-2">
                    {sdModels.map((model) => (
                      <div key={model.id} className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-white p-4">
                        <div>
                          <h3 className="text-sm font-semibold text-zinc-800">{model.display_name || model.name}</h3>
                          <p className="text-[10px] text-zinc-500">
                            {model.base_model || "Unknown"} • {model.model_type}
                          </p>
                          {model.description && (
                            <p className="mt-1 text-xs text-zinc-400">{model.description}</p>
                          )}
                        </div>
                        <span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${
                          model.is_active ? "bg-emerald-100 text-emerald-700" : "bg-zinc-100 text-zinc-500"
                        }`}>
                          {model.is_active ? "Active" : "Inactive"}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Embeddings Sub-tab */}
            {styleSubTab === "embeddings" && (
              <div className="grid gap-4">
                <p className="text-xs text-zinc-500">
                  Textual inversion embeddings for quality control.
                </p>
                {embeddings.length === 0 ? (
                  <p className="text-xs text-zinc-400">No embeddings registered.</p>
                ) : (
                  <div className="grid gap-2 md:grid-cols-2">
                    {embeddings.map((emb) => (
                      <div key={emb.id} className="rounded-2xl border border-zinc-200 bg-white p-3">
                        <div className="flex items-center justify-between">
                          <h3 className="text-xs font-semibold text-zinc-800">{emb.display_name || emb.name}</h3>
                          <span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${
                            emb.embedding_type === "negative" ? "bg-rose-100 text-rose-700" : "bg-emerald-100 text-emerald-700"
                          }`}>
                            {emb.embedding_type}
                          </span>
                        </div>
                        {emb.trigger_word && (
                          <p className="mt-1 font-mono text-[10px] text-zinc-500">{emb.trigger_word}</p>
                        )}
                        {emb.description && (
                          <p className="mt-1 text-[10px] text-zinc-400">{emb.description}</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </section>
        )}

        {manageTab === "tags" && (
          <section className="grid gap-6 rounded-3xl border border-white/60 bg-white/80 p-6 text-xs text-zinc-600 shadow-xl shadow-slate-200/40 backdrop-blur">
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
                      className={`rounded-xl border p-3 text-center transition ${
                        isActive
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
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {Object.keys(tagGroupsByCategory).filter(cat => cat !== "scene").map((group: string) => {
                  const count = allTags.filter(
                    (t: Tag) => t.category === "character" && t.group_name === group
                  ).length;
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
                      className={`rounded-xl border p-3 text-center transition ${
                        isActive
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
                <div className="text-2xl font-bold text-emerald-600">
                  {allTags.filter((t: Tag) => t.category === "quality").length}
                </div>
                <div className="text-[9px] font-medium uppercase tracking-wider text-zinc-400">Quality Tags</div>
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
                      {Object.keys(tagGroupsByCategory).map((group: string) => {
                        const groupTags = allTags.filter(
                          (t: Tag) => t.category === category && (group === "" ? !t.group_name : t.group_name === group)
                        );
                        if (groupTags.length === 0) return null;
                        return (
                          <div key={group || "ungrouped"} className="mb-3">
                            <div className="mb-2 text-[9px] font-medium uppercase tracking-wider text-zinc-400">
                              {group || "Ungrouped"} ({groupTags.length})
                            </div>
                            <div className="flex flex-wrap gap-1">
                              {groupTags.map((tag: Tag) => (
                                <span
                                  key={tag.id}
                                  className="rounded-full border border-zinc-100 bg-zinc-50 px-2 py-0.5 text-[9px] text-zinc-500"
                                >
                                  {tag.name}
                                </span>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </details>
                ))}
              </div>
            )}
          </section>
        )}

        {manageTab === "prompts" && (
          <section className="grid gap-4 rounded-3xl border border-white/60 bg-white/80 p-6 shadow-xl shadow-slate-200/40 backdrop-blur">
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
                          className={`rounded-full p-2 text-xs transition ${
                            prompt.is_favorite
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
          <section className="grid gap-6 rounded-3xl border border-white/60 bg-white/80 p-6 text-xs text-zinc-600 shadow-xl shadow-slate-200/40 backdrop-blur">
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
                    className={`flex cursor-pointer items-start gap-2 rounded-xl border p-3 transition ${
                      selectedTests.has(test.name)
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
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        evalSummary.overall.winner === "lora"
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
                          className={`w-16 rounded-full px-2 py-0.5 text-center text-[10px] font-semibold ${
                            test.winner === "lora"
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

        {manageTab === "quality" && <QualityDashboard />}

        {manageTab === "analytics" && <AnalyticsDashboard />}

        {manageTab === "settings" && (
          <section className="grid gap-6 rounded-3xl border border-white/60 bg-white/80 p-6 text-xs text-zinc-600 shadow-xl shadow-slate-200/40 backdrop-blur">
            {/* Storage Section */}
            <div className="grid gap-4">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                  Storage
                </span>
                <button
                  type="button"
                  onClick={fetchStorageStats}
                  disabled={isLoadingStorage}
                  className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase disabled:cursor-not-allowed disabled:text-zinc-400"
                >
                  {isLoadingStorage ? (
                    <div className="flex items-center gap-2">
                      <LoadingSpinner size="sm" color="text-zinc-400" />
                      <span>Loading...</span>
                    </div>
                  ) : (
                    "Refresh"
                  )}
                </button>
              </div>

              {storageStats && (
                <div className="grid gap-3">
                  <div className="rounded-2xl border border-zinc-200 bg-white p-4">
                    <div className="mb-3 flex items-baseline justify-between">
                      <span className="text-sm font-semibold text-zinc-800">
                        {storageStats.total_size_mb.toFixed(1)} MB
                      </span>
                      <span className="text-[10px] text-zinc-400">
                        {storageStats.total_count} files
                      </span>
                    </div>
                    <div className="grid gap-2">
                      {Object.entries(storageStats.directories).map(([name, stats]) => (
                        <div key={name} className="flex items-center justify-between text-xs">
                          <span className="text-zinc-600">{name}</span>
                          <span className="text-zinc-400">
                            {stats.count} files · {stats.size_mb.toFixed(1)} MB
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Cleanup Options */}
                  <div className="rounded-2xl border border-zinc-200 bg-white p-4">
                    <span className="mb-3 block text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                      Cleanup Options
                    </span>
                    <div className="grid gap-2">
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={cleanupOptions.cleanup_videos}
                          onChange={(e) =>
                            setCleanupOptions((prev) => ({
                              ...prev,
                              cleanup_videos: e.target.checked,
                            }))
                          }
                          className="rounded border-zinc-300"
                        />
                        <span className="text-xs text-zinc-600">
                          Videos older than{" "}
                          <input
                            type="number"
                            value={cleanupOptions.video_max_age_days}
                            onChange={(e) =>
                              setCleanupOptions((prev) => ({
                                ...prev,
                                video_max_age_days: Math.max(1, parseInt(e.target.value) || 1),
                              }))
                            }
                            min={1}
                            className="w-12 rounded border border-zinc-200 px-1 py-0.5 text-center text-xs"
                          />{" "}
                          days
                        </span>
                      </label>
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={cleanupOptions.cleanup_cache}
                          onChange={(e) =>
                            setCleanupOptions((prev) => ({
                              ...prev,
                              cleanup_cache: e.target.checked,
                            }))
                          }
                          className="rounded border-zinc-300"
                        />
                        <span className="text-xs text-zinc-600">Expired cache files</span>
                      </label>
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={cleanupOptions.cleanup_test_folders}
                          onChange={(e) =>
                            setCleanupOptions((prev) => ({
                              ...prev,
                              cleanup_test_folders: e.target.checked,
                            }))
                          }
                          className="rounded border-zinc-300"
                        />
                        <span className="text-xs text-zinc-600">Test folders</span>
                      </label>
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={cleanupOptions.cleanup_candidates}
                          onChange={(e) =>
                            setCleanupOptions((prev) => ({
                              ...prev,
                              cleanup_candidates: e.target.checked,
                            }))
                          }
                          className="rounded border-zinc-300"
                        />
                        <span className="text-xs text-zinc-600">Candidate images</span>
                      </label>
                    </div>
                    <div className="mt-4 flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleCleanup(true)}
                        disabled={isCleaningUp}
                        className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase disabled:cursor-not-allowed disabled:text-zinc-400"
                      >
                        {isCleaningUp ? "Analyzing..." : "Preview"}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleCleanup(false)}
                        disabled={isCleaningUp}
                        className="rounded-full bg-rose-600 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-white uppercase shadow-lg shadow-rose-600/20 disabled:cursor-not-allowed disabled:bg-rose-400"
                      >
                        {isCleaningUp ? "Cleaning..." : "Clean Up"}
                      </button>
                    </div>
                  </div>

                  {/* Cleanup Result */}
                  {cleanupResult && (
                    <div
                      className={`rounded-2xl border p-4 ${
                        cleanupResult.dry_run
                          ? "border-amber-200 bg-amber-50"
                          : "border-emerald-200 bg-emerald-50"
                      }`}
                    >
                      <div className="mb-2 flex items-baseline justify-between">
                        <span
                          className={`text-[10px] font-semibold tracking-[0.2em] uppercase ${
                            cleanupResult.dry_run ? "text-amber-600" : "text-emerald-600"
                          }`}
                        >
                          {cleanupResult.dry_run ? "Preview Result" : "Cleanup Complete"}
                        </span>
                        <span
                          className={`text-sm font-semibold ${
                            cleanupResult.dry_run ? "text-amber-700" : "text-emerald-700"
                          }`}
                        >
                          {cleanupResult.freed_mb.toFixed(1)} MB{" "}
                          {cleanupResult.dry_run ? "to free" : "freed"}
                        </span>
                      </div>
                      <div className="grid gap-1 text-xs">
                        {Object.entries(cleanupResult.details).map(([category, detail]) => (
                          <div key={category} className="flex items-center justify-between">
                            <span className="text-zinc-600">{category}</span>
                            <span className="text-zinc-500">
                              {detail.deleted} files · {detail.freed_mb.toFixed(1)} MB
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Original Settings Link */}
            <div className="grid gap-2">
              <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                Render Settings
              </span>
              <p className="text-[10px] tracking-[0.2em] text-zinc-400 uppercase">
                Settings are configured in the main studio page.
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <Link
                  href="/"
                  className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
                >
                  Open Render Settings
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
        {editingCharacter && (
          <CharacterEditModal
            character={editingCharacter}
            allTags={allTags}
            allLoras={loraEntries}
            onClose={() => setEditingCharacter(null)}
            onSave={handleSaveCharacter}
          />
        )}
      </main>
    </div>
  );
}
