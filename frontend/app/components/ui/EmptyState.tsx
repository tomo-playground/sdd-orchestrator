import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

type Props = {
  icon?: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
};

export default function EmptyState({ icon: Icon, title, description, action }: Props) {
  return (
    <div className="flex flex-col items-center gap-4 py-16 text-center">
      {Icon && <Icon className="h-12 w-12 text-zinc-200" strokeWidth={1} />}
      <div>
        <p className="text-sm font-medium text-zinc-500">{title}</p>
        <p className="mt-1 text-xs text-zinc-400">{description}</p>
      </div>
      {action}
    </div>
  );
}
