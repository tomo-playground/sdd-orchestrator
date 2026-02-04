import { FolderOpen, Settings } from "lucide-react";
import { cx } from "../../ui/variants";

type Props = {
  groups: { id: number; name: string }[];
  activeId: number | null;
  collapsed: boolean;
  onSelect: (id: number) => void;
  onConfig: (id: number) => void;
};

export default function GroupList({ groups, activeId, collapsed, onSelect, onConfig }: Props) {
  return (
    <ul className="space-y-0.5 px-1">
      {groups.map((g) => (
        <li key={g.id} className="group/item">
          <div
            className={cx(
              "flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs transition",
              g.id === activeId
                ? "bg-zinc-100 font-medium text-zinc-900"
                : "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-700"
            )}
          >
            <button
              onClick={() => onSelect(g.id)}
              title={collapsed ? g.name : undefined}
              className="flex min-w-0 flex-1 items-center gap-2"
            >
              <FolderOpen className="h-3.5 w-3.5 shrink-0" />
              {!collapsed && <span className="truncate">{g.name}</span>}
            </button>
            {!collapsed && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onConfig(g.id);
                }}
                title="Group settings"
                className="hidden shrink-0 rounded p-0.5 text-zinc-300 transition group-hover/item:block hover:text-zinc-600"
              >
                <Settings className="h-3 w-3" />
              </button>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
