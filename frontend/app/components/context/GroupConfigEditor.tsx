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
import { fetchGroups, loadGroupDefaults } from "../../store/actions/groupActions";

import { SelectField, labelCls, inputCls } from "./GroupConfigHelpers";

type GroupData = {
  id: number;
  name: string;
  description: string | null;
  render_preset_id: number | null;
  style_profile_id: number | null;
  narrator_voice_preset_id: number | null;
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
  const [groupDesc, setGroupDesc] = useState("");
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
        });
        setGroupName(g.name || "");
        setGroupDesc(g.description || "");
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
      await axios.put(`${API_BASE}/groups/${groupId}`, {
        name: groupName.trim(),
        description: groupDesc.trim() || null,
        render_preset_id: group.render_preset_id,
        style_profile_id: group.style_profile_id,
        narrator_voice_preset_id: group.narrator_voice_preset_id,
      });
      const { projectId, groupId: activeGroupId } = useContextStore.getState();
      if (projectId) fetchGroups(projectId);
      if (activeGroupId === groupId) await loadGroupDefaults(groupId);
      showToast("시리즈 설정 저장됨", "success");
      onClose();
    } catch {
      showToast("시리즈 설정 저장 실패", "error");
    } finally {
      setSaving(false);
    }
  };

  const toIdOrNull = (v: string) => (v ? Number(v) : null);

  return (
    <Modal open onClose={onClose} size="md">
      <Modal.Header>
        <h2 className="text-sm font-bold text-zinc-900">시리즈 설정</h2>
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
            <label className={labelCls}>시리즈 이름</label>
            <input
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              className={inputCls}
              placeholder="시리즈 이름"
            />
          </div>

          {/* Description */}
          <div>
            <label className={labelCls}>설명</label>
            <textarea
              value={groupDesc}
              onChange={(e) => setGroupDesc(e.target.value)}
              className={inputCls}
              placeholder="시리즈에 대한 간단한 설명"
              rows={2}
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
