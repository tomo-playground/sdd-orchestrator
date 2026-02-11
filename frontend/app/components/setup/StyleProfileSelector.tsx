"use client";

type Props = {
  currentProfileName: string | null;
};

/**
 * Read-only display of the current style profile.
 * Style profiles are managed at the Group level (GroupConfig).
 * Change via Manage > Group Config or onboarding modal.
 */
export default function StyleProfileSelector({ currentProfileName }: Props) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-[12px] font-semibold tracking-wider text-zinc-400 uppercase">
        Style
      </span>
      <span className="text-xs font-bold text-zinc-900">{currentProfileName || "Not set"}</span>
    </div>
  );
}
