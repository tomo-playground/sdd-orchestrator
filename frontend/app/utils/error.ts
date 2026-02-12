import axios from "axios";

export function getErrorMsg(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    // Structured error: { message, code, ... }
    if (typeof detail === "object" && detail?.message) return detail.message;
    if (typeof detail === "string") return detail;
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return fallback;
}
