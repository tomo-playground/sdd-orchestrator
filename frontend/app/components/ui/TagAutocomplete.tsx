"use client";

import { useId, useRef, KeyboardEvent } from "react";
import type { Tag } from "../../types";
import useTagSuggestion from "../../hooks/useTagSuggestion";
import TagSuggestionDropdown from "./TagSuggestionDropdown";

type TagAutocompleteProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  rows?: number;
  disabled?: boolean;
  id?: string;
};

export default function TagAutocomplete({
  value,
  onChange,
  placeholder,
  className,
  rows = 3,
  disabled,
  id,
}: TagAutocompleteProps) {
  const listboxId = useId();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const triggerInfoRef = useRef<{ start: number; end: number } | null>(null);

  const {
    suggestions,
    isOpen,
    highlightedIndex,
    setHighlightedIndex,
    triggerSearch,
    closeSuggestions,
    handleNavigationKey,
  } = useTagSuggestion({ inputRef: textareaRef, dropdownRef });

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    onChange(newValue);

    const cursorPos = e.target.selectionStart;

    // Find the word being typed (search backwards for separator)
    let start = cursorPos;
    while (start > 0) {
      const char = newValue[start - 1];
      if (char === " " || char === "," || char === "\n") break;
      start--;
    }

    const word = newValue.slice(start, cursorPos);
    if (word.length > 0) {
      triggerInfoRef.current = { start, end: cursorPos };
    } else {
      triggerInfoRef.current = null;
    }
    triggerSearch(word);
  };

  const selectTag = (tag: Tag) => {
    const trigger = triggerInfoRef.current;
    if (!trigger) return;

    const before = value.slice(0, trigger.start);
    const after = value.slice(trigger.end);

    // Use replacement tag if deprecated
    const insertName =
      tag.is_active === false && tag.replacement_tag_name ? tag.replacement_tag_name : tag.name;

    // Add ", " separator if next char is not already comma
    const needsSeparator = after.length === 0 || !after.trimStart().startsWith(",");
    const separator = needsSeparator ? ", " : "";

    const newValue = `${before}${insertName}${separator}${after}`;
    onChange(newValue);
    closeSuggestions();

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
    if (handleNavigationKey(e.key)) {
      e.preventDefault();
      return;
    }
    if (isOpen && suggestions.length > 0 && (e.key === "Enter" || e.key === "Tab")) {
      e.preventDefault();
      selectTag(suggestions[highlightedIndex]);
    }
  };

  return (
    <div className="relative w-full">
      <textarea
        ref={textareaRef}
        id={id}
        value={value}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        rows={rows}
        disabled={disabled}
        className={className}
        role="combobox"
        aria-expanded={isOpen && suggestions.length > 0}
        aria-autocomplete="list"
        aria-controls={listboxId}
      />

      {isOpen && suggestions.length > 0 && (
        <TagSuggestionDropdown
          suggestions={suggestions}
          highlightedIndex={highlightedIndex}
          onSelect={selectTag}
          onHighlight={setHighlightedIndex}
          dropdownRef={dropdownRef}
          listboxId={listboxId}
        />
      )}
    </div>
  );
}
