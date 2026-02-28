"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Users, Palette, Mic, Music, Loader2 } from "lucide-react";
import { API_BASE } from "../../constants";

type Stats = {
  characters: number;
  styles: number;
  voices: number;
  music: number;
};

export default function QuickStatsBar() {
  const router = useRouter();
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const [charactersRes, stylesRes, voicesRes, musicRes] = await Promise.all([
          fetch(`${API_BASE}/characters`),
          fetch(`${API_BASE}/style-profiles`),
          fetch(`${API_BASE}/voice-presets`),
          fetch(`${API_BASE}/music-presets`),
        ]);

        const [characters, styles, voices, music] = await Promise.all([
          charactersRes.json(),
          stylesRes.json(),
          voicesRes.json(),
          musicRes.json(),
        ]);

        setStats({
          characters: characters?.total ?? (Array.isArray(characters) ? characters.length : 0),
          styles: Array.isArray(styles) ? styles.length : 0,
          voices: Array.isArray(voices) ? voices.length : 0,
          music: Array.isArray(music) ? music.length : 0,
        });
      } catch (error) {
        console.error("Failed to fetch stats:", error);
        setStats({ characters: 0, styles: 0, voices: 0, music: 0 });
      } finally {
        setLoading(false);
      }
    }

    fetchStats();
  }, []);

  const statItems = [
    {
      id: "characters",
      label: "Characters",
      icon: Users,
      count: stats?.characters ?? 0,
      href: "/library/characters",
    },
    {
      id: "styles",
      label: "Styles",
      icon: Palette,
      count: stats?.styles ?? 0,
      href: "/library/styles",
    },
    {
      id: "voices",
      label: "Voices",
      icon: Mic,
      count: stats?.voices ?? 0,
      href: "/library/voices",
    },
    {
      id: "music",
      label: "Music",
      icon: Music,
      count: stats?.music ?? 0,
      href: "/library/music",
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center rounded-xl border border-zinc-200 bg-white p-4">
        <Loader2 className="h-4 w-4 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
      {statItems.map((item) => {
        const Icon = item.icon;
        return (
          <button
            key={item.id}
            onClick={() => router.push(item.href)}
            className="group flex items-center gap-3 rounded-xl border border-zinc-200 bg-white px-4 py-3 text-left transition hover:border-zinc-300 hover:shadow-sm"
          >
            <Icon className="h-4 w-4 shrink-0 text-zinc-400 transition group-hover:text-zinc-600" />
            <div className="min-w-0">
              <span className="text-base font-bold text-zinc-900">{item.count}</span>
              <span className="ml-1.5 text-xs text-zinc-500">{item.label}</span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
