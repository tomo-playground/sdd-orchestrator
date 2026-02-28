import { redirect } from "next/navigation";

export default function AdminNewCharacterRedirect() {
  redirect("/library/characters/new");
}
