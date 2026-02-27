import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { ADMIN_API_BASE } from "../../../constants";

// ── Types ──────────────────────────────────────────────

export type StorageStats = {
  total_size_mb: number;
  total_count: number;
  directories: Record<string, { count: number; size_mb: number }>;
};

export type CleanupResult = {
  deleted_count: number;
  freed_mb: number;
  dry_run: boolean;
  details: Record<string, { deleted: number; freed_mb: number; files?: string[] }>;
};

type AutoEditSettings = {
  enabled: boolean;
  threshold: number;
  max_cost_per_storyboard: number;
  max_retries_per_scene: number;
};

type CostSummary = {
  today: number;
  this_week: number;
  this_month: number;
  total: number;
  edit_count_today: number;
  edit_count_month: number;
};

export type EditAnalytics = {
  total_edits: number;
  total_cost_usd: number;
  avg_improvement: number;
  edits: Array<{
    id: number;
    storyboard_id: number;
    scene_id: number;
    original_match_rate: number;
    final_match_rate: number;
    improvement: number;
    cost_usd: number;
    created_at: string;
  }>;
  by_improvement_range: Record<string, number>;
};

type CleanupOptions = {
  cleanup_videos: boolean;
  video_max_age_days: number;
  cleanup_cache: boolean;
  cleanup_test_folders: boolean;
  cleanup_candidates: boolean;
};

export type MediaStats = {
  total_assets: number;
  temp_assets: number;
  null_owner_assets: number;
  orphan_count: number;
  by_owner_type: Record<string, number>;
};

export type OrphanInfo = {
  id: number;
  storage_key: string;
  owner_type: string | null;
  reason: string;
};

export type OrphanReport = {
  null_owner: OrphanInfo[];
  broken_fk: OrphanInfo[];
  expired_temp: OrphanInfo[];
  total: number;
};

export type MediaCleanupResult = {
  orphans: { deleted: number; storage_errors: string[]; dry_run: boolean };
  expired_temp: { deleted: number; storage_errors: string[]; dry_run: boolean };
  total_deleted: number;
};

export type CacheRefreshResult = {
  success: boolean;
  message?: string;
  error?: string;
};

import type { UiCallbacks } from "../../../types";

// ── Hook ───────────────────────────────────────────────

