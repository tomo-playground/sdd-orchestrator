import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import type { StyleProfile, StyleProfileFull, LoRA, SDModelEntry, Embedding } from "../../types";

// ── Types ──────────────────────────────────────────────

export type CivitaiResult = {
    civitai_id: number;
    name: string;
    type: "LORA" | "Checkpoint";
    trigger_words: string[];
    base_model: string;
    preview_image: string;
    civitai_url: string;
};

// ── Hook ───────────────────────────────────────────────

export function useStyleTab() {
    const [styleProfiles, setStyleProfiles] = useState<StyleProfile[]>([]);
    const [selectedProfile, setSelectedProfile] = useState<StyleProfileFull | null>(null);
    const [isStyleLoading, setIsStyleLoading] = useState(false);

    const [loraEntries, setLoraEntries] = useState<LoRA[]>([]);
    const [sdModels, setSdModels] = useState<SDModelEntry[]>([]);
    const [embeddings, setEmbeddings] = useState<Embedding[]>([]);

    // Editing state for Civitai LoRA
    const [editingLora, setEditingLora] = useState<LoRA | null>(null);
    const [isUpdatingLora, setIsUpdatingLora] = useState(false);

    // Civitai Search
    const [civitaiSearch, setCivitaiSearch] = useState("");
    const [civitaiResults, setCivitaiResults] = useState<CivitaiResult[]>([]);
    const [isSearchingCivitai, setIsSearchingCivitai] = useState(false);

    // ── Fetchers ───────────────────────────────────────

    const fetchStyles = useCallback(async () => {
        setIsStyleLoading(true);
        try {
            const res = await axios.get<StyleProfile[]>(`${API_BASE}/style-profiles/`);
            setStyleProfiles(res.data || []);
        } catch {
            console.error("Failed to fetch styles");
        } finally {
            setIsStyleLoading(false);
        }
    }, []);

    const fetchSdModels = useCallback(async () => {
        try {
            const res = await axios.get<SDModelEntry[]>(`${API_BASE}/sd-models`);
            setSdModels(res.data || []);
        } catch {
            console.error("Failed to fetch SD models");
        }
    }, []);

    const fetchEmbeddings = useCallback(async () => {
        try {
            const res = await axios.get<Embedding[]>(`${API_BASE}/embeddings`);
            setEmbeddings(res.data || []);
        } catch {
            console.error("Failed to fetch embeddings");
        }
    }, []);

    const fetchPublicLoras = useCallback(async () => {
        try {
            const res = await axios.get<LoRA[]>(`${API_BASE}/loras/`);
            setLoraEntries(res.data || []);
        } catch {
            console.error("Failed to fetch public LoRAs");
        }
    }, []);

    // ── Style CRUD ─────────────────────────────────────

    const handleCreateStyle = useCallback(async () => {
        const name = prompt("New Style Name:");
        if (!name) return;
        try {
            await axios.post(`${API_BASE}/style-profiles/`, { name });
            await fetchStyles();
        } catch {
            alert("Failed to create style");
        }
    }, [fetchStyles]);

    const handleDeleteStyle = useCallback(async (id: number) => {
        if (!confirm("Delete this style?")) return;
        try {
            await axios.delete(`${API_BASE}/style-profiles/${id}`);
            setSelectedProfile((prev) => (prev?.id === id ? null : prev));
            await fetchStyles();
        } catch {
            alert("Failed to delete style");
        }
    }, [fetchStyles]);

    const handleUpdateStyle = useCallback(async (id: number, data: Partial<StyleProfile>) => {
        try {
            await axios.put(`${API_BASE}/style-profiles/${id}`, data);
            await fetchStyles();
            setSelectedProfile((prev) => {
                if (prev && prev.id === id) {
                    // Trigger reload of full profile
                    void axios.get<StyleProfileFull>(`${API_BASE}/style-profiles/${id}`)
                        .then((res) => setSelectedProfile(res.data));
                }
                return prev;
            });
        } catch {
            alert("Failed to update style");
        }
    }, [fetchStyles]);

    const handleDuplicateStyle = useCallback(async (id: number) => {
        const original = styleProfiles.find((s) => s.id === id);
        if (!original) return;
        const newName = `${original.name} (Copy)`;
        if (!confirm(`Duplicate style as "${newName}"?`)) return;

        try {
            const createRes = await axios.post<{ id: number; name: string }>(`${API_BASE}/style-profiles/`, {
                name: newName,
            });
            const newId = createRes.data.id;
            const detailRes = await axios.get<StyleProfileFull>(`${API_BASE}/style-profiles/${id}`);
            const fullOriginal = detailRes.data;

            await axios.put(`${API_BASE}/style-profiles/${newId}`, {
                default_positive: fullOriginal.default_positive,
                default_negative: fullOriginal.default_negative,
            });
            await fetchStyles();
        } catch {
            alert("Failed to duplicate style");
        }
    }, [fetchStyles, styleProfiles]);

    const handleLoadProfile = useCallback(async (id: number) => {
        try {
            const res = await axios.get<StyleProfileFull>(`${API_BASE}/style-profiles/${id}`);
            setSelectedProfile(res.data);
        } catch {
            alert("Failed to load style details");
        }
    }, []);

    // ── Civitai ────────────────────────────────────────

    const handleCivitaiSearch = useCallback(async () => {
        if (!civitaiSearch.trim()) return;
        setIsSearchingCivitai(true);
        setCivitaiResults([]);
        try {
            const res = await axios.get<{ results: CivitaiResult[] }>(`${API_BASE}/loras/search-civitai`, {
                params: { query: civitaiSearch, limit: 10 },
            });
            setCivitaiResults(res.data.results || []);
        } catch {
            alert("Search failed or no results");
        } finally {
            setIsSearchingCivitai(false);
        }
    }, [civitaiSearch]);

    const handleDownloadModel = useCallback(async (modelId: number, type: "LORA" | "Checkpoint") => {
        if (type !== "LORA") {
            alert("Only LoRA download is supported by backend for now.");
            return;
        }
        const userConfirm = confirm(`Download this LoRA (ID: ${modelId})? It may take a while.`);
        if (!userConfirm) return;

        try {
            await axios.post(`${API_BASE}/loras/import-civitai/${modelId}`);
            alert("Download started. Check database later.");
        } catch {
            alert("Download request failed");
        }
    }, []);

    // ── LoRA CRUD ──────────────────────────────────────

    const handleUpdateLora = useCallback(async () => {
        if (!editingLora) return;
        setIsUpdatingLora(true);
        try {
            await axios.put(`${API_BASE}/loras/${editingLora.id}`, {
                name: editingLora.name,
                trigger_words: editingLora.trigger_words,
                default_weight: editingLora.default_weight,
            });
            setEditingLora(null);
            await fetchPublicLoras();
        } catch {
            alert("Failed to update LoRA");
        } finally {
            setIsUpdatingLora(false);
        }
    }, [editingLora, fetchPublicLoras]);

    const handleDeleteLora = useCallback(async (id: number) => {
        if (!confirm("Delete this LoRA registration? (File/Weights might remain on disk, this removes DB entry)")) return;
        try {
            await axios.delete(`${API_BASE}/loras/${id}`);
            await fetchPublicLoras();
        } catch {
            alert("Failed to delete LoRA");
        }
    }, [fetchPublicLoras]);

    // ── Effects ────────────────────────────────────────

    useEffect(() => {
        void fetchStyles();
        void fetchSdModels();
        void fetchEmbeddings();
        void fetchPublicLoras();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    return {
        // Styles
        styleProfiles,
        selectedProfile,
        setSelectedProfile,
        isStyleLoading,
        handleCreateStyle,
        handleDeleteStyle,
        handleUpdateStyle,
        handleDuplicateStyle,
        handleLoadProfile,
        // Models & Embeddings
        sdModels,
        embeddings,
        loraEntries,
        // LoRA editing
        editingLora,
        setEditingLora,
        isUpdatingLora,
        handleUpdateLora,
        handleDeleteLora,
        // Civitai
        civitaiSearch,
        setCivitaiSearch,
        civitaiResults,
        isSearchingCivitai,
        handleCivitaiSearch,
        handleDownloadModel,
    };
}
