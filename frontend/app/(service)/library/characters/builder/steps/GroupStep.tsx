"use client";

import { useState, useEffect } from "react";
import { FolderOpen, Check, Palette, Users } from "lucide-react";
import axios from "axios";
import { API_BASE } from "../../../../../constants";
import type { GroupItem } from "../../../../../types";
import LoadingSpinner from "../../../../../components/ui/LoadingSpinner";

type GroupStepProps = {
  selectedGroupId: number | null;
  onSelect: (
    groupId: number,
    styleProfileId: number | null,
    baseModel: string | null,
    styleLoraIds: number[]
  ) => void;
};

type StyleProfileFull = {
  id: number;
  sd_model: { base_model: string | null } | null;
  loras: { id: number }[];
};

type GroupWithStyleInfo = GroupItem & {
  baseModel: string | null;
  styleLoraIds: number[];
};

/**
 * Step 0: Select which series (group) this character belongs to.
 * Derives style_profile_id and baseModel from the group's configuration.
 */
export default function GroupStep({ selectedGroupId, onSelect }: GroupStepProps) {
  const [groups, setGroups] = useState<GroupWithStyleInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await axios.get<GroupItem[]>(`${API_BASE}/groups`);
        // Resolve baseModel from each group's style profile
        const uniqueSpIds = [
          ...new Set(
            res.data.map((g) => g.style_profile_id).filter((id): id is number => id != null)
          ),
        ];
        const spMap = new Map<number, { baseModel: string | null; loraIds: number[] }>();
        await Promise.all(
          uniqueSpIds.map(async (spId) => {
            try {
              const spRes = await axios.get<StyleProfileFull>(
                `${API_BASE}/style-profiles/${spId}/full`
              );
              spMap.set(spId, {
                baseModel: spRes.data.sd_model?.base_model ?? null,
                loraIds: (spRes.data.loras ?? []).map((l) => l.id),
              });
            } catch {
              spMap.set(spId, { baseModel: null, loraIds: [] });
            }
          })
        );
        const items: GroupWithStyleInfo[] = res.data.map((g) => {
          const sp = g.style_profile_id != null ? spMap.get(g.style_profile_id) : null;
          return { ...g, baseModel: sp?.baseModel ?? null, styleLoraIds: sp?.loraIds ?? [] };
        });
        setGroups(items);
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <LoadingSpinner size="md" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-zinc-800">소속 시리즈 선택</h2>
        <p className="mt-0.5 text-xs text-zinc-400">
          캐릭터가 소속될 시리즈를 선택하세요. 시리즈의 화풍(Style Profile)이 자동 적용됩니다.
        </p>
      </div>

      {groups.length > 0 ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {groups.map((group) => {
            const isSelected = selectedGroupId === group.id;

            return (
              <button
                key={group.id}
                onClick={() =>
                  onSelect(
                    group.id,
                    group.style_profile_id ?? null,
                    group.baseModel,
                    group.styleLoraIds
                  )
                }
                className={`relative flex flex-col items-start gap-2 rounded-xl border-2 p-4 text-left transition ${
                  isSelected
                    ? "border-zinc-900 bg-zinc-50 shadow-sm"
                    : "border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50/50"
                }`}
              >
                {/* Selection badge */}
                {isSelected && (
                  <div className="absolute top-2 right-2 flex h-5 w-5 items-center justify-center rounded-full bg-zinc-900">
                    <Check className="h-3 w-3 text-white" />
                  </div>
                )}

                {/* Icon */}
                <div
                  className={`flex h-9 w-9 items-center justify-center rounded-lg ${
                    isSelected ? "bg-zinc-900 text-white" : "bg-zinc-100 text-zinc-500"
                  }`}
                >
                  <FolderOpen className="h-4.5 w-4.5" />
                </div>

                {/* Name */}
                <div>
                  <p className="text-sm font-semibold text-zinc-800">{group.name}</p>
                  {group.description && (
                    <p className="mt-0.5 line-clamp-2 text-xs text-zinc-400">{group.description}</p>
                  )}
                </div>

                {/* Style profile badge + char count */}
                <div className="flex flex-wrap items-center gap-1.5">
                  {group.style_profile_name && (
                    <span className="flex items-center gap-1 rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-500">
                      <Palette className="h-3 w-3" />
                      {group.style_profile_name}
                    </span>
                  )}
                  <span className="flex items-center gap-1 rounded-full bg-zinc-50 px-2 py-0.5 text-[11px] text-zinc-400">
                    <Users className="h-3 w-3" />
                    {group.character_count}명
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-200 py-12">
          <FolderOpen className="mb-2 h-8 w-8 text-zinc-300" />
          <p className="text-sm text-zinc-400">시리즈가 없습니다. 먼저 시리즈를 생성하세요.</p>
        </div>
      )}
    </div>
  );
}
