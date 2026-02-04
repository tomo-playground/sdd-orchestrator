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
  style_profile_id: number | null;
  narrator_voice_preset_id: number | null;
  character_id: number | null;
  language: string | null;
  structure: string | null;
  duration: number | null;
  sd_steps: number | null;
  sd_cfg_scale: number | null;
  sd_sampler_name: string | null;
  sd_clip_skip: number | null;
};

type OptionItem = { id: number; name: string };

type Props = {
  groupId: number;
  onClose: () => void;
};

// ── Constants ────────────────────────────────────────────────
const LANGUAGES = ["Korean", "English", "Japanese"];
const STRUCTURES = ["Monologue", "Dialogue", "Narration"];
const SAMPLERS = ["DPM++ 2M Karras", "DPM++ SDE Karras", "Euler a", "Euler", "DDIM", "UniPC"];

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
  const [profiles, setProfiles] = useState<OptionItem[]>([]);
  const [characters, setCharacters] = useState<OptionItem[]>([]);

  useEffect(() => {
    Promise.all([
      axios.get<GroupConfig>(`${API_BASE}/groups/${groupId}/config`),
      axios.get(`${API_BASE}/render-presets`),
      axios.get(`${API_BASE}/style-profiles`),
      axios.get(`${API_BASE}/characters`),
    ])
      .then(([cfgRes, presetsRes, profilesRes, charsRes]) => {
        setConfig(cfgRes.data);
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
        setCharacters(
          charsRes.data.map((c: Record<string, unknown>) => ({
            id: c.id as number,
            name: c.name as string,
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
        style_profile_id: config.style_profile_id,
        narrator_voice_preset_id: config.narrator_voice_preset_id,
        character_id: config.character_id,
        language: config.language,
        structure: config.structure,
        duration: config.duration,
        sd_steps: config.sd_steps,
        sd_cfg_scale: config.sd_cfg_scale,
        sd_sampler_name: config.sd_sampler_name,
        sd_clip_skip: config.sd_clip_skip,
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
              label="Style Profile"
              value={config.style_profile_id}
              options={profiles.map((p) => ({ value: p.id, label: p.name }))}
              onChange={(v) => updateField("style_profile_id", toIdOrNull(v))}
              placeholder="-- None --"
            />
            <SelectField
              label="Character"
              value={config.character_id}
              options={characters.map((c) => ({ value: c.id, label: c.name }))}
              onChange={(v) => updateField("character_id", toIdOrNull(v))}
              placeholder="-- None --"
            />
            <VoicePresetSelector
              value={config.narrator_voice_preset_id}
              onChange={(v) => updateField("narrator_voice_preset_id", v)}
              label="Narrator Voice"
            />
          </div>

          {/* SD Generation Settings */}
          <div className="space-y-3 border-t border-zinc-100 pt-3">
            <p className="text-[10px] font-semibold tracking-wider text-zinc-300 uppercase">
              SD Generation
            </p>
            <div>
              <label className={labelCls}>Steps</label>
              <input
                type="number"
                min={1}
                max={80}
                value={config.sd_steps ?? ""}
                onChange={(e) =>
                  updateField("sd_steps", e.target.value ? Number(e.target.value) : null)
                }
                placeholder="27"
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>CFG Scale</label>
              <input
                type="number"
                min={1}
                max={20}
                step={0.5}
                value={config.sd_cfg_scale ?? ""}
                onChange={(e) =>
                  updateField("sd_cfg_scale", e.target.value ? Number(e.target.value) : null)
                }
                placeholder="7.0"
                className={inputCls}
              />
            </div>
            <SelectField
              label="Sampler"
              value={config.sd_sampler_name}
              options={SAMPLERS.map((s) => ({ value: s, label: s }))}
              onChange={(v) => updateField("sd_sampler_name", v || null)}
              placeholder="-- Default (DPM++ 2M Karras) --"
            />
            <div>
              <label className={labelCls}>Clip Skip</label>
              <input
                type="number"
                min={1}
                max={12}
                value={config.sd_clip_skip ?? ""}
                onChange={(e) =>
                  updateField("sd_clip_skip", e.target.value ? Number(e.target.value) : null)
                }
                placeholder="2"
                className={inputCls}
              />
            </div>
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
