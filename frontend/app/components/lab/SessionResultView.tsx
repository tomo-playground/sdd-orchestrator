"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { Check, ExternalLink, Loader2 } from "lucide-react";
import { API_BASE } from "../../constants";
import type {
  CopyrightResult,
  CreativeSceneSummary,
  MusicRecommendation,
} from "../../types/creative";
import CheckResultCard from "./CheckResultCard";

type Group = {
  id: number;
  name: string;
  project_id: number;
};

type Props = {
  scenes: CreativeSceneSummary[];
  topic: string;
  musicRecommendation?: MusicRecommendation;
  copyrightResult?: CopyrightResult;
  onSendToStudio: (groupId: number, title?: string, deepParse?: boolean) => Promise<void>;
};

export default function SessionResultView({
  scenes,
  topic,
  musicRecommendation,
  copyrightResult,
  onSendToStudio,
}: Props) {
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [groups, setGroups] = useState<Group[]>([]);
  const [groupId, setGroupId] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [deepParse, setDeepParse] = useState(false);

  useEffect(() => {
    axios
      .get<Group[]>(`${API_BASE}/groups`)
      .then((res) => {
        setGroups(res.data);
        if (res.data.length > 0) {
          setGroupId(res.data[0].id);
        }
      })
      .catch(() => setGroups([]));
  }, []);

  const handleSend = async () => {
    if (!groupId) return;
    setSending(true);
    try {
      await onSendToStudio(groupId, title || undefined, deepParse);
      setSent(true);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-4 rounded-2xl border border-emerald-200 bg-white p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[10px] font-semibold tracking-wider text-emerald-600 uppercase">
            Complete
          </p>
          <p className="text-xs text-zinc-600">{scenes.length} scenes ready</p>
        </div>
      </div>

      {/* Scene table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr>
              <th className="border-b border-zinc-100 px-3 py-1.5 text-left text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
                #
              </th>
              <th className="border-b border-zinc-100 px-3 py-1.5 text-left text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
                Script
              </th>
              <th className="border-b border-zinc-100 px-3 py-1.5 text-left text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
                Speaker
              </th>
              <th className="border-b border-zinc-100 px-3 py-1.5 text-left text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
                Duration
              </th>
              <th className="border-b border-zinc-100 px-3 py-1.5 text-left text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
                Scene (KO)
              </th>
              <th className="border-b border-zinc-100 px-3 py-1.5 text-left text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
                Camera
              </th>
              <th className="border-b border-zinc-100 px-3 py-1.5 text-left text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
                Environment
              </th>
            </tr>
          </thead>
          <tbody>
            {scenes.map((s, i) => (
              <tr key={i} className="border-b border-zinc-50">
                <td className="px-3 py-2 font-mono text-[10px] text-zinc-400">{s.order}</td>
                <td className="max-w-xs truncate px-3 py-2 text-zinc-700">{s.script}</td>
                <td className="px-3 py-2 text-zinc-500">{s.speaker}</td>
                <td className="px-3 py-2 text-zinc-500">{s.duration}s</td>
                <td
                  className="max-w-[200px] truncate px-3 py-2 text-zinc-500"
                  title={s.image_prompt_ko ?? ""}
                >
                  {s.image_prompt_ko ?? "-"}
                </td>
                <td className="px-3 py-2 text-zinc-500">{s.camera ?? "-"}</td>
                <td className="px-3 py-2 text-zinc-500">{s.environment ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Music Recommendation */}
      {musicRecommendation && (
        <div className="rounded-lg border border-purple-200 bg-purple-50 p-3">
          <p className="text-[10px] font-semibold tracking-wider text-purple-700 uppercase">
            BGM Recommendation
          </p>
          <p className="mt-1 text-xs text-purple-800">{musicRecommendation.prompt}</p>
          <div className="mt-1 flex gap-3 text-[10px] text-purple-600">
            <span>Mood: {musicRecommendation.mood}</span>
            <span>{musicRecommendation.duration}s</span>
          </div>
          <p className="mt-1 text-[10px] text-zinc-500">{musicRecommendation.reasoning}</p>
        </div>
      )}

      {/* Copyright Result */}
      {copyrightResult && <CheckResultCard result={copyrightResult} />}

      {/* Send to Studio */}
      {!sent ? (
        <div className="flex items-end gap-3 border-t border-zinc-100 pt-3">
          <div className="flex-1">
            <label className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
              Group
            </label>
            <select
              value={groupId ?? ""}
              onChange={(e) => setGroupId(e.target.value ? Number(e.target.value) : null)}
              className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
            >
              {groups.length === 0 ? (
                <option value="">No groups available</option>
              ) : (
                groups.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name}
                  </option>
                ))
              )}
            </select>
          </div>
          <div className="flex-1">
            <label className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
              Title (optional)
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={topic.slice(0, 50)}
              className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-xs focus:border-zinc-400 focus:outline-none"
            />
          </div>
          <div className="flex flex-col items-end gap-1.5">
            <label className="flex items-center gap-1.5 text-[10px] text-zinc-500">
              <input
                type="checkbox"
                checked={deepParse}
                onChange={(e) => setDeepParse(e.target.checked)}
                className="rounded border-zinc-300"
              />
              Deep Parse (V3 Prompt)
            </label>
            <button
              onClick={handleSend}
              disabled={sending || !groupId}
              className="flex items-center gap-1 rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-semibold text-white transition hover:bg-emerald-500 disabled:bg-zinc-300"
            >
              {sending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <ExternalLink className="h-3.5 w-3.5" />
              )}
              Send to Studio
            </button>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2">
          <Check className="h-4 w-4 text-emerald-600" />
          <span className="text-xs font-semibold text-emerald-700">Sent to Studio</span>
        </div>
      )}
    </div>
  );
}
