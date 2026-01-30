"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { API_BASE } from "../constants";
import LoadingSpinner from "../components/ui/LoadingSpinner";

interface DeprecatedTag {
  id: number;
  name: string;
  category: string;
  deprecated_reason: string;
  replacement: {
    id: number;
    name: string;
    category: string;
  } | null;
  created_at: string;
  updated_at: string;
}

interface DeprecatedTagsResponse {
  total: number;
  tags: DeprecatedTag[];
}

export default function DeprecatedTagsPanel() {
  const [deprecatedTags, setDeprecatedTags] = useState<DeprecatedTag[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    if (!confirm("Are you sure you want to reactivate this tag?")) {
      return;
    }

    try {
      await axios.put(`${API_BASE}/admin/tags/${tagId}/activate`);
      await fetchDeprecatedTags(); // Refresh list
    } catch (err) {
      console.error("Failed to activate tag:", err);
      alert("Failed to activate tag");
    }
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

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-600">
          {error}
        </div>
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
                      <span className="text-[10px] font-semibold text-zinc-400 uppercase">Reason:</span>
                      <span className="text-[10px] text-zinc-600">{tag.deprecated_reason}</span>
                    </div>

                    {tag.replacement && (
                      <div className="flex items-start gap-2">
                        <span className="text-[10px] font-semibold text-zinc-400 uppercase">Replacement:</span>
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
                  className="ml-4 rounded-lg border border-green-300 bg-green-50 px-3 py-1.5 text-[10px] font-semibold text-green-700 hover:bg-green-100 transition"
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
