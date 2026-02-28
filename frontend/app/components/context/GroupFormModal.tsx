"use client";

import { useState } from "react";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import { FORM_INPUT_COMPACT_CLASSES, FORM_LABEL_COMPACT_CLASSES } from "../ui/variants";

type Props = {
  projectId: number;
  onSave: (data: Record<string, unknown>) => Promise<void>;
  onClose: () => void;
};

export default function GroupFormModal({ projectId, onSave, onClose }: Props) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      await onSave({
        project_id: projectId,
        name: name.trim(),
        ...(description.trim() && { description: description.trim() }),
      });
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const inputCls = FORM_INPUT_COMPACT_CLASSES;
  const labelCls = FORM_LABEL_COMPACT_CLASSES;

  return (
    <Modal open onClose={onClose} size="md">
      <Modal.Header>
        <h2 className="text-sm font-bold text-zinc-900">새 시리즈</h2>
        <button
          onClick={onClose}
          aria-label="Close dialog"
          className="text-xs text-zinc-400 hover:text-zinc-600"
        >
          x
        </button>
      </Modal.Header>

      <div className="space-y-3 px-5 py-4">
        <div>
          <label htmlFor="group-form-name" className={labelCls}>
            Name *
          </label>
          <input
            id="group-form-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="시리즈 이름"
            className={inputCls}
            autoFocus
          />
        </div>
        <div>
          <label htmlFor="group-form-desc" className={labelCls}>
            Description
          </label>
          <input
            id="group-form-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description"
            className={inputCls}
          />
        </div>
      </div>

      <Modal.Footer>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Cancel
        </Button>
        <Button size="sm" loading={saving} disabled={!name.trim()} onClick={handleSubmit}>
          Create
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
