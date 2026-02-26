"use client";

import { useState, useCallback } from "react";
import { Copy, Check } from "lucide-react";

type CopyButtonProps = {
  text: string;
  className?: string;
  /** "icon" = icon only, "label" = icon + text */
  variant?: "icon" | "label";
};

export default function CopyButton({ text, className = "", variant = "icon" }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      navigator.clipboard
        .writeText(text)
        .then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        })
        .catch(() => {
          // Silently fail — UI stays in un-copied state
        });
    },
    [text]
  );

  const Icon = copied ? Check : Copy;
  const iconColor = copied ? "text-emerald-600" : "text-zinc-500";

  if (variant === "label") {
    return (
      <button
        type="button"
        onClick={handleCopy}
        className={`flex items-center gap-1 rounded-md border border-zinc-200 bg-white px-2 py-1 text-[12px] font-semibold transition hover:bg-zinc-50 ${iconColor} ${className}`}
      >
        <Icon className="h-3 w-3" />
        {copied ? "Copied" : "Copy"}
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      title={copied ? "Copied!" : "Copy to clipboard"}
      className={`rounded-md p-1 transition hover:bg-zinc-100 ${iconColor} ${className}`}
    >
      <Icon className="h-3.5 w-3.5" />
    </button>
  );
}
