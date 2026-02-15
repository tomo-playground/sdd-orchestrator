"use client";

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { Loader2, Plus, Trash2, Shield, X, Pencil } from "lucide-react";
import { API_BASE } from "../../constants";
import { FILTER_PILL_ACTIVE, FILTER_PILL_INACTIVE } from "../ui/variants";
import PresetFormFields from "./PresetFormFields";

// ── Types ────────────────────────────────────────────────────

type CategoryOption = {
  value: string;
  label: string;
};

type AgentPreset = {
  id: number;
  name: string;
  role_description: string;
  system_prompt: string;
  model_provider: string;
  model_name: string;
  temperature: number;
  is_system: boolean;
  agent_role: string | null;
  category: string | null;
  agent_metadata: Record<string, unknown> | null;
  template_content: string | null;
  created_at: string | null;
};

type PresetsApiResponse = {
  presets: AgentPreset[];
  categories: CategoryOption[];
};

type NewPresetForm = {
  name: string;
  role_description: string;
  system_prompt: string;
  model_provider: string;
  model_name: string;
  temperature: number;
  agent_role: string;
  category: string;
};

const EMPTY_FORM: NewPresetForm = {
  name: "",
  role_description: "",
  system_prompt: "",
  model_provider: "gemini",
  model_name: "gemini-2.0-flash",
  temperature: 0.9,
  agent_role: "",
  category: "",
};

// ── Main Component ───────────────────────────────────────────

export default function AgentConfigPanel() {
  const [presets, setPresets] = useState<AgentPreset[]>([]);
  const [categories, setCategories] = useState<CategoryOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<NewPresetForm>({ ...EMPTY_FORM });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  const categoryLabels = Object.fromEntries(categories.map((c) => [c.value, c.label]));

  const fetchPresets = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get<PresetsApiResponse>(`${API_BASE}/lab/creative/agent-presets`);
      setPresets(res.data.presets);
      setCategories(res.data.categories);
    } catch {
      setError("Failed to load presets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPresets();
  }, [fetchPresets]);

  /** Convert empty strings to null for optional fields before API call. */
  const sanitizeForm = useCallback(
    (f: NewPresetForm) => ({
      ...f,
      agent_role: f.agent_role.trim() || null,
      category: f.category || null,
    }),
    []
  );

  const handleCreate = useCallback(async () => {
    if (!form.name.trim() || !form.role_description.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await axios.post(`${API_BASE}/lab/creative/agent-presets`, sanitizeForm(form));
      setForm({ ...EMPTY_FORM });
      setShowForm(false);
      await fetchPresets();
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? (err.response?.data?.detail ?? err.message)
        : "Failed to create preset";
      setError(String(msg));
    } finally {
      setSubmitting(false);
    }
  }, [form, fetchPresets, sanitizeForm]);

  const handleDelete = useCallback(
    async (id: number) => {
      try {
        await axios.delete(`${API_BASE}/lab/creative/agent-presets/${id}`);
        await fetchPresets();
      } catch (err) {
        const msg = axios.isAxiosError(err)
          ? (err.response?.data?.detail ?? err.message)
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
      agent_role: preset.agent_role ?? "",
      category: preset.category ?? "",
    });
    setShowForm(false);
  }, []);

  const handleUpdate = useCallback(async () => {
    if (!editingId || !form.name.trim() || !form.role_description.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await axios.put(`${API_BASE}/lab/creative/agent-presets/${editingId}`, sanitizeForm(form));
      setForm({ ...EMPTY_FORM });
      setEditingId(null);
      await fetchPresets();
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? (err.response?.data?.detail ?? err.message)
        : "Failed to update preset";
      setError(String(msg));
    } finally {
      setSubmitting(false);
    }
  }, [editingId, form, fetchPresets, sanitizeForm]);

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

  const filteredPresets = categoryFilter
    ? presets.filter((p) => p.category === categoryFilter)
    : presets;

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

      {/* Category tabs */}
      <div className="flex gap-1">
        <button
          onClick={() => setCategoryFilter(null)}
          className={`rounded-lg px-3 py-1 text-xs transition ${categoryFilter === null ? FILTER_PILL_ACTIVE : FILTER_PILL_INACTIVE
            }`}
        >
          All
        </button>
        {categories.map((cat) => (
          <button
            key={cat.value}
            onClick={() => setCategoryFilter(cat.value)}
            className={`rounded-lg px-3 py-1 text-xs transition ${categoryFilter === cat.value ? FILTER_PILL_ACTIVE : FILTER_PILL_INACTIVE
              }`}
          >
            {cat.label}
          </button>
        ))}
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
            categoryOptions={categories}
          />
        </div>
      )}

      {/* Preset list */}
      {filteredPresets.length === 0 ? (
        <div className="flex h-24 items-center justify-center rounded-xl border border-dashed border-zinc-300 bg-zinc-50 text-xs text-zinc-400">
          No presets yet
        </div>
      ) : (
        <div className="space-y-2">
          {filteredPresets.map((preset) => (
            <div key={preset.id} className="rounded-2xl border border-zinc-200 bg-white p-4">
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
                  categoryOptions={categories}
                />
              ) : (
                // View mode
                <>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-zinc-800">{preset.name}</span>
                      {preset.is_system && (
                        <span className="flex items-center gap-0.5 rounded bg-blue-50 px-1.5 py-0.5 text-[12px] font-semibold text-blue-600">
                          <Shield className="h-3 w-3" />
                          System
                        </span>
                      )}
                      {preset.category && categoryLabels[preset.category] && (
                        <span className="rounded bg-zinc-100 px-1.5 py-0.5 text-[12px] font-medium text-zinc-500">
                          {categoryLabels[preset.category]}
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
                  {preset.agent_role && (
                    <p className="mt-0.5 text-[12px] text-zinc-400">{preset.agent_role}</p>
                  )}
                  <p className="mt-1 text-xs text-zinc-500">{preset.role_description}</p>
                  <div className="mt-2 flex items-center gap-3 text-[12px] text-zinc-400">
                    <span>
                      {preset.model_provider}/{preset.model_name}
                    </span>
                    <span>temp: {preset.temperature}</span>
                  </div>

                  {/* Template Content (Read-only) */}
                  {preset.template_content && (
                    <div className="mt-4 space-y-1">
                      <p className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
                        Core Task Instructions (Read-only Template)
                      </p>
                      <div className="max-h-60 overflow-y-auto rounded-lg border border-zinc-100 bg-zinc-50/50 p-3">
                        <pre className="whitespace-pre-wrap font-mono text-[11px] text-zinc-500 leading-relaxed">
                          {preset.template_content}
                        </pre>
                      </div>
                      <p className="text-[11px] text-zinc-400 italic">
                        * 이 지시사항은 서버의 템플릿 파일(.j2)에서 관리되며, 시스템 프롬프트와 결합되어 LLM에게 전달됩니다.
                      </p>
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
