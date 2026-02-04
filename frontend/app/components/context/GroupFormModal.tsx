"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import { API_BASE } from "../../constants";
import type { GroupItem, RenderPreset } from "../../types";

type Props = {
  group?: GroupItem;
  projectId: number;
  onSave: (data: Record<string, unknown>) => Promise<void>;
  onClose: () => void;
};

export default function GroupFormModal({ group, projectId, onSave, onClose }: Props) {
  const isEdit = !!group;
  const [name, setName] = useState(group?.name ?? "");
  const [description, setDescription] = useState(group?.description ?? "");
  const [saving, setSaving] = useState(false);

  const [presets, setPresets] = useState<RenderPreset[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<number | null>(null);

  type OptionItem = { id: number; name: string };
  const [styleProfiles, setStyleProfiles] = useState<OptionItem[]>([]);
  const [selectedStyleProfileId, setSelectedStyleProfileId] = useState<number | null>(null);

  useEffect(() => {
    const fetches: Promise<unknown>[] = [
      axios.get<RenderPreset[]>(`${API_BASE}/render-presets`, {
        params: { project_id: projectId },
      }),
      axios.get(`${API_BASE}/style-profiles`),
    ];
    // Load existing config when editing
    if (group) {
      fetches.push(axios.get(`${API_BASE}/groups/${group.id}/config`));
    }

    Promise.all(fetches)
      .then(([presetsRes, profilesRes, configRes]) => {
        const presetsData = (presetsRes as { data: RenderPreset[] }).data;
        setPresets(presetsData);

        const profilesData = (profilesRes as { data: Record<string, unknown>[] }).data;
        setStyleProfiles(
          profilesData.map((p) => ({
            id: p.id as number,
            name: (p.display_name || p.name) as string,
          }))
        );

        if (configRes) {
          const cfg = (configRes as { data: Record<string, unknown> }).data;
          setSelectedPresetId((cfg.render_preset_id as number) ?? null);
          setSelectedStyleProfileId((cfg.style_profile_id as number) ?? null);
        } else if (presetsData.length > 0) {
          setSelectedPresetId(presetsData[0].id);
        }
      })
      .catch(() => {});
  }, [projectId, group]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      const data: Record<string, unknown> = {
        name: name.trim(),
        ...(description.trim() && { description: description.trim() }),
        render_preset_id: selectedPresetId,
        style_profile_id: selectedStyleProfileId,
      };
      if (!isEdit) data.project_id = projectId;
      await onSave(data);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const inputCls =
    "w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none";
  const labelCls = "mb-1 block text-[10px] font-semibold uppercase tracking-wider text-zinc-400";

  const summarize = (p: RenderPreset) => {
    const parts: string[] = [];
    if (p.layout_style) parts.push(p.layout_style);
    if (p.bgm_volume != null) parts.push(`BGM ${p.bgm_volume}`);
    if (p.transition_type) parts.push(p.transition_type);
    if (p.speed_multiplier != null && p.speed_multiplier !== 1.0)
      parts.push(`${p.speed_multiplier}x`);
    if (p.ken_burns_preset && p.ken_burns_preset !== "none")
      parts.push(`KB: ${p.ken_burns_preset}`);
    return parts.join(", ");
  };

  return (
    <Modal open onClose={onClose} size="lg">
      <Modal.Header>
        <h2 className="text-sm font-bold text-zinc-900">{isEdit ? "Edit Group" : "New Group"}</h2>
        <button onClick={onClose} className="text-xs text-zinc-400 hover:text-zinc-600">
          x
        </button>
      </Modal.Header>

      <div className="max-h-[60vh] space-y-4 overflow-y-auto px-5 py-4">
        {/* Basic */}
        <div className="space-y-3">
          <div>
            <label className={labelCls}>Name *</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Series Name"
              className={inputCls}
              autoFocus
            />
          </div>
          <div>
            <label className={labelCls}>Description</label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description"
              className={inputCls}
            />
          </div>
        </div>

        {/* Render Preset */}
        <div className="border-t border-zinc-100 pt-3">
          <label className={labelCls}>Render Preset</label>
          {presets.length === 0 ? (
            <p className="text-[10px] text-zinc-400">Loading presets...</p>
          ) : (
            <div className="space-y-2">
              {presets.map((p) => (
                <label
                  key={p.id}
                  className={`flex cursor-pointer items-start gap-2.5 rounded-lg border px-3 py-2.5 transition ${
                    selectedPresetId === p.id
                      ? "border-zinc-400 bg-zinc-50"
                      : "border-zinc-100 hover:border-zinc-200"
                  }`}
                >
                  <input
                    type="radio"
                    name="render_preset"
                    checked={selectedPresetId === p.id}
                    onChange={() => setSelectedPresetId(p.id)}
                    className="mt-0.5"
                  />
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-zinc-800">{p.name}</div>
                    <div className="truncate text-[10px] text-zinc-400">{summarize(p)}</div>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Style Profile */}
        <div className="border-t border-zinc-100 pt-3">
          <label className={labelCls}>Style Profile *</label>
          {styleProfiles.length === 0 ? (
            <p className="text-[10px] text-zinc-400">Loading style profiles...</p>
          ) : (
            <select
              value={selectedStyleProfileId ?? ""}
              onChange={(e) =>
                setSelectedStyleProfileId(e.target.value ? Number(e.target.value) : null)
              }
              className={inputCls}
            >
              <option value="">-- Select Style Profile --</option>
              {styleProfiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      <Modal.Footer>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Cancel
        </Button>
        <Button
          size="sm"
          loading={saving}
          disabled={!name.trim() || (!isEdit && !selectedStyleProfileId)}
          onClick={handleSubmit}
        >
          {isEdit ? "Save" : "Create"}
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
