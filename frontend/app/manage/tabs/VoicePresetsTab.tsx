"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import type { VoicePreset } from "../../types";

type EditingPreset = {
  name: string;
  description: string;
  voice_design_prompt: string;
  sample_text: string;
  language: string;
};

const EMPTY_PRESET: EditingPreset = {
  name: "",
  description: "",
  voice_design_prompt: "",
  sample_text: "Hello, this is a test voice.",
  language: "korean",
};

export default function VoicePresetsTab() {
  const [presets, setPresets] = useState<VoicePreset[]>([]);
  const [editing, setEditing] = useState<EditingPreset | null>(null);
  const [editId, setEditId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewAssetId, setPreviewAssetId] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const fetchPresets = useCallback(async () => {
    try {
      const res = await axios.get<VoicePreset[]>(`${API_BASE}/voice-presets`);
      setPresets(res.data);
    } catch {
      console.error("Failed to fetch voice presets");
    }
  }, []);

  useEffect(() => {
    void fetchPresets();
  }, [fetchPresets]);

  const handleCreate = () => {
    setEditId(null);
    setEditing({ ...EMPTY_PRESET });
    setPreviewUrl(null);
    setPreviewAssetId(null);
  };

  const handleEdit = (p: VoicePreset) => {
    setEditId(p.id);
    setEditing({
      name: p.name,
      description: p.description ?? "",
      voice_design_prompt: p.voice_design_prompt ?? "",
      sample_text: p.sample_text ?? "",
      language: p.language,
    });
    setPreviewUrl(p.audio_url);
    setPreviewAssetId(null);
  };

  const handleDelete = async (p: VoicePreset) => {
    if (!confirm(`Delete "${p.name}"?`)) return;
    try {
      await axios.delete(`${API_BASE}/voice-presets/${p.id}`);
      await fetchPresets();
    } catch {
      alert("Delete failed");
    }
  };

  const handlePreview = async () => {
    if (!editing?.voice_design_prompt?.trim()) return;
    setPreviewing(true);
    try {
      const res = await axios.post(`${API_BASE}/voice-presets/preview`, {
        voice_design_prompt: editing.voice_design_prompt,
        sample_text: editing.sample_text || "Hello, this is a test.",
        language: editing.language,
      });
      setPreviewUrl(res.data.audio_url);
      setPreviewAssetId(res.data.temp_asset_id);
    } catch {
      alert("Preview generation failed");
    } finally {
      setPreviewing(false);
    }
  };

  const handleSave = async () => {
    if (!editing?.name.trim()) return;
    setSaving(true);
    try {
      if (editId) {
        await axios.put(`${API_BASE}/voice-presets/${editId}`, {
          name: editing.name,
          description: editing.description,
        });
      } else {
        const res = await axios.post(`${API_BASE}/voice-presets`, {
          name: editing.name,
          description: editing.description,
          source_type: "generated",
          voice_design_prompt: editing.voice_design_prompt,
          language: editing.language,
          sample_text: editing.sample_text,
        });
        // Attach preview audio if available
        if (previewAssetId && res.data.id) {
          await axios.post(
            `${API_BASE}/voice-presets/${res.data.id}/attach-preview`,
            null,
            { params: { temp_asset_id: previewAssetId } },
          );
        }
      }
      setEditing(null);
      setEditId(null);
      setPreviewUrl(null);
      setPreviewAssetId(null);
      await fetchPresets();
    } catch {
      alert("Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("name", file.name.replace(/\.[^.]+$/, ""));
      await axios.post(`${API_BASE}/voice-presets/upload`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      await fetchPresets();
    } catch (err: unknown) {
      const msg = axios.isAxiosError(err) ? err.response?.data?.detail : "Upload failed";
      alert(msg || "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const playAudio = (url: string) => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    const audio = new Audio(url);
    audioRef.current = audio;
    audio.play().catch(() => {});
  };

  const set = (key: string, value: unknown) =>
    setEditing((prev) => (prev ? { ...prev, [key]: value } : prev));

  const inputCls =
    "w-full rounded border border-zinc-200 bg-white px-2.5 py-1.5 text-[11px] text-zinc-800 focus:border-zinc-400 focus:outline-none";
  const labelCls = "text-[10px] font-semibold uppercase tracking-wider text-zinc-400";

  return (
    <section className="grid gap-6 rounded-2xl border border-zinc-200/60 bg-white p-8 text-xs text-zinc-600 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
        <span className="text-[10px] font-bold tracking-[0.2em] uppercase text-zinc-400">
          Voice Presets ({presets.length})
        </span>
        <div className="flex items-center gap-2">
          <label className="cursor-pointer rounded-full border border-zinc-200 bg-white px-4 py-1.5 text-[10px] font-bold text-zinc-600 shadow hover:bg-zinc-50 transition">
            {uploading ? "Uploading..." : "Upload Audio"}
            <input
              ref={fileInputRef}
              type="file"
              accept=".wav,.mp3,.flac,.ogg"
              onChange={handleUpload}
              disabled={uploading}
              className="hidden"
            />
          </label>
          <button
            onClick={handleCreate}
            className="rounded-full bg-zinc-900 px-4 py-1.5 text-[10px] font-bold text-white shadow hover:bg-zinc-700 transition"
          >
            + Generate
          </button>
        </div>
      </div>

      {/* List */}
      <div className="grid gap-3">
        {presets.map((p) => (
          <div
            key={p.id}
            className="flex items-center justify-between rounded-xl border border-zinc-100 px-4 py-3 hover:bg-zinc-50/50 transition"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-zinc-800">{p.name}</span>
                <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[9px] font-medium text-zinc-500">
                  {p.source_type}
                </span>
                {p.is_system && (
                  <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[9px] font-medium text-indigo-500">
                    System
                  </span>
                )}
              </div>
              {p.description && (
                <div className="mt-0.5 text-[10px] text-zinc-400 truncate">{p.description}</div>
              )}
            </div>
            <div className="flex items-center gap-2 ml-3">
              {p.audio_url && (
                <button
                  onClick={() => playAudio(p.audio_url!)}
                  className="rounded-full border border-zinc-200 px-3 py-1 text-[10px] font-medium text-zinc-600 hover:bg-zinc-100 transition"
                >
                  Play
                </button>
              )}
              <button
                onClick={() => handleEdit(p)}
                className="rounded-full border border-zinc-200 px-3 py-1 text-[10px] font-medium text-zinc-600 hover:bg-zinc-100 transition"
              >
                Edit
              </button>
              <button
                onClick={() => handleDelete(p)}
                className="rounded-full border border-red-200 px-3 py-1 text-[10px] font-medium text-red-500 hover:bg-red-50 transition"
              >
                Del
              </button>
            </div>
          </div>
        ))}
        {presets.length === 0 && (
          <p className="py-8 text-center text-zinc-400">No voice presets. Generate or upload one.</p>
        )}
      </div>

      {/* Edit / Create Form */}
      {editing && (
        <div className="rounded-xl border border-zinc-200 bg-zinc-50/50 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-zinc-700">
              {editId ? "Edit Voice Preset" : "Generate Voice Preset"}
            </span>
            <button
              onClick={() => {
                setEditing(null);
                setEditId(null);
                setPreviewUrl(null);
                setPreviewAssetId(null);
              }}
              className="text-[10px] text-zinc-400 hover:text-zinc-600"
            >
              Cancel
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className={labelCls}>Name *</label>
              <input
                value={editing.name}
                onChange={(e) => set("name", e.target.value)}
                className={inputCls}
                placeholder="Preset name"
              />
            </div>
            <div className="col-span-2">
              <label className={labelCls}>Description</label>
              <input
                value={editing.description}
                onChange={(e) => set("description", e.target.value)}
                className={inputCls}
                placeholder="Optional"
              />
            </div>
            {!editId && (
              <>
                <div className="col-span-2">
                  <label className={labelCls}>Voice Design Prompt *</label>
                  <input
                    value={editing.voice_design_prompt}
                    onChange={(e) => set("voice_design_prompt", e.target.value)}
                    className={inputCls}
                    placeholder="e.g. calm 40s female narrator"
                  />
                </div>
                <div className="col-span-2">
                  <label className={labelCls}>Sample Text</label>
                  <input
                    value={editing.sample_text}
                    onChange={(e) => set("sample_text", e.target.value)}
                    className={inputCls}
                    placeholder="Text to preview the voice with"
                  />
                </div>
                <div>
                  <label className={labelCls}>Language</label>
                  <select
                    value={editing.language}
                    onChange={(e) => set("language", e.target.value)}
                    className={inputCls}
                  >
                    <option value="korean">Korean</option>
                    <option value="english">English</option>
                    <option value="japanese">Japanese</option>
                    <option value="chinese">Chinese</option>
                  </select>
                </div>
                <div className="flex items-end gap-2">
                  <button
                    onClick={handlePreview}
                    disabled={previewing || !editing.voice_design_prompt?.trim()}
                    className="rounded-full bg-indigo-600 px-4 py-1.5 text-[10px] font-bold text-white shadow hover:bg-indigo-500 disabled:opacity-40 transition"
                  >
                    {previewing ? "Generating..." : "Preview"}
                  </button>
                  {previewUrl && (
                    <button
                      onClick={() => playAudio(previewUrl)}
                      className="rounded-full border border-indigo-200 px-3 py-1.5 text-[10px] font-medium text-indigo-600 hover:bg-indigo-50 transition"
                    >
                      Play Preview
                    </button>
                  )}
                </div>
              </>
            )}
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={handleSave}
              disabled={saving || !editing.name.trim()}
              className="rounded-full bg-zinc-900 px-5 py-1.5 text-[10px] font-bold text-white shadow hover:bg-zinc-700 disabled:opacity-40 transition"
            >
              {saving ? "Saving..." : editId ? "Save" : "Create"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
