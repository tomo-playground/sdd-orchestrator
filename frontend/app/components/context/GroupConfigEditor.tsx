"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { API_BASE, ADMIN_API_BASE } from "../../constants";
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

type GroupConfig = {
  id: number;
  group_id: number;
  render_preset_id: number | null;
  style_profile_id: number | null;
  narrator_voice_preset_id: number | null;
  language: string | null;
  duration: number | null;
  channel_dna: ChannelDNA | null;
};

type OptionItem = { id: number; name: string };

type Props = {
  groupId: number;
  onClose: () => void;
};

// ── Constants ────────────────────────────────────────────────
// ── Component ────────────────────────────────────────────────
export default function GroupConfigEditor({ groupId, onClose }: Props) {
  const showToast = useUIStore((s) => s.showToast);
  const [config, setConfig] = useState<GroupConfig | null>(null);
  const [groupName, setGroupName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [presets, setPresets] = useState<OptionItem[]>([]);
  const [profiles, setProfiles] = useState<OptionItem[]>([]);
  const [languages, setLanguages] = useState<{ value: string; label: string }[]>([]);

  useEffect(() => {
    Promise.all([
      axios.get<GroupConfig>(`${API_BASE}/groups/${groupId}/config`),
      axios.get(`${API_BASE}/render-presets`),
      axios.get(`${API_BASE}/style-profiles`),
      axios.get(`${API_BASE}/presets`),
      axios.get(`${API_BASE}/groups/${groupId}`),
    ])
      .then(([cfgRes, presetsRes, profilesRes, sbPresetsRes, groupRes]) => {
        setConfig(cfgRes.data);
        setGroupName(groupRes.data.name || "");
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
        const sbData = sbPresetsRes.data;
        if (Array.isArray(sbData?.languages)) setLanguages(sbData.languages);
      })
      .catch(() => showToast("Failed to load config", "error"))
      .finally(() => setLoading(false));
  }, [groupId, showToast]);

  const updateField = (field: keyof GroupConfig, value: unknown) => {
    setConfig((prev) => (prev ? { ...prev, [field]: value } : prev));
  };

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      // Normalize: if all DNA fields are null, send null instead of empty object
      const dna = config.channel_dna;
      const channelDna =
        dna && (dna.tone || dna.target_audience || dna.worldview || dna.guidelines) ? dna : null;

      await Promise.all([
        axios.put(`${ADMIN_API_BASE}/groups/${groupId}/config`, {
          render_preset_id: config.render_preset_id,
          style_profile_id: config.style_profile_id,
          narrator_voice_preset_id: config.narrator_voice_preset_id,
          language: config.language,
          duration: config.duration,
          channel_dna: channelDna,
        }),
        axios.put(`${ADMIN_API_BASE}/groups/${groupId}`, { name: groupName.trim() }),
      ]);
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
      ) : !config ? (
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

          {/* Content Settings */}
          <div className="space-y-3">
            <SelectField
              label="Language"
              value={config.language}
              options={languages.map((l) => ({ value: l.value, label: l.label }))}
              onChange={(v) => updateField("language", v || null)}
              placeholder="-- None --"
            />
            <div>
              <label className={labelCls}>Duration (seconds)</label>
              <input
                type="number"
                min={10}
                max={120}
                value={config.duration ?? ""}
                onChange={(e) =>
                  updateField("duration", e.target.value ? Number(e.target.value) : null)
                }
                placeholder="10 - 120"
                className={inputCls}
              />
            </div>
          </div>

          {/* Defaults */}
          <div className="space-y-3 border-t border-zinc-100 pt-3">
            <p className="text-[12px] font-semibold tracking-wider text-zinc-300 uppercase">
              Defaults
            </p>
            <SelectField
              label="Render Preset"
              value={config.render_preset_id}
              options={presets.map((p) => ({ value: p.id, label: p.name }))}
              onChange={(v) => updateField("render_preset_id", toIdOrNull(v))}
              placeholder="-- None --"
            />
            <SelectField
              label="Style Profile"
              value={config.style_profile_id}
              options={profiles.map((p) => ({ value: p.id, label: p.name }))}
              onChange={(v) => updateField("style_profile_id", toIdOrNull(v))}
              placeholder="-- None --"
            />
            <VoicePresetSelector
              value={config.narrator_voice_preset_id}
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
                value={config.channel_dna?.[f.field] ?? ""}
                onChange={(v) =>
                  setConfig((prev) =>
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
        <Button size="sm" loading={saving} disabled={loading || !config} onClick={handleSave}>
          Save
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
