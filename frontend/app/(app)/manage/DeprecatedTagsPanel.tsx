"use client";

import { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import LoadingSpinner from "../../components/ui/LoadingSpinner";

interface DeprecatedTag {
  id: number;
  name: string;
  category: string;
  deprecated_reason: string;
  replacement: { id: number; name: string; category: string } | null;
  created_at: string;
  updated_at: string;
}

interface DeprecatedTagsResponse {
  total: number;
  tags: DeprecatedTag[];
}

interface TagSearchResult {
  id: number;
  name: string;
  category: string | null;
}

export default function DeprecatedTagsPanel() {
  const [deprecatedTags, setDeprecatedTags] = useState<DeprecatedTag[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Deprecate form state
  const [showForm, setShowForm] = useState(false);
  const [tagQuery, setTagQuery] = useState("");
  const [tagResults, setTagResults] = useState<TagSearchResult[]>([]);
  const [selectedTag, setSelectedTag] = useState<TagSearchResult | null>(null);
  const [reason, setReason] = useState("");
  const [replacementQuery, setReplacementQuery] = useState("");
  const [replacementResults, setReplacementResults] = useState<TagSearchResult[]>([]);
  const [selectedReplacement, setSelectedReplacement] = useState<TagSearchResult | null>(null);
  const [isDeprecating, setIsDeprecating] = useState(false);

  const fetchDeprecatedTags = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await axios.get<DeprecatedTagsResponse>(`${API_BASE}/admin/tags/deprecated`);
      setDeprecatedTags(response.data.tags);
    } catch (err) {
      console.error("Failed to fetch deprecated tags:", err);
      setError("Failed to load deprecated tags");
    } finally {
      setIsLoading(false);
    }
  };

  const handleActivateTag = async (tagId: number) => {
    if (!confirm("Are you sure you want to reactivate this tag?")) return;
    try {
      await axios.put(`${API_BASE}/admin/tags/${tagId}/activate`);
      await fetchDeprecatedTags();
    } catch (err) {
      console.error("Failed to activate tag:", err);
      alert("Failed to activate tag");
    }
  };

  const searchTags = useCallback(async (query: string, setter: (r: TagSearchResult[]) => void) => {
    if (query.length < 1) {
      setter([]);
      return;
    }
    try {
      const res = await axios.get<TagSearchResult[]>(`${API_BASE}/tags/search`, {
        params: { q: query, limit: 8 },
      });
      setter(res.data);
    } catch {
      setter([]);
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => searchTags(tagQuery, setTagResults), 250);
    return () => clearTimeout(t);
  }, [tagQuery, searchTags]);

  useEffect(() => {
    const t = setTimeout(() => searchTags(replacementQuery, setReplacementResults), 250);
    return () => clearTimeout(t);
  }, [replacementQuery, searchTags]);

  const handleDeprecate = async () => {
    if (!selectedTag || !reason.trim()) return;
    if (!confirm(`Deprecate tag "${selectedTag.name}"?`)) return;

    setIsDeprecating(true);
    try {
      await axios.put(`${API_BASE}/admin/tags/${selectedTag.id}/deprecate`, {
        deprecated_reason: reason.trim(),
        replacement_tag_id: selectedReplacement?.id ?? null,
      });
      resetForm();
      await fetchDeprecatedTags();
    } catch (err) {
      console.error("Failed to deprecate tag:", err);
      alert("Failed to deprecate tag");
    } finally {
      setIsDeprecating(false);
    }
  };

  const resetForm = () => {
    setShowForm(false);
    setTagQuery("");
    setTagResults([]);
    setSelectedTag(null);
    setReason("");
    setReplacementQuery("");
    setReplacementResults([]);
    setSelectedReplacement(null);
  };

  useEffect(() => {
    fetchDeprecatedTags();
  }, []);

  return (
    <section className="grid gap-4 rounded-2xl border border-orange-200/60 bg-orange-50/30 p-6 text-xs text-zinc-600">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-[10px] font-semibold tracking-[0.2em] text-orange-600 uppercase">
            Deprecated Tags
          </span>
          <p className="mt-1 text-[10px] text-zinc-500">
            Tags that have been marked as deprecated and will be auto-replaced in prompts
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowForm(!showForm)}
            className="rounded-full border border-orange-300 bg-white px-3 py-1 text-[10px] font-semibold tracking-[0.1em] text-orange-600 uppercase hover:bg-orange-50"
          >
            {showForm ? "Cancel" : "+ Deprecate a Tag"}
          </button>
          <button
            type="button"
            onClick={fetchDeprecatedTags}
            disabled={isLoading}
            className="rounded-full border border-orange-300 bg-white px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-orange-600 uppercase hover:bg-orange-50 disabled:opacity-50"
          >
            {isLoading ? (
              <div className="flex items-center gap-2">
                <LoadingSpinner size="sm" color="text-orange-400" />
                <span>Loading...</span>
              </div>
            ) : (
              "Refresh"
            )}
          </button>
        </div>
      </div>

      {/* Deprecate Form */}
      {showForm && (
        <div className="space-y-4 rounded-xl border border-orange-200 bg-white p-4">
          {/* Tag Search */}
          <div>
            <label className="mb-1 block text-[10px] font-bold text-zinc-500 uppercase">
              Tag to Deprecate
            </label>
            {selectedTag ? (
              <div className="flex items-center gap-2">
                <span className="rounded-md bg-orange-100 px-2 py-1 font-mono text-xs font-semibold text-orange-700">
                  {selectedTag.name}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedTag(null);
                    setTagQuery("");
                  }}
                  className="text-[10px] text-zinc-400 hover:text-zinc-600"
                >
                  change
                </button>
              </div>
            ) : (
              <div className="relative">
                <input
                  type="text"
                  value={tagQuery}
                  onChange={(e) => setTagQuery(e.target.value)}
                  placeholder="Search tag name..."
                  className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-xs outline-none focus:border-orange-300"
                />
                {tagResults.length > 0 && (
                  <div className="absolute z-[var(--z-dropdown)] mt-1 max-h-[160px] w-full overflow-y-auto rounded-lg border border-zinc-200 bg-white shadow-lg">
                    {tagResults.map((t) => (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => {
                          setSelectedTag(t);
                          setTagQuery("");
                          setTagResults([]);
                        }}
                        className="flex w-full items-center gap-2 border-b border-zinc-50 px-3 py-2 text-left last:border-0 hover:bg-zinc-50"
                      >
                        <span className="font-mono text-[11px] font-semibold text-zinc-700">
                          {t.name}
                        </span>
                        {t.category && (
                          <span className="text-[9px] text-zinc-400">{t.category}</span>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Reason */}
          <div>
            <label className="mb-1 block text-[10px] font-bold text-zinc-500 uppercase">
              Reason
            </label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Why is this tag deprecated?"
              className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-xs outline-none focus:border-orange-300"
            />
          </div>

          {/* Replacement Tag (optional) */}
          <div>
            <label className="mb-1 block text-[10px] font-bold text-zinc-500 uppercase">
              Replacement Tag <span className="text-zinc-400 normal-case">(optional)</span>
            </label>
            {selectedReplacement ? (
              <div className="flex items-center gap-2">
                <span className="rounded-md bg-green-100 px-2 py-1 font-mono text-xs font-semibold text-green-700">
                  {selectedReplacement.name}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedReplacement(null);
                    setReplacementQuery("");
                  }}
                  className="text-[10px] text-zinc-400 hover:text-zinc-600"
                >
                  remove
                </button>
              </div>
            ) : (
              <div className="relative">
                <input
                  type="text"
                  value={replacementQuery}
                  onChange={(e) => setReplacementQuery(e.target.value)}
                  placeholder="Search replacement tag..."
                  className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-xs outline-none focus:border-green-300"
                />
                {replacementResults.length > 0 && (
                  <div className="absolute z-[var(--z-dropdown)] mt-1 max-h-[160px] w-full overflow-y-auto rounded-lg border border-zinc-200 bg-white shadow-lg">
                    {replacementResults.map((t) => (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => {
                          setSelectedReplacement(t);
                          setReplacementQuery("");
                          setReplacementResults([]);
                        }}
                        className="flex w-full items-center gap-2 border-b border-zinc-50 px-3 py-2 text-left last:border-0 hover:bg-zinc-50"
                      >
                        <span className="font-mono text-[11px] font-semibold text-zinc-700">
                          {t.name}
                        </span>
                        {t.category && (
                          <span className="text-[9px] text-zinc-400">{t.category}</span>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Submit */}
          <button
            type="button"
            onClick={handleDeprecate}
            disabled={!selectedTag || !reason.trim() || isDeprecating}
            className="w-full rounded-xl bg-orange-600 px-4 py-2.5 text-[10px] font-bold tracking-widest text-white uppercase transition hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isDeprecating ? "Deprecating..." : "Deprecate Tag"}
          </button>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-600">{error}</div>
      )}

      {deprecatedTags.length === 0 && !isLoading ? (
        <div className="rounded-xl border border-zinc-200 bg-white p-8 text-center text-zinc-400">
          <p className="text-sm font-medium">No deprecated tags</p>
          <p className="mt-1 text-[10px]">All tags are currently active</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {deprecatedTags.map((tag) => (
            <div
              key={tag.id}
              className="rounded-xl border border-orange-200 bg-white p-4 transition hover:shadow-sm"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="rounded-md bg-orange-100 px-2 py-1 font-mono text-xs font-semibold text-orange-700">
                      {tag.name}
                    </span>
                    <span className="rounded-md bg-zinc-100 px-2 py-1 text-[10px] text-zinc-500">
                      {tag.category}
                    </span>
                  </div>

                  <div className="mt-3 space-y-2">
                    <div className="flex items-start gap-2">
                      <span className="text-[10px] font-semibold text-zinc-400 uppercase">
                        Reason:
                      </span>
                      <span className="text-[10px] text-zinc-600">{tag.deprecated_reason}</span>
                    </div>

                    {tag.replacement && (
                      <div className="flex items-start gap-2">
                        <span className="text-[10px] font-semibold text-zinc-400 uppercase">
                          Replacement:
                        </span>
                        <span className="rounded-md bg-green-100 px-2 py-0.5 font-mono text-[10px] font-semibold text-green-700">
                          {tag.replacement.name}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => handleActivateTag(tag.id)}
                  className="ml-4 rounded-lg border border-green-300 bg-green-50 px-3 py-1.5 text-[10px] font-semibold text-green-700 transition hover:bg-green-100"
                >
                  Reactivate
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
