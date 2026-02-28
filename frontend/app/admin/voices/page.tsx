import { redirect } from "next/navigation";

export default function AdminVoicesRedirect() {
  redirect("/library/voices");
}
