"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import { API_BASE } from "../../constants";
import type { Character, ProjectItem } from "../../types";

type Props = {
  project?: ProjectItem;
  onSave: (data: { name: string; description?: string; handle?: string; avatar_key?: string }) => Promise<void>;
  onClose: () => void;
};

export default function ProjectFormModal({ project, onSave, onClose }: Props) {
  const isEdit = !!project;
  const [name, setName] = useState(project?.name ?? "");
  const [description, setDescription] = useState(project?.description ?? "");
  const [handle, setHandle] = useState(project?.handle ?? "");
  const [avatarKey, setAvatarKey] = useState(project?.avatar_key ?? "");
  const [saving, setSaving] = useState(false);
  const [characters, setCharacters] = useState<Character[]>([]);

  // Fetch characters for avatar selector
  useEffect(() => {
    axios
      .get<Character[]>(`${API_BASE}/characters`)
      .then((r) => {
        console.log("[ProjectFormModal] characters loaded:", r.data.length);
        setCharacters(r.data);
      })
      .catch((err) => console.error("[ProjectFormModal] failed to load characters:", err));
  }, []);

  const handleSubmit = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      await onSave({
        name: name.trim(),
        ...(description.trim() && { description: description.trim() }),
        ...(handle.trim() && { handle: handle.trim() }),
        avatar_key: avatarKey || undefined,
      });
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const charsWithImage = characters.filter((c) => c.preview_image_url);

  return (
    <Modal open onClose={onClose} size="sm">
      <Modal.Header>
        <h2 className="text-sm font-bold text-zinc-900">
          {isEdit ? "Edit Project" : "New Project"}
        </h2>
        <button onClick={onClose} className="text-zinc-400 hover:text-zinc-600 text-xs">x</button>
      </Modal.Header>

      <div className="space-y-3 px-5 py-4">
        <div>
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
            Name *
          </label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My Project"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none"
            autoFocus
          />
        </div>
        <div>
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
            Handle
          </label>
          <input
            value={handle}
            onChange={(e) => setHandle(e.target.value)}
            placeholder="@channel-handle"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
            Description
          </label>
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none"
          />
        </div>

        {/* Avatar: Character Selector */}
        <div>
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
            Channel Avatar
          </label>
          {charsWithImage.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {/* None option */}
              <button
                type="button"
                onClick={() => setAvatarKey("")}
                className={`flex h-12 w-12 items-center justify-center rounded-full border-2 text-[10px] font-bold transition ${
                  !avatarKey
                    ? "border-zinc-900 bg-zinc-100 text-zinc-600"
                    : "border-zinc-200 bg-zinc-50 text-zinc-400 hover:border-zinc-300"
                }`}
              >
                None
              </button>
              {charsWithImage.map((ch) => {
                const imgUrl = ch.preview_image_url!.startsWith("http")
                  ? ch.preview_image_url!
                  : `${API_BASE}${ch.preview_image_url}`;
                const isSelected = avatarKey === ch.preview_image_url;
                return (
                  <button
                    key={ch.id}
                    type="button"
                    onClick={() => setAvatarKey(ch.preview_image_url!)}
                    title={ch.name}
                    className={`h-12 w-12 shrink-0 overflow-hidden rounded-full border-2 transition ${
                      isSelected
                        ? "border-zinc-900 ring-2 ring-zinc-300"
                        : "border-zinc-200 hover:border-zinc-400"
                    }`}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={imgUrl} alt={ch.name} className="h-full w-full object-cover object-top" />
                  </button>
                );
              })}
            </div>
          ) : (
            <p className="text-[10px] text-zinc-400">No characters with preview images available</p>
          )}
        </div>
      </div>

      <Modal.Footer>
        <Button variant="ghost" size="sm" onClick={onClose}>Cancel</Button>
        <Button size="sm" loading={saving} disabled={!name.trim()} onClick={handleSubmit}>
          {isEdit ? "Save" : "Create"}
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
