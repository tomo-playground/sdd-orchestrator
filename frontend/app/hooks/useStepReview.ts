import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { API_BASE } from "../constants";
import type { StepReview, ReviewMessage } from "../types/creative";

/** Hook for managing interactive step review state. */
export function useStepReview(sessionId: number, status: string) {
  const [review, setReview] = useState<StepReview | null>(null);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReview = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get<StepReview>(
        `${API_BASE}/lab/creative/sessions/${sessionId}/review`
      );
      setReview(res.data);
      setError(null);
    } catch (err) {
      setReview(null);
      if (axios.isAxiosError(err) && err.response?.status === 404) {
        setError("Review data not available yet. The pipeline may still be preparing.");
      } else {
        setError(err instanceof Error ? err.message : "Failed to load review");
      }
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  // Auto-fetch when entering step_review status
  useEffect(() => {
    if (status === "step_review") {
      fetchReview();
    } else {
      setReview(null);
    }
  }, [status, fetchReview]);

  const handleReviewMessage = useCallback(
    async (message: string) => {
      if (!message.trim()) return;
      setSending(true);
      setError(null);
      try {
        const res = await axios.post<StepReview>(
          `${API_BASE}/lab/creative/sessions/${sessionId}/review/message`,
          { message }
        );
        setReview(res.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to send message");
      } finally {
        setSending(false);
      }
    },
    [sessionId]
  );

  const handleReviewAction = useCallback(
    async (action: "approve" | "revise", feedback?: string) => {
      setSending(true);
      setError(null);
      try {
        await axios.post(`${API_BASE}/lab/creative/sessions/${sessionId}/review/action`, {
          action,
          feedback,
        });
        setReview(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to perform action");
      } finally {
        setSending(false);
      }
    },
    [sessionId]
  );

  const messages: ReviewMessage[] = review?.messages ?? [];

  return {
    review,
    loading,
    sending,
    error,
    messages,
    fetchReview,
    handleReviewMessage,
    handleReviewAction,
  };
}
