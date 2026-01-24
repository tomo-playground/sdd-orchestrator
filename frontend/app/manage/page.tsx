"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

import type { LoRA, SDModelEntry, Embedding, StyleProfile, StyleProfileFull, Character, Tag } from "../types";

type KeywordSuggestion = { tag: string; count: number };
type KeywordCategories = Record<string, string[]>;
type AudioItem = { name: string; url: string };
type FontItem = { name: string };
type LoraItem = { name: string; alias?: string };
type ManageTab = "keywords" | "assets" | "style" | "settings";

const OVERLAY_STYLES = [{ id: "overlay_minimal.png", label: "Minimal" }];

export default function ManagePage() {
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
  const [bgmList, setBgmList] = useState<AudioItem[]>([]);
  const [fontList, setFontList] = useState<FontItem[]>([]);
  const [loraList, setLoraList] = useState<LoraItem[]>([]);
  const [isPreviewingBgm, setIsPreviewingBgm] = useState(false);

  // Style tab state
  type StyleSubTab = "profiles" | "loras" | "characters" | "models" | "embeddings";
  const [styleSubTab, setStyleSubTab] = useState<StyleSubTab>("profiles");
  const [styleProfiles, setStyleProfiles] = useState<StyleProfile[]>([]);
  const [loraEntries, setLoraEntries] = useState<LoRA[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [sdModels, setSdModels] = useState<SDModelEntry[]>([]);
  const [embeddings, setEmbeddings] = useState<Embedding[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [isStyleLoading, setIsStyleLoading] = useState(false);
  const [civitaiSearch, setCivitaiSearch] = useState("");
  const [civitaiResults, setCivitaiResults] = useState<LoRA[]>([]);
  const [isSearchingCivitai, setIsSearchingCivitai] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState<StyleProfileFull | null>(null);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const previewTimeoutRef = useRef<number | null>(null);

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

  // Style tab data fetching
  const fetchStyleData = async () => {
    setIsStyleLoading(true);
    try {
      const [profilesRes, lorasRes, charsRes, modelsRes, embsRes, tagsRes] = await Promise.all([
        axios.get(`${API_BASE}/style-profiles`),
        axios.get(`${API_BASE}/loras`),
        axios.get(`${API_BASE}/characters`),
        axios.get(`${API_BASE}/sd-models`),
        axios.get(`${API_BASE}/embeddings`),
        axios.get(`${API_BASE}/tags`),
      ]);
      setStyleProfiles(profilesRes.data || []);
      setLoraEntries(lorasRes.data || []);
      setCharacters(charsRes.data || []);
      setSdModels(modelsRes.data || []);
      setEmbeddings(embsRes.data || []);
      setTags(tagsRes.data || []);
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
            next[item.tag] = suggestCategoryForTag(item.tag, categories);
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
    void refreshKeywordSuggestions();
  }, []);

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
    const category = keywordCategorySelection[tag];
    if (!category) {
      alert("Select a category first.");
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
    previewAudioRef.current = audio;
    setIsPreviewingBgm(true);
    audio.play().catch(() => {
      stopBgmPreview();
      alert("BGM preview failed.");
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
                className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase shadow-sm transition outline-none focus:border-zinc-400"
              >
                <option value="">All categories</option>
                {Object.keys(keywordCategories).map((category) => (
                  <option key={category} value={category}>
                    {category}
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
                {isKeywordLoading ? "Loading..." : "Refresh"}
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
                      const selected = keywordCategorySelection[item.tag] ?? "";
                      const canApprove = selected && !keywordApproving[item.tag];
                      return (
                        <div
                          key={item.tag}
                          className="grid gap-3 rounded-2xl border border-zinc-200 bg-white p-4 md:grid-cols-[1.4fr_1fr_auto]"
                        >
                          <div className="flex flex-col gap-1">
                            <span className="text-xs font-semibold text-zinc-800">{item.tag}</span>
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
                              <option value="">Select category</option>
                              {categoryOptions.map((category) => (
                                <option key={category} value={category}>
                                  {category}
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

        {manageTab === "assets" && (
          <section className="grid gap-6 rounded-3xl border border-white/60 bg-white/80 p-6 shadow-xl shadow-slate-200/40 backdrop-blur">
            <div className="grid gap-2">
              <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                Overlay Styles
              </span>
              <div className="grid gap-3 sm:grid-cols-2">
                {OVERLAY_STYLES.map((style) => (
                  <div
                    key={style.id}
                    className="flex flex-col gap-2 rounded-2xl border border-zinc-200 bg-white p-3"
                  >
                    <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase">
                      {style.label}
                    </span>
                    <div className="aspect-[9/16] w-full overflow-hidden rounded-xl bg-zinc-100">
                      <img
                        src={`${API_BASE}/assets/overlay/${style.id}`}
                        alt={`${style.label} frame`}
                        className="h-full w-full object-cover"
                      />
                    </div>
                    <span className="text-[10px] tracking-[0.2em] text-zinc-400 uppercase">
                      {style.id}
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
                {isStyleLoading ? "Loading..." : "Refresh"}
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
                      {isSearchingCivitai ? "Searching..." : "Search"}
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
                              <img src={lora.preview_image_url} alt="" className="h-10 w-10 rounded-lg object-cover" />
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
                    {characters.map((char) => {
                      const charLoras = char.loras?.map((cl) => {
                        const lora = loraEntries.find((l) => l.id === cl.lora_id);
                        return lora ? { ...lora, weight: cl.weight } : null;
                      }).filter(Boolean) || [];
                      const identityTagNames = char.identity_tags?.map((id) => tags.find((t) => t.id === id)?.name).filter(Boolean) || [];
                      const clothingTagNames = char.clothing_tags?.map((id) => tags.find((t) => t.id === id)?.name).filter(Boolean) || [];
                      return (
                        <div key={char.id} className="rounded-2xl border border-zinc-200 bg-white p-4">
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-3">
                              {char.preview_image_url ? (
                                <img src={char.preview_image_url} alt="" className="h-14 w-14 rounded-xl object-cover" />
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
                                    LoRA: {charLoras.map((l) => `${l?.display_name || l?.name}:${l?.weight}`).join(" + ")}
                                  </p>
                                )}
                              </div>
                            </div>
                            <button
                              onClick={() => deleteCharacter(char.id)}
                              className="text-[9px] text-rose-500 hover:underline"
                            >
                              Delete
                            </button>
                          </div>
                          <div className="mt-3 space-y-2">
                            {identityTagNames.length > 0 && (
                              <div>
                                <span className="text-[9px] font-semibold text-zinc-400 uppercase">Identity</span>
                                <div className="mt-1 flex flex-wrap gap-1">
                                  {identityTagNames.map((tag) => (
                                    <span key={tag} className="rounded-full bg-purple-100 px-2 py-0.5 text-[9px] text-purple-700">
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
                                    <span key={tag} className="rounded-full bg-amber-100 px-2 py-0.5 text-[9px] text-amber-700">
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
                  {isLoadingStorage ? "Loading..." : "Refresh"}
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
      </main>
    </div>
  );
}
