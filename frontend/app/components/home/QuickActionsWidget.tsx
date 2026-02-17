"use client";

import { useRouter } from "next/navigation";
import { PenLine, UserRound, Palette, Mic } from "lucide-react";

type QuickAction = {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  href?: string;
  onClick?: () => void;
};

export default function QuickActionsWidget() {
  const router = useRouter();

  const actions: QuickAction[] = [
    {
      id: "create-story",
      label: "Create Story",
      icon: PenLine,
      href: "/studio?new=true",
    },
    {
      id: "create-character",
      label: "Character",
      icon: UserRound,
      href: "/characters/new",
    },
    {
      id: "browse-styles",
      label: "Styles",
      icon: Palette,
      href: "/library?tab=style",
    },
    {
      id: "browse-voices",
      label: "Voices",
      icon: Mic,
      href: "/library?tab=voices",
    },
  ];

  const handleAction = (action: QuickAction) => {
    if (action.onClick) {
      action.onClick();
    } else if (action.href) {
      router.push(action.href);
    }
  };

  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold text-zinc-900">Quick Actions</h3>
      <div className="grid grid-cols-2 gap-2">
        {actions.map((action) => {
          const Icon = action.icon;
          return (
            <button
              key={action.id}
              onClick={() => handleAction(action)}
              className="group flex flex-col items-center gap-2 rounded-xl border border-zinc-200 bg-white p-4 transition hover:border-zinc-300 hover:shadow-sm"
            >
              <div className="rounded-full bg-zinc-100 p-3 transition group-hover:bg-zinc-900">
                <Icon className="h-5 w-5 text-zinc-600 transition group-hover:text-white" />
              </div>
              <span className="text-xs font-medium text-zinc-700">{action.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
