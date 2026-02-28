import { redirect } from "next/navigation";

export default function AdminCharactersRedirect() {
  redirect("/library/characters");
}