export function useSettingsTab(ui: UiCallbacks) {
  // Storage state
  const [storageStats, setStorageStats] = useState<StorageStats | null>(null);
  const [isLoadingStorage, setIsLoadingStorage] = useState(false);
  const [cleanupResult, setCleanupResult] = useState<CleanupResult | null>(null);
  const [isCleaningUp, setIsCleaningUp] = useState(false);
  const [cleanupOptions, setCleanupOptions] = useState<CleanupOptions>({
    cleanup_videos: true,
    video_max_age_days: 7,
    cleanup_cache: true,
    cleanup_test_folders: true,
    cleanup_candidates: false,
  });

  // Gemini Auto Edit state
  const [autoEditSettings, setAutoEditSettings] = useState<AutoEditSettings | null>(null);
  const [costSummary, setCostSummary] = useState<CostSummary | null>(null);
  const [isLoadingAutoEdit, setIsLoadingAutoEdit] = useState(false);

  // Gemini Analytics state
  const [analytics, setAnalytics] = useState<EditAnalytics | null>(null);
  const [isLoadingAnalytics, setIsLoadingAnalytics] = useState(false);
  const [analyticsStoryboardFilter, setAnalyticsStoryboardFilter] = useState<number | null>(null);

  // Media Assets GC state
  const [mediaStats, setMediaStats] = useState<MediaStats | null>(null);
  const [isLoadingMediaStats, setIsLoadingMediaStats] = useState(false);
  const [orphanReport, setOrphanReport] = useState<OrphanReport | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [mediaCleanupResult, setMediaCleanupResult] = useState<MediaCleanupResult | null>(null);
  const [isMediaCleaning, setIsMediaCleaning] = useState(false);

  // Cache Refresh state
  const [isRefreshingCaches, setIsRefreshingCaches] = useState(false);
  const [cacheRefreshResult, setCacheRefreshResult] = useState<CacheRefreshResult | null>(null);

  // ── Fetchers ───────────────────────────────────────

  const fetchStorageStats = useCallback(async () => {
    setIsLoadingStorage(true);
    try {
      const res = await axios.get(`${ADMIN_API_BASE}/storage/stats`);
      setStorageStats(res.data);
    } catch {
      setStorageStats(null);
    } finally {
      setIsLoadingStorage(false);
    }
  }, []);

  const handleCleanup = useCallback(
    async (dryRun: boolean) => {
      setIsCleaningUp(true);
      setCleanupResult(null);
      try {
        const res = await axios.post(`${ADMIN_API_BASE}/storage/cleanup`, {
          ...cleanupOptions,
          dry_run: dryRun,
        });
        setCleanupResult(res.data);
        if (!dryRun) {
          const statsRes = await axios.get(`${ADMIN_API_BASE}/storage/stats`);
          setStorageStats(statsRes.data);
        }
      } catch (error) {
        const msg = axios.isAxiosError(error)
          ? (error.response?.data?.detail ?? error.message)
          : "Unknown error";
        ui.showToast(`Cleanup failed: ${msg}`, "error");
      } finally {
        setIsCleaningUp(false);
      }
    },
    [cleanupOptions, ui]
  );

  const fetchAutoEditSettings = useCallback(async () => {
    setIsLoadingAutoEdit(true);
    try {
      const [settingsRes, costRes] = await Promise.all([
        axios.get(`${ADMIN_API_BASE}/settings/auto-edit`),
        axios.get(`${ADMIN_API_BASE}/settings/auto-edit/cost-summary`),
      ]);
      setAutoEditSettings(settingsRes.data);
      setCostSummary(costRes.data);
    } catch {
      setAutoEditSettings(null);
      setCostSummary(null);
    } finally {
      setIsLoadingAutoEdit(false);
    }
  }, []);

  const fetchAnalytics = useCallback(async (storyboardId?: number | null) => {
    setIsLoadingAnalytics(true);
    try {
      const params = storyboardId ? { storyboard_id: storyboardId } : {};
      const res = await axios.get(`${ADMIN_API_BASE}/analytics/gemini-edits`, { params });
      setAnalytics(res.data);
    } catch {
      setAnalytics(null);
    } finally {
      setIsLoadingAnalytics(false);
    }
  }, []);

  // ── Media Assets GC ────────────────────────────────

  const fetchMediaStats = useCallback(async () => {
    setIsLoadingMediaStats(true);
    try {
      const res = await axios.get(`${ADMIN_API_BASE}/media-assets/stats`);
      setMediaStats(res.data);
    } catch {
      setMediaStats(null);
    } finally {
      setIsLoadingMediaStats(false);
    }
  }, []);

  const handleOrphanScan = useCallback(async () => {
    setIsScanning(true);
    setOrphanReport(null);
    try {
      const res = await axios.get(`${ADMIN_API_BASE}/media-assets/orphans`);
      setOrphanReport(res.data);
    } catch {
      setOrphanReport(null);
    } finally {
      setIsScanning(false);
    }
  }, []);

  const handleMediaCleanup = useCallback(
    async (dryRun: boolean) => {
      setIsMediaCleaning(true);
      setMediaCleanupResult(null);
      try {
        const res = await axios.post(`${ADMIN_API_BASE}/media-assets/cleanup`, null, {
          params: { dry_run: dryRun },
        });
        setMediaCleanupResult(res.data);
        if (!dryRun) void fetchMediaStats();
      } catch (error) {
        const msg = axios.isAxiosError(error)
          ? (error.response?.data?.detail ?? error.message)
          : "Unknown error";
        ui.showToast(`Media cleanup failed: ${msg}`, "error");
      } finally {
        setIsMediaCleaning(false);
      }
    },
    [fetchMediaStats, ui]
  );

  // ── Cache Refresh ────────────────────────────────

  const handleRefreshCaches = useCallback(async () => {
    setIsRefreshingCaches(true);
    setCacheRefreshResult(null);
    try {
      const res = await axios.post(`${ADMIN_API_BASE}/refresh-caches`);
      setCacheRefreshResult(res.data);
    } catch {
      setCacheRefreshResult({ success: false, error: "Request failed" });
    } finally {
      setIsRefreshingCaches(false);
      setTimeout(() => setCacheRefreshResult(null), 5000);
    }
  }, []);

  // ── Effects ────────────────────────────────────────

  useEffect(() => {
    void fetchStorageStats();
    void fetchAutoEditSettings();
    void fetchAnalytics(analyticsStoryboardFilter);
    void fetchMediaStats();
  }, [analyticsStoryboardFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    // Storage
    storageStats,
    isLoadingStorage,
    cleanupResult,
    isCleaningUp,
    cleanupOptions,
    setCleanupOptions,
    fetchStorageStats,
    handleCleanup,
    // Auto Edit
    autoEditSettings,
    costSummary,
    isLoadingAutoEdit,
    fetchAutoEditSettings,
    // Analytics
    analytics,
    isLoadingAnalytics,
    analyticsStoryboardFilter,
    setAnalyticsStoryboardFilter,
    fetchAnalytics,
    // Media Assets GC
    mediaStats,
    isLoadingMediaStats,
    fetchMediaStats,
    orphanReport,
    isScanning,
    handleOrphanScan,
    mediaCleanupResult,
    isMediaCleaning,
    handleMediaCleanup,
    // Cache Refresh
    isRefreshingCaches,
    cacheRefreshResult,
    handleRefreshCaches,
  };
}
