"use client";

import { useState } from "react";
import { Check, ExternalLink, Loader2 } from "lucide-react";
import type { CopyrightResult, MusicRecommendation } from "../../types/creative";
import CheckResultCard from "./CheckResultCard";

type SceneData = {
  order: number;
  script: string;
  speaker: string;
  duration: number;
  camera?: string;
  environment?: string;
  image_prompt?: string;
};

type Props = {
  scenes: SceneData[];
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
  const [groupId, setGroupId] = useState<string>("");
  const [title, setTitle] = useState("");
  const [deepParse, setDeepParse] = useState(false);

  const handleSend = async () => {
    const gid = parseInt(groupId, 10);
    if (isNaN(gid) || gid <= 0) return;
    setSending(true);
    try {
      await onSendToStudio(gid, title || undefined, deepParse);
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
              Group ID
            </label>
            <input
              type="number"
              value={groupId}
              onChange={(e) => setGroupId(e.target.value)}
              placeholder="Group ID"
              className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-xs focus:border-zinc-400 focus:outline-none"
            />
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
