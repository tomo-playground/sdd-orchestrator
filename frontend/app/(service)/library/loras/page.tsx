"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import axios from "axios";
import { API_BASE } from "../../../constants";
import type { LoRA } from "../../../types";

export default function LibraryLorasPage() {
  const [loraEntries, setLoraEntries] = useState<LoRA[]>([]);

  useEffect(() => {
    axios
      .get<LoRA[]>(`${API_BASE}/loras`)
      .then((res) => setLoraEntries(res.data || []))
      .catch(() => console.error("Failed to fetch LoRAs"));
  }, []);

  return (
    <div className="px-8 py-6">
      <div className="grid gap-6">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-zinc-800">Registered LoRAs</h2>
          <div className="flex items-center gap-3">
            <span className="rounded-full border border-zinc-200 bg-zinc-100 px-2.5 py-0.5 text-[11px] font-semibold text-zinc-500">
              {loraEntries.length}
            </span>
            <Link
              href="/dev/sd-models"
              className="rounded-lg border border-zinc-200 px-3 py-1 text-[11px] font-semibold text-zinc-500 transition hover:bg-zinc-100 hover:text-zinc-700"
            >
              Manage in Dev
            </Link>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {loraEntries.map((lora) => {
            const typeBadge =
              lora.lora_type === "style"
                ? "border-violet-200 bg-violet-50 text-violet-600"
                : "border-sky-200 bg-sky-50 text-sky-600";
            return (
              <div
                key={lora.id}
                className="rounded-2xl border border-zinc-200 bg-white p-4 transition hover:border-violet-200 hover:shadow-sm"
              >
                <div className="flex items-center gap-2">
                  <p className="truncate text-xs font-bold text-zinc-700">
                    {lora.display_name || lora.name}
                  </p>
                  <span
                    className={`shrink-0 rounded-full border px-1.5 py-0.5 text-[11px] font-semibold ${typeBadge}`}
                  >
                    {lora.lora_type || "character"}
                  </span>
                  {lora.base_model && (
                    <span className="shrink-0 rounded-full border border-zinc-200 bg-zinc-100 px-1.5 py-0.5 text-[11px] font-semibold text-zinc-500">
                      {lora.base_model}
                    </span>
                  )}
                  {lora.is_multi_character_capable && (
                    <span className="shrink-0 rounded-full border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-[11px] font-semibold text-emerald-600">
                      Multi
                    </span>
                  )}
                </div>
                {lora.display_name && lora.display_name !== lora.name && (
                  <p className="mt-0.5 truncate font-mono text-[11px] text-zinc-400">{lora.name}</p>
                )}
                <p className="mt-1 text-[11px] text-zinc-400">
                  trigger: {lora.trigger_words?.join(", ") || "none"}
                </p>
                <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-zinc-400">
                  <span>w: {lora.default_weight}</span>
                  <span>
                    range: {lora.weight_min}&ndash;{lora.weight_max}
                  </span>
                  {lora.civitai_url && (
                    <a
                      href={lora.civitai_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-400 underline hover:text-indigo-600"
                    >
                      Civitai
                    </a>
                  )}
                </div>
                {lora.preview_image_url && (
                  <div className="mt-3 aspect-[3/2] w-full overflow-hidden rounded-lg bg-zinc-100">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={lora.preview_image_url}
                      alt=""
                      className="h-full w-full object-cover opacity-80"
                    />
                  </div>
                )}
              </div>
            );
          })}
          {loraEntries.length === 0 && (
            <p className="col-span-full py-12 text-center text-xs text-zinc-400">
              No LoRAs registered. Import from Civitai in Dev &gt; SD Models.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
