import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

type Props = {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
  /** "default" = centered vertical (py-16), "inline" = compact horizontal (py-5) */
  variant?: "default" | "inline";
};

export default function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  variant = "default",
}: Props) {
  if (variant === "inline") {
    return (
      <div className="flex items-center justify-center gap-2 rounded-xl border border-dashed border-zinc-200 py-5">
        {Icon && <Icon className="h-5 w-5 text-zinc-300" />}
        <p className="text-xs text-zinc-500">{title}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-4 py-16 text-center">
      {Icon && <Icon className="h-12 w-12 text-zinc-200" strokeWidth={1} />}
      <div>
        <p className="text-sm font-medium text-zinc-500">{title}</p>
        {description && <p className="mt-1 text-xs text-zinc-400">{description}</p>}
      </div>
      {action}
    </div>
  );
}
