"use client";

import { useParams, redirect } from "next/navigation";

export default function AdminCharacterDetailRedirect() {
  const { id } = useParams<{ id: string }>();
  redirect(`/library/characters/${id}`);
}
