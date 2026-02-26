import { useState, useId, ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { SIDE_PANEL_LABEL } from "./variants";

interface CollapsibleSectionProps {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
  className?: string;
  headerClassName?: string;
}

export default function CollapsibleSection({
  title,
  children,
  defaultOpen = false,
  className = "",
  headerClassName = "",
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const contentId = useId();

  return (
    <div className={`border-t border-zinc-100 py-3 ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-controls={contentId}
        className={`group flex w-full items-center justify-between ${headerClassName}`}
      >
        <span
          className={`${SIDE_PANEL_LABEL} !mb-0 cursor-pointer transition-colors group-hover:text-zinc-600`}
        >
          {title}
        </span>
        <ChevronDown
          className={`h-4 w-4 text-zinc-400 transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          } group-hover:text-zinc-600`}
        />
      </button>

      {isOpen && (
        <div id={contentId} className="animate-in slide-in-from-top-1 fade-in mt-3 duration-200">
          {children}
        </div>
      )}
    </div>
  );
}
