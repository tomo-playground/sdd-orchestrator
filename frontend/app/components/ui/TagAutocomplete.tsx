"use client";

import { useState, useEffect, useRef, KeyboardEvent } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import type { Tag } from "../../types";

type TagAutocompleteProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  rows?: number;
  disabled?: boolean;
};

type TagCategory = "character" | "copyright" | "artist" | "meta" | "scene" | "general";

const getTagColor = (category: string) => {
  switch (category) {
    case "character":
      return "text-emerald-600";
    case "copyright":
      return "text-purple-600";
    case "artist":
      return "text-rose-600";
    case "meta":
      return "text-orange-600";
    case "scene":
    case "general":
      return "text-blue-600";
    default:
      return "text-zinc-600";
  }
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
  const [triggerInfo, setTriggerInfo] = useState<{ start: number; end: number; word: string } | null>(
    null
  );
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

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

    // Only trigger if word is at least 2 chars and doesn't contain invalid chars
    if (word.length >= 2 && /^[a-zA-Z0-9_\-()]+$/.test(word)) {
      setTriggerInfo({ start, end: cursorPos, word });
      void fetchSuggestions(word);
    } else {
      setTriggerInfo(null);
      setIsOpen(false);
    }
  };

  const selectTag = (tag: Tag) => {
    if (!triggerInfo) return;

    const before = value.slice(0, triggerInfo.start);
    const after = value.slice(triggerInfo.end);
    // Add comma if not present (simple heuristic)
    const newValue = `${before}${tag.name}${after}`;
    
    onChange(newValue);
    setIsOpen(false);
    setSuggestions([]);
    
    // Restore focus and move cursor
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        const newCursorPos = before.length + tag.name.length;
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
          className="absolute z-50 mt-1 max-h-60 w-full overflow-y-auto rounded-xl border border-zinc-200 bg-white shadow-xl"
        >
          <ul className="grid gap-0.5 p-1">
            {suggestions.map((tag, index) => (
              <li
                key={tag.id}
                onClick={() => selectTag(tag)}
                onMouseEnter={() => setHighlightedIndex(index)}
                className={`flex cursor-pointer items-center justify-between rounded-lg px-3 py-2 text-xs transition ${ 
                  index === highlightedIndex ? "bg-zinc-100" : "hover:bg-zinc-50"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className={`font-semibold ${getTagColor(tag.category)}`}>
                    {tag.name}
                  </span>
                  {tag.group_name && (
                    <span className="rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] text-zinc-500">
                      {tag.group_name}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                   <span className="text-[10px] tracking-wide text-zinc-400 uppercase">
                    {tag.category}
                  </span>
                  {/* Priority indicator if relevant */}
                  {tag.priority && tag.priority < 5 && (
                     <span className="text-[10px] text-amber-500">★</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
          <div className="border-t border-zinc-100 bg-zinc-50 px-3 py-1.5 text-[10px] text-zinc-400">
             Use <kbd className="font-sans">↑</kbd> <kbd className="font-sans">↓</kbd> to navigate, <kbd className="font-sans">Enter</kbd> to select
          </div>
        </div>
      )}
    </div>
  );
}
