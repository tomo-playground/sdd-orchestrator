"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { createPortal } from "react-dom";
import axios from "axios";
import { API_BASE } from "../../constants";
import { useStudioStore } from "../../store/useStudioStore";

type ResultItem = {
  id: string;
  label: string;
  sublabel?: string;
  type: "project" | "group" | "storyboard";
  action: () => void;
};

/** Self-contained Cmd+K quick switcher. Reads projects/groups from store, fetches storyboards on open. */
export default function CommandPalette() {
  const router = useRouter();
  const setMeta = useStudioStore((s) => s.setMeta);
  const projects = useStudioStore((s) => s.projects);
  const groups = useStudioStore((s) => s.groups);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ResultItem[]>([]);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [storyboards, setStoryboards] = useState<{ id: number; title: string; group_id: number }[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  // Global keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Fetch storyboards when opened
  useEffect(() => {
    if (open) {
      setQuery(""); // eslint-disable-line react-hooks/set-state-in-effect
      setSelectedIdx(0);  
      axios
        .get(`${API_BASE}/storyboards`)
        .then((r) => setStoryboards(r.data))
        .catch(() => {});
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  // Build results from query
  const buildResults = useCallback(
    (q: string): ResultItem[] => {
      const lq = q.toLowerCase();
      const items: ResultItem[] = [];

      for (const p of projects) {
        if (!lq || p.name.toLowerCase().includes(lq) || p.handle?.toLowerCase().includes(lq)) {
          items.push({
            id: `p-${p.id}`,
            label: p.name,
            sublabel: p.handle ?? undefined,
            type: "project",
            action: () => {
              setMeta({ projectId: p.id, groupId: null });
              router.push("/");
            },
          });
        }
      }

      for (const g of groups) {
        const proj = projects.find((p) => p.id === g.project_id);
        if (!lq || g.name.toLowerCase().includes(lq)) {
          items.push({
            id: `g-${g.id}`,
            label: g.name,
            sublabel: proj?.name,
            type: "group",
            action: () => {
              if (proj) setMeta({ projectId: proj.id });
              setMeta({ groupId: g.id });
              router.push("/");
            },
          });
        }
      }

      for (const sb of storyboards) {
        if (!lq || sb.title.toLowerCase().includes(lq)) {
          items.push({
            id: `s-${sb.id}`,
            label: sb.title,
            sublabel: `Storyboard #${sb.id}`,
            type: "storyboard",
            action: () => router.push(`/studio?id=${sb.id}`),
          });
        }
      }

      return items.slice(0, 12);
    },
    [projects, groups, storyboards, setMeta, router],
  );

  useEffect(() => {
    setResults(buildResults(query)); // eslint-disable-line react-hooks/set-state-in-effect
    setSelectedIdx(0);  
  }, [query, buildResults]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIdx((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && results[selectedIdx]) {
      results[selectedIdx].action();
      setOpen(false);
    }
  };

  if (!open) return null;

  const typeIcon = (type: ResultItem["type"]) => {
    switch (type) {
      case "project":
        return (
          <svg className="h-3.5 w-3.5 text-violet-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
          </svg>
        );
      case "group":
        return (
          <svg className="h-3.5 w-3.5 text-sky-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
          </svg>
        );
      case "storyboard":
        return (
          <svg className="h-3.5 w-3.5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h1.5C5.496 19.5 6 18.996 6 18.375m-3.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-1.5A1.125 1.125 0 0118 18.375M20.625 4.5H3.375m17.25 0c.621 0 1.125.504 1.125 1.125M20.625 4.5h-1.5C18.504 4.5 18 5.004 18 5.625m3.75 0v1.5c0 .621-.504 1.125-1.125 1.125M3.375 4.5c-.621 0-1.125.504-1.125 1.125M3.375 4.5h1.5C5.496 4.5 6 5.004 6 5.625m-3.75 0v1.5c0 .621.504 1.125 1.125 1.125m0 0h1.5m-1.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m1.5-3.75C5.496 8.25 6 7.746 6 7.125v-1.5M4.875 8.25C5.496 8.25 6 8.754 6 9.375v1.5m0-5.25v5.25m0-5.25C6 5.004 6.504 4.5 7.125 4.5h9.75c.621 0 1.125.504 1.125 1.125m1.125 2.625h1.5m-1.5 0A1.125 1.125 0 0118 7.125v-1.5m1.125 2.625c-.621 0-1.125.504-1.125 1.125v1.5m2.625-2.625c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125M18 5.625v5.25M7.125 12h9.75m-9.75 0A1.125 1.125 0 016 10.875M7.125 12C6.504 12 6 12.504 6 13.125m0-2.25C6 11.496 5.496 12 4.875 12M18 10.875c0 .621-.504 1.125-1.125 1.125M18 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125m-12 5.25v-5.25m0 5.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125m-12 0v-1.5c0-.621-.504-1.125-1.125-1.125M18 18.375v-5.25m0 5.25v-1.5c0-.621.504-1.125 1.125-1.125M18 13.125v1.5c0 .621.504 1.125 1.125 1.125M18 13.125c0-.621.504-1.125 1.125-1.125M6 13.125v1.5c0 .621-.504 1.125-1.125 1.125M6 13.125C6 12.504 5.496 12 4.875 12m-1.5 0h1.5m-1.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M19.125 12h1.5m0 0c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h1.5m14.25 0h1.5" />
          </svg>
        );
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]"
      onClick={() => setOpen(false)}
    >
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" />
      <div
        className="relative z-10 w-full max-w-lg overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input */}
        <div className="flex items-center gap-3 border-b border-zinc-100 px-4 py-3">
          <svg className="h-4 w-4 shrink-0 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search projects, groups, storyboards..."
            className="flex-1 bg-transparent text-sm text-zinc-900 placeholder:text-zinc-400 outline-none"
          />
          <kbd className="hidden shrink-0 rounded border border-zinc-200 bg-zinc-50 px-1.5 py-0.5 text-[10px] font-medium text-zinc-400 sm:inline">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto py-2">
          {results.length === 0 ? (
            <p className="px-4 py-8 text-center text-xs text-zinc-400">
              {query ? "No results found" : "Type to search..."}
            </p>
          ) : (
            results.map((item, idx) => (
              <button
                key={item.id}
                onClick={() => {
                  item.action();
                  setOpen(false);
                }}
                onMouseEnter={() => setSelectedIdx(idx)}
                className={`flex w-full items-center gap-3 px-4 py-2.5 text-left transition ${
                  idx === selectedIdx ? "bg-zinc-50" : ""
                }`}
              >
                {typeIcon(item.type)}
                <div className="min-w-0 flex-1">
                  <div className="truncate text-xs font-medium text-zinc-800">{item.label}</div>
                  {item.sublabel && (
                    <div className="truncate text-[10px] text-zinc-400">{item.sublabel}</div>
                  )}
                </div>
                <span className="shrink-0 rounded bg-zinc-100 px-1.5 py-0.5 text-[9px] font-medium uppercase text-zinc-400">
                  {item.type}
                </span>
              </button>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-3 border-t border-zinc-100 px-4 py-2 text-[10px] text-zinc-400">
          <span><kbd className="rounded border border-zinc-200 bg-zinc-50 px-1 font-mono">↑↓</kbd> navigate</span>
          <span><kbd className="rounded border border-zinc-200 bg-zinc-50 px-1 font-mono">↵</kbd> open</span>
          <span><kbd className="rounded border border-zinc-200 bg-zinc-50 px-1 font-mono">esc</kbd> close</span>
        </div>
      </div>
    </div>,
    document.body,
  );
}
