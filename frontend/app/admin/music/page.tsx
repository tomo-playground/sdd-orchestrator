import { redirect } from "next/navigation";

export default function AdminMusicRedirect() {
  redirect("/library/music");
}
