"use client";

import { useId, useState, useRef, KeyboardEvent } from "react";
import type { Tag } from "../../types";
import useTagSuggestion from "../../hooks/useTagSuggestion";
import TagSuggestionDropdown from "./TagSuggestionDropdown";

type TagSuggestInputProps = {
  onTagSelect: (tagName: string) => void;
  placeholder?: string;
  className?: string;
};

export default function TagSuggestInput({
  onTagSelect,
  placeholder = "Add tag...",
  className,
}: TagSuggestInputProps) {
  const listboxId = useId();
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const {
    suggestions,
    isOpen,
    highlightedIndex,
    setHighlightedIndex,
    triggerSearch,
    closeSuggestions,
    handleNavigationKey,
  } = useTagSuggestion({ inputRef, dropdownRef });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setValue(newValue);
    triggerSearch(newValue.trim());
  };

  const selectTag = (tag: Tag) => {
    const insertName =
      tag.is_active === false && tag.replacement_tag_name ? tag.replacement_tag_name : tag.name;
    onTagSelect(insertName);
    setValue("");
    closeSuggestions();
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (handleNavigationKey(e.key)) {
      e.preventDefault();
      return;
    }
    if (isOpen && suggestions.length > 0 && (e.key === "Enter" || e.key === "Tab")) {
      e.preventDefault();
      selectTag(suggestions[highlightedIndex]);
      return;
    }
    // Dropdown closed: Enter submits the raw value
    if (e.key === "Enter" && value.trim()) {
      e.preventDefault();
      onTagSelect(value.trim());
      setValue("");
    }
  };

  return (
    <div className="relative inline-block">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
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
