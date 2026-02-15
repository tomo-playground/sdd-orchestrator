import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API_BASE } from "../constants";
import type { Background } from "../types";
import type { UiCallbacks } from "../types";

export type EditingBackground = {
  name: string;
  description: string;
  tags: string; // comma-separated, converted to string[] on save
  category: string;
  weight: number;
};

export const EMPTY_BACKGROUND: EditingBackground = {
  name: "",
  description: "",
  tags: "",
  category: "",
  weight: 0.3,
};

// ── Hook ───────────────────────────────────────────────

export function useBackgrounds(ui: UiCallbacks) {
  const [backgrounds, setBackgrounds] = useState<Background[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [editing, setEditing] = useState<EditingBackground | null>(null);
  const [editId, setEditId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState<number | null>(null);

  const fetchBackgrounds = useCallback(async () => {
    try {
      const res = await axios.get<Background[]>(`${API_BASE}/backgrounds`);
      setBackgrounds(res.data);
    } catch {
      console.error("Failed to fetch backgrounds");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await axios.get<string[]>(`${API_BASE}/backgrounds/categories`);
      setCategories(res.data);
    } catch {
      console.error("Failed to fetch categories");
    }
  }, []);

  useEffect(() => {
    void fetchBackgrounds();
    void fetchCategories();
  }, [fetchBackgrounds, fetchCategories]);

  const handleCreate = useCallback(() => {
    setEditId(null);
    setEditing({ ...EMPTY_BACKGROUND });
  }, []);

  const handleEdit = useCallback((bg: Background) => {
    setEditId(bg.id);
    setEditing({
      name: bg.name,
      description: bg.description ?? "",
      tags: bg.tags?.join(", ") ?? "",
      category: bg.category ?? "",
      weight: bg.weight,
    });
  }, []);

  const handleDelete = useCallback(
    async (bg: Background) => {
      const ok = await ui.confirmDialog({
        title: "Delete Background",
        message: `Delete "${bg.name}"?`,
        confirmLabel: "Delete",
        variant: "danger",
      });
      if (!ok) return;
      try {
        await axios.delete(`${API_BASE}/backgrounds/${bg.id}`);
        await fetchBackgrounds();
        await fetchCategories();
      } catch (error) {
        const msg = axios.isAxiosError(error)
          ? (error.response?.data?.detail ?? error.message)
          : "Unknown error";
        ui.showToast(`Delete failed: ${msg}`, "error");
      }
    },
    [fetchBackgrounds, fetchCategories, ui]
  );

  const handleSave = useCallback(async () => {
    if (!editing?.name.trim()) return;
    setSaving(true);
    const tags = editing.tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    const payload = {
      name: editing.name,
      description: editing.description || null,
      tags: tags.length > 0 ? tags : null,
      category: editing.category || null,
      weight: editing.weight,
    };
    try {
      if (editId) {
        await axios.put(`${API_BASE}/backgrounds/${editId}`, payload);
      } else {
        await axios.post(`${API_BASE}/backgrounds`, payload);
      }
      setEditing(null);
      setEditId(null);
      await fetchBackgrounds();
      await fetchCategories();
    } catch (error) {
      const msg = axios.isAxiosError(error)
        ? (error.response?.data?.detail ?? error.message)
        : "Unknown error";
      ui.showToast(`Save failed: ${msg}`, "error");
    } finally {
      setSaving(false);
    }
  }, [editing, editId, fetchBackgrounds, fetchCategories, ui]);

  const handleCancel = useCallback(() => {
    setEditing(null);
    setEditId(null);
  }, []);

  const handleUploadImage = useCallback(
    async (bgId: number, file: File) => {
      setUploading(bgId);
      try {
        const formData = new FormData();
        formData.append("file", file);
        await axios.post(`${API_BASE}/backgrounds/${bgId}/upload-image`, formData);
        await fetchBackgrounds();
        ui.showToast("Image uploaded", "success");
      } catch (error) {
        const msg = axios.isAxiosError(error)
          ? (error.response?.data?.detail ?? error.message)
          : "Unknown error";
        ui.showToast(`Upload failed: ${msg}`, "error");
      } finally {
        setUploading(null);
      }
    },
    [fetchBackgrounds, ui]
  );

  const set = useCallback(
    <K extends keyof EditingBackground>(key: K, value: EditingBackground[K]) =>
      setEditing((prev) => (prev ? { ...prev, [key]: value } : prev)),
    []
  );

  return {
    backgrounds,
    categories,
    isLoading,
    editing,
    editId,
    saving,
    uploading,
    handleCreate,
    handleEdit,
    handleDelete,
    handleSave,
    handleCancel,
    handleUploadImage,
    set,
  };
}
