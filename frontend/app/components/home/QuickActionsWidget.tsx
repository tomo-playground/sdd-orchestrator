"use client";

import { useRouter } from "next/navigation";
import { Clapperboard, UserRound, Palette, Mic } from "lucide-react";
import { useUIStore } from "../../store/useUIStore";

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
      id: "new-project",
      label: "New Project",
      icon: Clapperboard,
      onClick: () =>
        useUIStore.getState().set({ showSetupWizard: true, setupWizardInitialStep: 1 }),
    },
    {
      id: "create-character",
      label: "Create Character",
      icon: UserRound,
      href: "/characters/new",
    },
    {
      id: "browse-styles",
      label: "Browse Styles",
      icon: Palette,
      href: "/library?tab=style", // Fixed: 'style' not 'styles'
    },
    {
      id: "browse-voices",
      label: "Browse Voices", // Changed from "Test Voice" to "Browse Voices"
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
    <div className="mt-8">
      <h2 className="mb-4 text-xl font-bold text-zinc-900">Quick Actions</h2>
      <p className="mb-6 text-sm text-zinc-500">
        Jump into creating without opening a full project
      </p>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {actions.map((action) => {
          const Icon = action.icon;
          return (
            <button
              key={action.id}
              onClick={() => handleAction(action)}
              className="group flex flex-col items-center gap-3 rounded-xl border border-zinc-200 bg-white p-6 transition hover:border-zinc-300 hover:shadow-md"
            >
              <div className="rounded-full bg-zinc-100 p-4 transition group-hover:bg-zinc-900">
                <Icon className="h-6 w-6 text-zinc-600 transition group-hover:text-white" />
              </div>
              <span className="text-sm font-medium text-zinc-700">{action.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
