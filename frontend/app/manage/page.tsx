"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type KeywordSuggestion = { tag: string; count: number };
type KeywordCategories = Record<string, string[]>;
type AudioItem = { name: string; url: string };
type FontItem = { name: string };
type LoraItem = { name: string; alias?: string };

const OVERLAY_STYLES = [
  { id: "overlay_minimal.png", label: "Minimal" },
];

export default function ManagePage() {
  const [manageTab, setManageTab] = useState<"keywords" | "assets" | "settings">("keywords");
  const [keywordSuggestions, setKeywordSuggestions] = useState<KeywordSuggestion[]>([]);
  const [keywordCategories, setKeywordCategories] = useState<KeywordCategories>({});
  const [keywordCategorySelection, setKeywordCategorySelection] = useState<Record<string, string>>({});
  const [keywordCategoryFilter, setKeywordCategoryFilter] = useState("");
  const [keywordSearch, setKeywordSearch] = useState("");
  const [keywordSort, setKeywordSort] = useState<"count_desc" | "count_asc" | "alpha">("count_desc");
  const [keywordPanelOpen, setKeywordPanelOpen] = useState(true);
  const [isKeywordLoading, setIsKeywordLoading] = useState(false);
  const [keywordError, setKeywordError] = useState("");
  const [keywordApproving, setKeywordApproving] = useState<Record<string, boolean>>({});
  const [bgmList, setBgmList] = useState<AudioItem[]>([]);
  const [fontList, setFontList] = useState<FontItem[]>([]);
  const [loraList, setLoraList] = useState<LoraItem[]>([]);
  const [isPreviewingBgm, setIsPreviewingBgm] = useState(false);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const previewTimeoutRef = useRef<number | null>(null);

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
        if (compressedTag && compressedTag === compressedValue) categoryScore = Math.max(categoryScore, 3);
        if (compressedTag && compressedValue.includes(compressedTag)) categoryScore = Math.max(categoryScore, 2);
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
  }, [keywordCategoryFilter, keywordCategorySelection, keywordSearch, keywordSort, keywordSuggestions]);

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
            <p className="text-xs uppercase tracking-[0.3em] text-zinc-500">Workspace Tools</p>
            <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">Manage</h1>
            <p className="max-w-xl text-sm text-zinc-600">
              Review keyword suggestions and manage assets.
            </p>
          </div>
          <Link
            href="/"
            className="rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600 shadow-sm"
          >
            Back to Studio
          </Link>
        </header>

        <div className="flex flex-wrap items-center gap-2">
          {[
            { id: "keywords", label: "Keywords" },
            { id: "assets", label: "Assets" },
            { id: "settings", label: "Settings" },
          ].map((tab) => {
            const active = manageTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setManageTab(tab.id as typeof manageTab)}
                className={`rounded-full px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] transition ${
                  active ? "bg-zinc-900 text-white" : "border border-zinc-200 bg-white text-zinc-600"
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
                className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600 shadow-sm transition"
              >
                {keywordPanelOpen ? "Collapse" : "Expand"}
              </button>
              <select
                value={keywordCategoryFilter}
                onChange={(e) => setKeywordCategoryFilter(e.target.value)}
                className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600 shadow-sm outline-none transition focus:border-zinc-400"
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
                className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600 shadow-sm outline-none transition focus:border-zinc-400"
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
                className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-700 shadow-sm transition disabled:cursor-not-allowed disabled:text-zinc-400"
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

                {!isKeywordLoading && keywordSuggestions.length > 0 && filteredKeywordSuggestions.length === 0 && (
                  <p className="text-xs text-zinc-500">No suggestions match the selected category.</p>
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
                            <span className="text-[10px] uppercase tracking-[0.2em] text-zinc-400">
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
                              className="rounded-full bg-zinc-900 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-white shadow-lg shadow-zinc-900/20 transition disabled:cursor-not-allowed disabled:bg-zinc-400"
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
              <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                Overlay Styles
              </span>
              <div className="grid gap-3 sm:grid-cols-2">
                {OVERLAY_STYLES.map((style) => (
                  <div key={style.id} className="flex flex-col gap-2 rounded-2xl border border-zinc-200 bg-white p-3">
                    <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600">
                      {style.label}
                    </span>
                    <div className="aspect-[9/16] w-full overflow-hidden rounded-xl bg-zinc-100">
                      <img
                        src={`${API_BASE}/assets/overlay/${style.id}`}
                        alt={`${style.label} frame`}
                        className="h-full w-full object-cover"
                      />
                    </div>
                    <span className="text-[10px] uppercase tracking-[0.2em] text-zinc-400">
                      {style.id}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
              <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                        className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600 disabled:cursor-not-allowed disabled:text-zinc-400"
                      >
                        {isPreviewingBgm ? "Playing..." : "Preview 10s"}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="grid gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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

        {manageTab === "settings" && (
          <section className="grid gap-3 rounded-3xl border border-white/60 bg-white/80 p-6 text-xs text-zinc-600 shadow-xl shadow-slate-200/40 backdrop-blur">
            <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-400">
              Settings are configured in the main studio page.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <Link
                href="/"
                className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600"
              >
                Open Render Settings
              </Link>
            </div>
          </section>
        )}
      </main>

    </div>
  );
}
