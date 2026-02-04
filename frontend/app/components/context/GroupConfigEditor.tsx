"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import LoadingSpinner from "../ui/LoadingSpinner";
import VoicePresetSelector from "../voice/VoicePresetSelector";
import { useStudioStore } from "../../store/useStudioStore";

// ── Types ────────────────────────────────────────────────────
type GroupConfig = {
  id: number;
  group_id: number;
  render_preset_id: number | null;
  default_character_id: number | null;
  default_style_profile_id: number | null;
  narrator_voice_preset_id: number | null;
  language: string | null;
  structure: string | null;
  duration: number | null;
};

type OptionItem = { id: number; name: string };

type Props = {
  groupId: number;
  onClose: () => void;
};

// ── Constants ────────────────────────────────────────────────
const LANGUAGES = ["Korean", "English", "Japanese"];
const STRUCTURES = ["Monologue", "Dialogue", "Narration"];

const labelCls = "mb-1 block text-[10px] font-semibold uppercase tracking-wider text-zinc-400";
const inputCls =
  "w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 focus:border-zinc-400 focus:outline-none";
const disabledCls =
  "w-full rounded-lg border border-zinc-100 bg-zinc-50 px-3 py-2 text-xs text-zinc-400 cursor-not-allowed";

// ── Helpers ──────────────────────────────────────────────────
function SelectField({
  label,
  value,
  options,
  onChange,
  placeholder,
  disabled,
}: {
  label: string;
  value: string | number | null;
  options: { value: string | number; label: string }[];
  onChange: (v: string) => void;
  placeholder?: string;
  disabled?: boolean;
}) {
  return (
    <div>
      <label className={labelCls}>{label}</label>
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className={disabled ? disabledCls : inputCls}
        disabled={disabled}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

// ── Component ────────────────────────────────────────────────
export default function GroupConfigEditor({ groupId, onClose }: Props) {
  const showToast = useStudioStore((s) => s.showToast);
  const [config, setConfig] = useState<GroupConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [presets, setPresets] = useState<OptionItem[]>([]);
  const [characters, setCharacters] = useState<OptionItem[]>([]);
  const [profiles, setProfiles] = useState<OptionItem[]>([]);

  useEffect(() => {
    Promise.all([
      axios.get<GroupConfig>(`${API_BASE}/groups/${groupId}/config`),
      axios.get(`${API_BASE}/render-presets`),
      axios.get(`${API_BASE}/characters`),
      axios.get(`${API_BASE}/style-profiles`),
    ])
      .then(([cfgRes, presetsRes, charsRes, profilesRes]) => {
        setConfig(cfgRes.data);
        setPresets(
          presetsRes.data.map((p: Record<string, unknown>) => ({
            id: p.id as number,
            name: p.name as string,
          }))
        );
        setCharacters(
          charsRes.data.map((c: Record<string, unknown>) => ({
            id: c.id as number,
            name: c.name as string,
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

  const updateField = (field: keyof GroupConfig, value: unknown) => {
    setConfig((prev) => (prev ? { ...prev, [field]: value } : prev));
  };

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      await axios.put(`${API_BASE}/groups/${groupId}/config`, {
        render_preset_id: config.render_preset_id,
        default_character_id: config.default_character_id,
        default_style_profile_id: config.default_style_profile_id,
        narrator_voice_preset_id: config.narrator_voice_preset_id,
        language: config.language,
        structure: config.structure,
        duration: config.duration,
      });
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
          {/* Content Settings */}
          <div className="space-y-3">
            <SelectField
              label="Language"
              value={config.language}
              options={LANGUAGES.map((l) => ({ value: l, label: l }))}
              onChange={(v) => updateField("language", v || null)}
              placeholder="-- None --"
            />
            <SelectField
              label="Structure"
              value={config.structure}
              options={STRUCTURES.map((s) => ({ value: s, label: s }))}
              onChange={(v) => updateField("structure", v || null)}
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
            <p className="text-[10px] font-semibold tracking-wider text-zinc-300 uppercase">
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
              label="Character"
              value={config.default_character_id}
              options={characters.map((c) => ({ value: c.id, label: c.name }))}
              onChange={(v) => updateField("default_character_id", toIdOrNull(v))}
              placeholder="-- None --"
            />
            <SelectField
              label="Style Profile"
              value={config.default_style_profile_id}
              options={profiles.map((p) => ({ value: p.id, label: p.name }))}
              onChange={(v) => updateField("default_style_profile_id", toIdOrNull(v))}
              placeholder="-- None --"
            />
            <VoicePresetSelector
              value={config.narrator_voice_preset_id}
              onChange={(v) => updateField("narrator_voice_preset_id", v)}
              label="Narrator Voice"
            />
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
