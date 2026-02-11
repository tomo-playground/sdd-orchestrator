"use client";

import { useEffect, useState } from "react";
import { format } from "date-fns";

interface Storyboard {
    id: number;
    title: string;
    description: string | null;
    created_at: string | null;
    updated_at: string | null;
}

interface StoryboardListProps {
    selectedStoryboardId: number | null;
    onSelect: (id: number, title: string) => void;
}

export default function StoryboardList({ selectedStoryboardId, onSelect }: StoryboardListProps) {
    const [storyboards, setStoryboards] = useState<Storyboard[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        async function fetchStoryboards() {
            try {
                const res = await fetch("http://127.0.0.1:8000/storyboards");
                if (!res.ok) throw new Error("Failed to fetch storyboards");
                const data = await res.json();
                setStoryboards(data);
            } catch (err) {
                console.error(err);
                setError("Failed to load storyboards");
            } finally {
                setIsLoading(false);
            }
        }
        fetchStoryboards();
    }, []);

    if (isLoading) {
        return <div className="text-zinc-500 text-xs p-4">Loading storyboards...</div>;
    }

    if (error) {
        return <div className="text-red-400 text-xs p-4">{error}</div>;
    }

    if (storyboards.length === 0) {
        return <div className="text-zinc-500 text-xs p-4">No storyboards found.</div>;
    }

    return (
        <div className="grid grid-cols-1 gap-2 p-2">
            {storyboards.map((sb) => (
                <button
                    key={sb.id}
                    onClick={() => onSelect(sb.id, sb.title)}
                    className={`flex flex-col items-start gap-1 rounded-xl border p-3 text-left transition hover:bg-zinc-50/50 ${selectedStoryboardId === sb.id
                            ? "border-zinc-900 bg-white shadow-sm ring-1 ring-zinc-900/50"
                            : "border-transparent bg-white/50 hover:border-zinc-200"
                        }`}
                >
                    <span className="text-sm font-medium text-zinc-900">{sb.title}</span>
                    {sb.description && (
                        <span className="text-[12px] text-zinc-500 line-clamp-1">
                            {sb.description}
                        </span>
                    )}
                    <span className="text-[11px] text-zinc-400">
                        {sb.updated_at
                            ? format(new Date(sb.updated_at), "yyyy.MM.dd HH:mm")
                            : "No date"}
                    </span>
                </button>
            ))}
        </div>
    );
}
