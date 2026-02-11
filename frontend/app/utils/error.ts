import axios from "axios";

export function getErrorMsg(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) return error.response?.data?.detail ?? error.message;
  if (error instanceof Error) return error.message;
  return fallback;
}
