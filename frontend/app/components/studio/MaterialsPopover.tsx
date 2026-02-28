"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useContextStore } from "../../store/useContextStore";
import { useUIStore } from "../../store/useUIStore";
import { useMaterialsCheck } from "../../hooks/useMaterialsCheck";

type MaterialKey = "script" | "style" | "characters" | "voice" | "music" | "background";

type MaterialAction = "script-tab" | "stage-tab";

type MaterialItem = {
  key: MaterialKey;
  label: string;
  icon: string;
  link?: string;
  action?: MaterialAction;
};

const MATERIALS: MaterialItem[] = [
  { key: "script", label: "Script", icon: "S", action: "script-tab" },
  { key: "style", label: "Style", icon: "\u2726", action: "stage-tab" },
  { key: "characters", label: "Characters", icon: "C", action: "stage-tab" },
  { key: "voice", label: "Voice", icon: "V", link: "/admin/voices" },
  { key: "music", label: "Music", icon: "M", link: "/admin/music" },
  { key: "background", label: "BG", icon: "B", action: "stage-tab" },
];

export default function MaterialsPopover() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const setActiveTab = useUIStore((s) => s.setActiveTab);
  const storyboardId = useContextStore((s) => s.storyboardId);
  const { data, isLoading } = useMaterialsCheck(storyboardId);

  const readyCount = data ? MATERIALS.filter((m) => data[m.key]?.ready).length : 0;

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold transition ${
          readyCount === MATERIALS.length
            ? "border-emerald-200 bg-emerald-50 text-emerald-700"
            : "border-zinc-200 bg-zinc-50 text-zinc-600 hover:bg-zinc-100"
        }`}
      >
        {isLoading ? "..." : `${readyCount}/${MATERIALS.length}`}
      </button>

      {open && (
        <div className="absolute top-full right-0 z-20 mt-2 w-64 rounded-xl border border-zinc-200 bg-white p-3 shadow-xl">
          <p className="mb-2 text-[12px] font-semibold tracking-wider text-zinc-400 uppercase">
            Materials
          </p>
          <div className="space-y-1.5">
            {MATERIALS.map((mat) => {
              const ready = data?.[mat.key]?.ready ?? false;
              return (
                <button
                  key={mat.key}
                  onClick={() => {
                    if (mat.action === "script-tab") {
                      setActiveTab("script");
                    } else if (mat.action === "stage-tab") {
                      setActiveTab("stage");
                    } else if (mat.link) {
                      router.push(mat.link);
                    }
                    setOpen(false);
                  }}
                  className={`flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left transition ${
                    ready ? "bg-emerald-50/50 hover:bg-emerald-50" : "bg-zinc-50 hover:bg-zinc-100"
                  }`}
                >
                  <span
                    className={`flex h-5 w-5 items-center justify-center rounded text-[11px] font-bold ${
                      ready ? "bg-emerald-500 text-white" : "bg-zinc-200 text-zinc-500"
                    }`}
                  >
                    {mat.icon}
                  </span>
                  <span className="flex-1 text-xs font-medium text-zinc-700">{mat.label}</span>
                  <span
                    className={`text-xs font-medium ${ready ? "text-emerald-600" : "text-zinc-400"}`}
                  >
                    {ready ? "Ready" : "Missing"}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
