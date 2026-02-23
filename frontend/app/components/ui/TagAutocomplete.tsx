"use client";

import { useState, useEffect, useRef, KeyboardEvent } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import type { Tag } from "../../types";
import { ERROR_TEXT } from "../ui/variants";

type TagAutocompleteProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  rows?: number;
  disabled?: boolean;
};

// TagCategory kept for documentation / future use
// type TagCategory = "character" | "copyright" | "artist" | "meta" | "scene" | "general";

const getTagColor = (category: string) => {
  switch (category) {
    case "character":
      return "text-emerald-600";
    case "copyright":
      return "text-purple-600";
    case "artist":
      return ERROR_TEXT;
    case "meta":
      return "text-orange-600";
    case "scene":
    case "general":
      return "text-blue-600";
    default:
      return "text-zinc-600";
  }
};

const formatPostCount = (count: number): string => {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 1_000) return `${Math.round(count / 1_000)}K`;
  return String(count);
};

export default function TagAutocomplete({
  value,
  onChange,
  placeholder,
  className,
  rows = 3,
  disabled,
}: TagAutocompleteProps) {
  const [suggestions, setSuggestions] = useState<Tag[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const [triggerInfo, setTriggerInfo] = useState<{
    start: number;
    end: number;
    word: string;
  } | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        textareaRef.current &&
        !textareaRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const fetchSuggestions = async (query: string) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const res = await axios.get(`${API_BASE}/tags/search`, {
        params: { q: query, limit: 10 },
        signal: controller.signal,
      });
      setSuggestions(res.data);
      setHighlightedIndex(0);
      setIsOpen(true);
    } catch (err) {
      if (!axios.isCancel(err)) {
        console.error("Tag search failed", err);
      }
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    onChange(newValue);

    const cursorPos = e.target.selectionStart;

    // Find the word being typed
    // Search backwards from cursor for a separator (space, comma, newline)
    let start = cursorPos;
    while (start > 0) {
      const char = newValue[start - 1];
      if (char === " " || char === "," || char === "\n") {
        break;
      }
      start--;
    }

    const word = newValue.slice(start, cursorPos);

    // Korean input triggers at 1 char, Latin at 2 chars
    const hasKorean = /[가-힣\u3130-\u318F]/.test(word);
    const minLen = hasKorean ? 1 : 2;

    if (word.length >= minLen && /^[a-zA-Z0-9_\-()가-힣\u3130-\u318F]+$/.test(word)) {
      setTriggerInfo({ start, end: cursorPos, word });

      // Debounce API call (300ms)
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        void fetchSuggestions(word);
      }, 300);
    } else {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      setTriggerInfo(null);
      setIsOpen(false);
    }
  };

  const selectTag = (tag: Tag) => {
    if (!triggerInfo) return;

    const before = value.slice(0, triggerInfo.start);
    const after = value.slice(triggerInfo.end);

    // Use replacement tag if deprecated
    const insertName =
      tag.is_active === false && tag.replacement_tag_name ? tag.replacement_tag_name : tag.name;

    // Add ", " separator if next char is not already comma
    const needsSeparator = after.length === 0 || !after.trimStart().startsWith(",");
    const separator = needsSeparator ? ", " : "";

    const newValue = `${before}${insertName}${separator}${after}`;

    onChange(newValue);
    setIsOpen(false);
    setSuggestions([]);

    // Restore focus and move cursor after inserted tag + separator
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        const newCursorPos = before.length + insertName.length + separator.length;
        textareaRef.current.setSelectionRange(newCursorPos, newCursorPos);
      }
    }, 0);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (!isOpen || suggestions.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev + 1) % suggestions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev - 1 + suggestions.length) % suggestions.length);
    } else if (e.key === "Enter" || e.key === "Tab") {
      e.preventDefault();
      selectTag(suggestions[highlightedIndex]);
    } else if (e.key === "Escape") {
      setIsOpen(false);
    }
  };

  return (
    <div className="relative w-full">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        rows={rows}
        disabled={disabled}
        className={className}
      />

      {isOpen && suggestions.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute z-[var(--z-popover)] mt-1 max-h-60 w-full overflow-y-auto rounded-xl border border-zinc-200 bg-white shadow-xl"
        >
          <ul className="grid gap-0.5 p-1">
            {suggestions.map((tag, index) => (
              <li
                key={tag.id}
                onClick={() => selectTag(tag)}
                onMouseEnter={() => setHighlightedIndex(index)}
                className={`flex cursor-pointer items-center justify-between rounded-lg px-3 py-2 text-xs transition ${
                  index === highlightedIndex ? "bg-zinc-100" : "hover:bg-zinc-50"
                } ${tag.is_active === false ? "opacity-50" : ""}`}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`font-semibold ${getTagColor(tag.category)} ${
                      tag.is_active === false ? "line-through" : ""
                    }`}
                  >
                    {tag.name}
                  </span>
                  {tag.is_active === false && tag.replacement_tag_name && (
                    <span className="text-[11px] text-zinc-500">→ {tag.replacement_tag_name}</span>
                  )}
                  {tag.is_active === false && tag.deprecated_reason && (
                    <span className="text-[11px] text-zinc-400 italic">
                      {tag.deprecated_reason}
                    </span>
                  )}
                  {tag.group_name && (
                    <span className="rounded bg-zinc-100 px-1.5 py-0.5 text-[12px] text-zinc-500">
                      {tag.group_name}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[12px] tracking-wide text-zinc-400 uppercase">
                    {tag.category}
                  </span>
                  {/* Priority indicator if relevant */}
                  {tag.priority && tag.priority < 5 && (
                    <span className="text-[12px] text-amber-500">★</span>
                  )}
                  {tag.wd14_count != null && tag.wd14_count > 0 && (
                    <span className="text-[11px] text-zinc-400 tabular-nums">
                      {formatPostCount(tag.wd14_count)}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
          <div className="border-t border-zinc-100 bg-zinc-50 px-3 py-1.5 text-[12px] text-zinc-400">
            Use <kbd className="font-sans">↑</kbd> <kbd className="font-sans">↓</kbd> to navigate,{" "}
            <kbd className="font-sans">Enter</kbd> to select
          </div>
        </div>
      )}
    </div>
  );
}
