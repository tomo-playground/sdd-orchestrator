import { redirect } from "next/navigation";

export default function AdminPromptsRedirect() {
  redirect("/library/prompts");
}
