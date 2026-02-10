import { Clapperboard, Trash2 } from "lucide-react";
import { cx } from "../../ui/variants";

export type StoryboardItem = { id: number; title: string; group_id: number };

type Props = {
  storyboards: StoryboardItem[];
  activeId: number | null;
  collapsed: boolean;
  locked: boolean;
  onSelect: (sb: StoryboardItem) => void;
  onDelete: (id: number) => void;
};

export default function StoryList({
  storyboards,
  activeId,
  collapsed,
  locked,
  onSelect,
  onDelete,
}: Props) {
  if (storyboards.length === 0 && !collapsed) {
    return <p className="px-3 py-1 text-[11px] text-zinc-300">No stories yet</p>;
  }
  return (
    <ul className="space-y-0.5 px-1">
      {storyboards.map((sb) => {
        const isActive = sb.id === activeId;
        const isDisabled = locked && !isActive;
        return (
          <li key={sb.id} className="group/story">
            <div
              className={cx(
                "flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs transition",
                isActive
                  ? "border-l-2 border-zinc-900 bg-zinc-100 font-medium text-zinc-900"
                  : isDisabled
                    ? "cursor-not-allowed text-zinc-300"
                    : "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-700"
              )}
            >
              <button
                onClick={() => onSelect(sb)}
                disabled={isDisabled}
                title={
                  isDisabled
                    ? "Autopilot running — wait for completion"
                    : sb.title || `Story #${sb.id}`
                }
                className="flex min-w-0 flex-1 items-center gap-2"
              >
                <Clapperboard className={cx("h-3.5 w-3.5 shrink-0", isDisabled && "opacity-40")} />
                {!collapsed && <span className="truncate">{sb.title || `Story #${sb.id}`}</span>}
              </button>
              {!collapsed && !locked && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(sb.id);
                  }}
                  title="Delete storyboard"
                  className="hidden shrink-0 rounded p-0.5 text-zinc-300 transition group-hover/story:block hover:text-rose-500"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
