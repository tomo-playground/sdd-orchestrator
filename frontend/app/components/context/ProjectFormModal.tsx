"use client";

import { useState } from "react";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import type { ProjectItem } from "../../types";

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

  const handleSubmit = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      await onSave({
        name: name.trim(),
        ...(description.trim() && { description: description.trim() }),
        ...(handle.trim() && { handle: handle.trim() }),
        ...(avatarKey.trim() && { avatar_key: avatarKey.trim() }),
      });
      onClose();
    } finally {
      setSaving(false);
    }
  };

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
            Description
          </label>
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
            Handle
          </label>
          <input
            value={handle}
            onChange={(e) => setHandle(e.target.value)}
            placeholder="@my-project"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
            Avatar Key (IP-Adapter Reference)
          </label>
          <input
            value={avatarKey}
            onChange={(e) => setAvatarKey(e.target.value)}
            placeholder="character_key for avatar"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none"
          />
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
