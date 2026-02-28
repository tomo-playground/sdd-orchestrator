"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import { API_BASE } from "../../constants";
import type { Character, ProjectItem } from "../../types";
import { resolveImageUrl } from "../../utils/url";

type Props = {
  project?: ProjectItem;
  onSave: (data: {
    name: string;
    description?: string;
    handle?: string;
    avatar_media_asset_id?: number | null;
  }) => Promise<void>;
  onClose: () => void;
};

export default function ProjectFormModal({ project, onSave, onClose }: Props) {
  const isEdit = !!project;
  const [name, setName] = useState(project?.name ?? "");
  const [description, setDescription] = useState(project?.description ?? "");
  const [handle, setHandle] = useState(project?.handle ?? "");
  const [avatarAssetId, setAvatarAssetId] = useState<number | null>(
    project?.avatar_media_asset_id ?? null
  );
  const [saving, setSaving] = useState(false);
  const [characters, setCharacters] = useState<Character[]>([]);

  // Fetch characters for avatar selector
  useEffect(() => {
    axios
      .get<{ items: Character[] }>(`${API_BASE}/characters`)
      .then((r) => {
        const items = r.data.items ?? [];
        setCharacters(items);
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
        avatar_media_asset_id: avatarAssetId,
      });
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const charsWithImage = characters.filter((c) => c.preview_image_asset_id);

  return (
    <Modal open onClose={onClose} size="sm">
      <Modal.Header>
        <h2 className="text-sm font-bold text-zinc-900">
          {isEdit ? "채널 편집" : "새 채널"}
        </h2>
        <button onClick={onClose} className="text-xs text-zinc-400 hover:text-zinc-600">
          x
        </button>
      </Modal.Header>

      <div className="space-y-3 px-5 py-4">
        <div>
          <label
            htmlFor="project-form-name"
            className="mb-1 block text-[12px] font-semibold tracking-wider text-zinc-400 uppercase"
          >
            Name *
          </label>
          <input
            id="project-form-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="내 채널"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none"
            autoFocus
          />
        </div>
        <div>
          <label
            htmlFor="project-form-handle"
            className="mb-1 block text-[12px] font-semibold tracking-wider text-zinc-400 uppercase"
          >
            Handle
          </label>
          <input
            id="project-form-handle"
            value={handle}
            onChange={(e) => setHandle(e.target.value)}
            placeholder="@channel-handle"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none"
          />
        </div>
        <div>
          <label
            htmlFor="project-form-desc"
            className="mb-1 block text-[12px] font-semibold tracking-wider text-zinc-400 uppercase"
          >
            Description
          </label>
          <input
            id="project-form-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none"
          />
        </div>

        {/* Avatar: Character Selector */}
        <div>
          <label className="mb-1 block text-[12px] font-semibold tracking-wider text-zinc-400 uppercase">
            Channel Avatar
          </label>
          {charsWithImage.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {/* None option */}
              <button
                type="button"
                onClick={() => setAvatarAssetId(null)}
                className={`flex h-12 w-12 items-center justify-center rounded-full border-2 text-[12px] font-bold transition ${avatarAssetId === null
                    ? "border-zinc-900 bg-zinc-100 text-zinc-600"
                    : "border-zinc-200 bg-zinc-50 text-zinc-400 hover:border-zinc-300"
                  }`}
              >
                None
              </button>
              {charsWithImage.map((ch) => {
                const imgUrl = resolveImageUrl(ch.preview_image_url);
                const isSelected = avatarAssetId === ch.preview_image_asset_id;
                return (
                  <button
                    key={ch.id}
                    type="button"
                    onClick={() => setAvatarAssetId(ch.preview_image_asset_id!)}
                    title={ch.name}
                    className={`h-12 w-12 shrink-0 overflow-hidden rounded-full border-2 transition ${isSelected
                        ? "border-zinc-900 ring-2 ring-zinc-300"
                        : "border-zinc-200 hover:border-zinc-400"
                      }`}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={imgUrl!}
                      alt={ch.name}
                      className="h-full w-full object-cover object-top"
                    />
                  </button>
                );
              })}
            </div>
          ) : (
            <p className="text-[12px] text-zinc-400">No characters with preview images available</p>
          )}
        </div>
      </div>

      <Modal.Footer>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Cancel
        </Button>
        <Button size="sm" loading={saving} disabled={!name.trim()} onClick={handleSubmit}>
          {isEdit ? "Save" : "Create"}
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
