"use client";

import type { DriftStatus, SceneDriftResponse } from "../../types";

const GROUP_ABBREV: Record<string, string> = {
  hair_color: "HC",
  eye_color: "EC",
  hair_length: "HL",
  hair_style: "HS",
  appearance: "AP",
  body_feature: "BF",
  skin_color: "SC",
};

const GROUP_FULL_NAME: Record<string, string> = {
  HC: "Hair Color",
  EC: "Eye Color",
  HL: "Hair Length",
  HS: "Hair Style",
  AP: "Appearance",
  BF: "Body Feature",
  SC: "Skin Color",
};

const STATUS_COLOR: Record<DriftStatus, string> = {
  match: "bg-emerald-400",
  mismatch: "bg-red-400",
  missing: "bg-amber-400",
  extra: "bg-blue-400",
  no_data: "bg-zinc-200",
};

type DriftHeatmapProps = {
  scenes: SceneDriftResponse[];
  selectedSceneId: number | null;
  onSceneClick: (scene: SceneDriftResponse) => void;
};

const COLUMNS = ["HC", "EC", "HL", "HS", "AP", "BF", "SC"];

export default function DriftHeatmap({ scenes, selectedSceneId, onSceneClick }: DriftHeatmapProps) {
  return (
    <table className="w-full text-[11px]" role="grid">
      <thead>
        <tr>
          <th className="px-1 py-1 text-left font-medium text-zinc-400">Sc</th>
          {COLUMNS.map((col) => (
            <th
              key={col}
              className="px-0.5 py-1 text-center font-medium text-zinc-400"
              title={GROUP_FULL_NAME[col]}
            >
              {col}
            </th>
          ))}
          <th className="px-1 py-1 text-right font-medium text-zinc-400">ID%</th>
        </tr>
      </thead>
      <tbody>
        {scenes.map((scene) => {
          const isSelected = scene.scene_id === selectedSceneId;
          const groupMap = new Map(
            scene.groups.map((g) => [GROUP_ABBREV[g.group] ?? g.group, g.status as DriftStatus])
          );

          return (
            <tr
              key={scene.scene_id}
              onClick={() => onSceneClick(scene)}
              className={`cursor-pointer transition-colors hover:bg-zinc-50 ${
                isSelected ? "bg-indigo-50 ring-1 ring-indigo-200" : ""
              }`}
              data-testid={`drift-row-${scene.scene_order}`}
            >
              <td className="px-1 py-1 font-medium text-zinc-500">S{scene.scene_order}</td>
              {COLUMNS.map((col) => {
                const status = groupMap.get(col) ?? "no_data";
                return (
                  <td key={col} className="px-0.5 py-1 text-center">
                    <span
                      className={`inline-block h-4 w-4 rounded-sm ${STATUS_COLOR[status]}`}
                      title={`${GROUP_FULL_NAME[col]}: ${status}`}
                      data-testid={`cell-${scene.scene_order}-${col}`}
                      data-status={status}
                    />
                  </td>
                );
              })}
              <td className="px-1 py-1 text-right font-semibold text-zinc-600">
                {Math.round(scene.identity_score * 100)}%
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
