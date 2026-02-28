"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import LoadingSpinner from "../ui/LoadingSpinner";
import VoicePresetSelector from "../voice/VoicePresetSelector";
import { useUIStore } from "../../store/useUIStore";
import { useContextStore } from "../../store/useContextStore";
import { fetchGroups } from "../../store/actions/groupActions";

import { SelectField, DnaField, DNA_FIELDS, labelCls, inputCls } from "./GroupConfigHelpers";

// ── Types ────────────────────────────────────────────────────
import type { ChannelDNA } from "../../types";

const EMPTY_CHANNEL_DNA: ChannelDNA = {
  tone: null,
  target_audience: null,
  worldview: null,
  guidelines: null,
};

type GroupData = {
  id: number;
  name: string;
  description: string | null;
  render_preset_id: number | null;
  style_profile_id: number | null;
  narrator_voice_preset_id: number | null;
  channel_dna: ChannelDNA | null;
};

type OptionItem = { id: number; name: string };

type Props = {
  groupId: number;
  onClose: () => void;
};

// ── Component ────────────────────────────────────────────────
export default function GroupConfigEditor({ groupId, onClose }: Props) {
  const showToast = useUIStore((s) => s.showToast);
  const [group, setGroup] = useState<GroupData | null>(null);
  const [groupName, setGroupName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [presets, setPresets] = useState<OptionItem[]>([]);
  const [profiles, setProfiles] = useState<OptionItem[]>([]);

  useEffect(() => {
    Promise.all([
      axios.get(`${API_BASE}/groups/${groupId}`),
      axios.get(`${API_BASE}/render-presets`),
      axios.get(`${API_BASE}/style-profiles`),
    ])
      .then(([groupRes, presetsRes, profilesRes]) => {
        const g = groupRes.data;
        setGroup({
          id: g.id,
          name: g.name,
          description: g.description,
          render_preset_id: g.render_preset_id ?? null,
          style_profile_id: g.style_profile_id ?? null,
          narrator_voice_preset_id: g.narrator_voice_preset_id ?? null,
          channel_dna: g.channel_dna ?? null,
        });
        setGroupName(g.name || "");
        setPresets(
          presetsRes.data.map((p: Record<string, unknown>) => ({
            id: p.id as number,
            name: p.name as string,
          }))
        );
        setProfiles(
          profilesRes.data.map((s: Record<string, unknown>) => ({
            id: s.id as number,
            name: (s.name || s.display_name) as string,
          }))
        );
      })
      .catch(() => showToast("Failed to load config", "error"))
      .finally(() => setLoading(false));
  }, [groupId, showToast]);

  const updateField = (field: keyof GroupData, value: unknown) => {
    setGroup((prev) => (prev ? { ...prev, [field]: value } : prev));
  };

  const handleSave = async () => {
    if (!group) return;
    setSaving(true);
    try {
      // Normalize: if all DNA fields are null, send null instead of empty object
      const dna = group.channel_dna;
      const channelDna =
        dna && (dna.tone || dna.target_audience || dna.worldview || dna.guidelines) ? dna : null;

      await axios.put(`${API_BASE}/groups/${groupId}`, {
        name: groupName.trim(),
        render_preset_id: group.render_preset_id,
        style_profile_id: group.style_profile_id,
        narrator_voice_preset_id: group.narrator_voice_preset_id,
        channel_dna: channelDna,
      });
      const projectId = useContextStore.getState().projectId;
      if (projectId) fetchGroups(projectId);
      showToast("Group config saved", "success");
      onClose();
    } catch {
      showToast("Failed to save config", "error");
    } finally {
      setSaving(false);
    }
  };

  const toIdOrNull = (v: string) => (v ? Number(v) : null);

  return (
    <Modal open onClose={onClose} size="md">
      <Modal.Header>
        <h2 className="text-sm font-bold text-zinc-900">Group Config</h2>
        <button onClick={onClose} className="text-xs text-zinc-400 hover:text-zinc-600">
          x
        </button>
      </Modal.Header>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner />
        </div>
      ) : !group ? (
        <div className="px-5 py-8 text-center text-xs text-zinc-400">
          Failed to load configuration.
        </div>
      ) : (
        <div className="max-h-[60vh] space-y-4 overflow-y-auto px-5 py-4">
          {/* Group Name */}
          <div>
            <label className={labelCls}>Group Name</label>
            <input
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              className={inputCls}
              placeholder="Group name"
            />
          </div>

          {/* Defaults */}
          <div className="space-y-3 border-t border-zinc-100 pt-3">
            <p className="text-[12px] font-semibold tracking-wider text-zinc-300 uppercase">
              Defaults
            </p>
            <SelectField
              label="Render Preset"
              value={group.render_preset_id}
              options={presets.map((p) => ({ value: p.id, label: p.name }))}
              onChange={(v) => updateField("render_preset_id", toIdOrNull(v))}
              placeholder="-- None --"
            />
            <SelectField
              label="Style Profile"
              value={group.style_profile_id}
              options={profiles.map((p) => ({ value: p.id, label: p.name }))}
              onChange={(v) => updateField("style_profile_id", toIdOrNull(v))}
              placeholder="-- None --"
            />
            <VoicePresetSelector
              value={group.narrator_voice_preset_id}
              onChange={(v) => updateField("narrator_voice_preset_id", v)}
              label="Narrator Voice"
            />
          </div>

          {/* Channel DNA */}
          <div className="space-y-3 border-t border-zinc-100 pt-3">
            <p className="text-[12px] font-semibold tracking-wider text-zinc-300 uppercase">
              Channel DNA
            </p>
            {DNA_FIELDS.map((f) => (
              <DnaField
                key={f.field}
                {...f}
                value={group.channel_dna?.[f.field] ?? ""}
                onChange={(v) =>
                  setGroup((prev) =>
                    prev
                      ? {
                          ...prev,
                          channel_dna: {
                            ...EMPTY_CHANNEL_DNA,
                            ...prev.channel_dna,
                            [f.field]: v || null,
                          },
                        }
                      : prev
                  )
                }
              />
            ))}
          </div>
        </div>
      )}

      <Modal.Footer>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Cancel
        </Button>
        <Button size="sm" loading={saving} disabled={loading || !group} onClick={handleSave}>
          Save
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
