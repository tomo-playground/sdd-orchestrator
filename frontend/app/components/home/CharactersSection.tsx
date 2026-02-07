"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import { useStudioStore } from "../../store/useStudioStore";
import { useCharacters } from "../../hooks/useCharacters";
import CharacterEditModal from "../shared/CharacterEditModal";
import Button from "../ui/Button";
import ImagePreviewModal from "../ui/ImagePreviewModal";
import { LABEL_CLASSES } from "../ui/variants";
import type { Character, Tag, LoRA } from "../../types";

export default function CharactersSection() {
  const showToast = useStudioStore((s) => s.showToast);
  const { characters, reload: refreshCharacters } = useCharacters();
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [allLoras, setAllLoras] = useState<LoRA[]>([]);
  const [editingCharacter, setEditingCharacter] = useState<Character | undefined>(undefined);
  const [showModal, setShowModal] = useState(false);
  const [imagePreview, setImagePreview] = useState<string | null>(null);

  // Fetch tags & loras for character modal
  useEffect(() => {
    Promise.all([
      axios.get(`${API_BASE}/tags`).then((r) => setAllTags(r.data)),
      axios.get(`${API_BASE}/loras`).then((r) => setAllLoras(r.data)),
    ]).catch(() => {});
  }, []);

  const handleSave = async (data: Partial<Character>, id?: number) => {
    if (id) {
      await axios.put(`${API_BASE}/characters/${id}`, data);
    } else {
      await axios.post(`${API_BASE}/characters`, data);
    }
    refreshCharacters();
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this character?")) return;
    try {
      await axios.delete(`${API_BASE}/characters/${id}`);
      refreshCharacters();
      showToast("Character deleted", "success");
    } catch {
      showToast("Failed to delete character", "error");
    }
  };

  const openCreate = () => {
    setEditingCharacter(undefined);
    setShowModal(true);
  };
  const openEdit = (ch: Character) => {
    setEditingCharacter(ch);
    setShowModal(true);
  };

  return (
    <>
      <section>
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className={LABEL_CLASSES}>
              Characters{characters.length > 0 ? ` (${characters.length})` : ""}
            </h2>
            <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[9px] font-medium text-zinc-400">
              Global
            </span>
          </div>
          {characters.length > 0 && (
            <Button size="sm" onClick={openCreate} className="shrink-0 rounded-full">
              + New Character
            </Button>
          )}
        </div>

        {characters.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <svg
              className="h-12 w-12 text-zinc-200"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"
              />
            </svg>
            <div>
              <p className="text-sm font-medium text-zinc-500">No characters yet</p>
              <p className="mt-1 text-xs text-zinc-400">
                Characters maintain visual consistency across scenes
              </p>
            </div>
            <Button size="md" onClick={openCreate}>
              + New Character
            </Button>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {characters.map((ch) => (
              <div
                key={ch.id}
                className="group relative flex items-start gap-3 rounded-2xl border border-zinc-200/60 bg-white p-4 shadow-sm transition hover:shadow-md"
              >
                {ch.preview_image_url ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={
                      ch.preview_image_url.startsWith("http")
                        ? ch.preview_image_url
                        : `${API_BASE}${ch.preview_image_url}`
                    }
                    alt={ch.name}
                    onClick={() => openEdit(ch)}
                    className="h-14 w-14 cursor-pointer rounded-xl bg-zinc-100 object-cover object-top transition-all hover:ring-2 hover:ring-zinc-300"
                  />
                ) : (
                  <div
                    onClick={() => openEdit(ch)}
                    className="flex h-14 w-14 cursor-pointer items-center justify-center rounded-xl bg-zinc-100 text-lg font-bold text-zinc-400 transition-all hover:ring-2 hover:ring-zinc-300"
                  >
                    {ch.name.charAt(0)}
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <h3 className="text-sm font-semibold text-zinc-900">{ch.name}</h3>
                  <p className="line-clamp-1 text-xs text-zinc-500">
                    {ch.description || ch.gender}
                  </p>
                  <div className="mt-1 flex gap-1">
                    <button
                      onClick={() => openEdit(ch)}
                      className="text-[10px] text-zinc-500 underline hover:text-zinc-700"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(ch.id)}
                      className="text-[10px] text-zinc-400 underline hover:text-red-500"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {showModal && (
        <CharacterEditModal
          character={editingCharacter}
          allTags={allTags}
          allLoras={allLoras}
          onClose={() => setShowModal(false)}
          onSave={handleSave}
        />
      )}

      {imagePreview && (
        <ImagePreviewModal src={imagePreview} onClose={() => setImagePreview(null)} />
      )}
    </>
  );
}
