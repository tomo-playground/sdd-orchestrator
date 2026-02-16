"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Users, Palette, Mic, Music, Loader2 } from "lucide-react";

type Stats = {
  characters: number;
  styles: number;
  voices: number;
  music: number;
};

export default function QuickStatsWidget() {
  const router = useRouter();
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const [charactersRes, stylesRes, voicesRes, musicRes] = await Promise.all([
          fetch("/api/characters"),
          fetch("/api/style-profiles"),
          fetch("/api/voice-presets"),
          fetch("/api/music-presets"),
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
      href: "/library?tab=characters",
    },
    {
      id: "styles",
      label: "Styles",
      icon: Palette,
      count: stats?.styles ?? 0,
      href: "/library?tab=style",
    },
    {
      id: "voices",
      label: "Voices",
      icon: Mic,
      count: stats?.voices ?? 0,
      href: "/library?tab=voices",
    },
    {
      id: "music",
      label: "Music",
      icon: Music,
      count: stats?.music ?? 0,
      href: "/library?tab=music",
    },
  ];

  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold text-zinc-900">Your Library</h3>

      {loading ? (
        <div className="flex items-center justify-center rounded-xl border border-zinc-200 bg-white p-6">
          <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          {statItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => router.push(item.href)}
                className="group flex flex-col items-center gap-2 rounded-xl border border-zinc-200 bg-white p-3 transition hover:border-zinc-300 hover:shadow-sm"
              >
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4 text-zinc-500" />
                  <span className="text-xl font-bold text-zinc-900">{item.count}</span>
                </div>
                <span className="text-xs font-medium text-zinc-600">{item.label}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
