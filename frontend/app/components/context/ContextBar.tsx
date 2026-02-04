"use client";

import { useState, useRef, useEffect } from "react";
import { useStudioStore } from "../../store/useStudioStore";

type Props = {
  title?: string;
};

export default function ContextBar({ title }: Props) {
  const setMeta = useStudioStore((s) => s.setMeta);
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(title || "");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setEditValue(title || "");
  }, [title]);

  useEffect(() => {
    if (isEditing) inputRef.current?.focus();
  }, [isEditing]);

  const handleSave = () => {
    setIsEditing(false);
    if (editValue.trim() && editValue !== title) {
      setMeta({ storyboardTitle: editValue.trim() });
    }
  };

  return (
    <div className="flex min-w-0 items-center gap-2">
      {isEditing ? (
        <input
          ref={inputRef}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={handleSave}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSave();
            if (e.key === "Escape") {
              setIsEditing(false);
              setEditValue(title || "");
            }
          }}
          className="max-w-xs min-w-[120px] border-b border-zinc-300 bg-transparent px-0 py-0.5 text-sm font-bold text-zinc-900 outline-none"
        />
      ) : (
        <button
          onClick={() => setIsEditing(true)}
          className="max-w-[200px] truncate text-sm font-bold text-zinc-900 transition hover:text-zinc-700 md:max-w-sm"
          title="Click to edit title"
        >
          {title || "New Storyboard"}
        </button>
      )}
    </div>
  );
}
