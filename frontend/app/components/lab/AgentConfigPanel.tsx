"use client";

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { Loader2, Plus, Trash2, Shield, X, Pencil } from "lucide-react";
import { API_BASE } from "../../constants";
import PresetFormFields from "./PresetFormFields";

// ── Types ────────────────────────────────────────────────────

type AgentPreset = {
  id: number;
  name: string;
  role_description: string;
  system_prompt: string;
  model_provider: string;
  model_name: string;
  temperature: number;
  is_system: boolean;
  created_at: string | null;
};

type NewPresetForm = {
  name: string;
  role_description: string;
  system_prompt: string;
  model_provider: string;
  model_name: string;
  temperature: number;
};

const EMPTY_FORM: NewPresetForm = {
  name: "",
  role_description: "",
  system_prompt: "",
  model_provider: "gemini",
  model_name: "gemini-2.0-flash",
  temperature: 0.9,
};

// ── Main Component ───────────────────────────────────────────

export default function AgentConfigPanel() {
  const [presets, setPresets] = useState<AgentPreset[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<NewPresetForm>({ ...EMPTY_FORM });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);

  const fetchPresets = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get<AgentPreset[]>(
        `${API_BASE}/lab/creative/agent-presets`
      );
      setPresets(res.data);
    } catch {
      setError("Failed to load presets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPresets();
  }, [fetchPresets]);

  const handleCreate = useCallback(async () => {
    if (!form.name.trim() || !form.role_description.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await axios.post(`${API_BASE}/lab/creative/agent-presets`, form);
      setForm({ ...EMPTY_FORM });
      setShowForm(false);
      await fetchPresets();
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? err.response?.data?.detail ?? err.message
        : "Failed to create preset";
      setError(String(msg));
    } finally {
      setSubmitting(false);
    }
  }, [form, fetchPresets]);

  const handleDelete = useCallback(
    async (id: number) => {
      try {
        await axios.delete(`${API_BASE}/lab/creative/agent-presets/${id}`);
        await fetchPresets();
      } catch (err) {
        const msg = axios.isAxiosError(err)
          ? err.response?.data?.detail ?? err.message
          : "Failed to delete preset";
        setError(String(msg));
      }
    },
    [fetchPresets]
  );

  const handleEdit = useCallback((preset: AgentPreset) => {
    setEditingId(preset.id);
    setForm({
      name: preset.name,
      role_description: preset.role_description,
      system_prompt: preset.system_prompt,
      model_provider: preset.model_provider,
      model_name: preset.model_name,
      temperature: preset.temperature,
    });
    setShowForm(false);
  }, []);

  const handleUpdate = useCallback(async () => {
    if (!editingId || !form.name.trim() || !form.role_description.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await axios.put(`${API_BASE}/lab/creative/agent-presets/${editingId}`, form);
      setForm({ ...EMPTY_FORM });
      setEditingId(null);
      await fetchPresets();
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? err.response?.data?.detail ?? err.message
        : "Failed to update preset";
      setError(String(msg));
    } finally {
      setSubmitting(false);
    }
  }, [editingId, form, fetchPresets]);

  const handleCancelEdit = useCallback(() => {
    setEditingId(null);
    setForm({ ...EMPTY_FORM });
  }, []);

  const updateField = useCallback(
    <K extends keyof NewPresetForm>(key: K, value: NewPresetForm[K]) => {
      setForm((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  if (loading) {
    return (
      <div className="flex h-32 items-center justify-center">
        <Loader2 className="h-4 w-4 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-800">Agent Presets</h3>
        <button
          onClick={() => setShowForm((p) => !p)}
          className="flex items-center gap-1 rounded-lg border border-zinc-200 px-3 py-1.5 text-xs text-zinc-600 hover:bg-zinc-50"
        >
          {showForm ? (
            <>
              <X className="h-3.5 w-3.5" /> Cancel
            </>
          ) : (
            <>
              <Plus className="h-3.5 w-3.5" /> New Preset
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
          {error}
        </div>
      )}

      {/* Create form */}
      {showForm && (
        <div className="rounded-2xl border border-zinc-200 bg-white p-5">
          <PresetFormFields
            title="New Agent Preset"
            form={form}
            updateField={updateField}
            onSubmit={handleCreate}
            submitting={submitting}
            submitLabel="Create Preset"
          />
        </div>
      )}

      {/* Preset list */}
      {presets.length === 0 ? (
        <div className="flex h-24 items-center justify-center rounded-xl border border-dashed border-zinc-300 bg-zinc-50 text-xs text-zinc-400">
          No presets yet
        </div>
      ) : (
        <div className="space-y-2">
          {presets.map((preset) => (
            <div
              key={preset.id}
              className="rounded-2xl border border-zinc-200 bg-white p-4"
            >
              {editingId === preset.id ? (
                // Edit mode
                <PresetFormFields
                  title="Edit Agent Preset"
                  form={form}
                  updateField={updateField}
                  onSubmit={handleUpdate}
                  onCancel={handleCancelEdit}
                  submitting={submitting}
                  submitLabel="Save"
                  submitIcon="save"
                />
              ) : (
                // View mode
                <>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-zinc-800">
                        {preset.name}
                      </span>
                      {preset.is_system && (
                        <span className="flex items-center gap-0.5 rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-blue-600">
                          <Shield className="h-3 w-3" />
                          System
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleEdit(preset)}
                        className="rounded p-1 text-zinc-400 transition hover:bg-blue-50 hover:text-blue-500"
                        title="Edit preset"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      {!preset.is_system && (
                        <button
                          onClick={() => handleDelete(preset.id)}
                          className="rounded p-1 text-zinc-400 transition hover:bg-red-50 hover:text-red-500"
                          title="Delete preset"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                  <p className="mt-1 text-xs text-zinc-500">
                    {preset.role_description}
                  </p>
                  <div className="mt-2 flex items-center gap-3 text-[10px] text-zinc-400">
                    <span>
                      {preset.model_provider}/{preset.model_name}
                    </span>
                    <span>temp: {preset.temperature}</span>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
