"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
import Button from "../ui/Button";
import { API_BASE } from "../../constants";

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export default function WelcomeBar() {
  const router = useRouter();
  const [totalCount, setTotalCount] = useState<number | null>(null);

  useEffect(() => {
    async function fetchCount() {
      try {
        const res = await fetch(`${API_BASE}/storyboards?limit=1`);
        if (!res.ok) return;
        const data = await res.json();
        setTotalCount(data.total ?? 0);
      } catch {
        setTotalCount(0);
      }
    }
    fetchCount();
  }, []);

  const summary =
    totalCount === null
      ? ""
      : totalCount === 0
        ? "Create your first story to get started"
        : `${totalCount} storyboard${totalCount !== 1 ? "s" : ""} in progress`;

  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-lg font-bold text-zinc-900">{getGreeting()}</h1>
        {summary && <p className="mt-0.5 text-sm text-zinc-500">{summary}</p>}
      </div>
      <Button variant="primary" size="md" onClick={() => router.push("/studio?new=true")}>
        <Plus className="h-4 w-4" />
        New Story
      </Button>
    </div>
  );
}
