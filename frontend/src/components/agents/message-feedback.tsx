"use client";

import { useState } from "react";
import { ThumbsDown, ThumbsUp } from "lucide-react";
import { motion } from "framer-motion";

import { apiBaseUrl } from "@/lib/env";
import { getOrgId } from "@/lib/org";
import { toast } from "@/lib/toast";

export function MessageFeedback({ interactionId }: { interactionId: string }) {
  const [rating, setRating] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleFeedback(newRating: number) {
    if (submitting || rating !== null) return;
    setSubmitting(true);
    setRating(newRating);

    try {
      const orgId = getOrgId() || "org_test";
      const res = await fetch(`${apiBaseUrl()}/v1/academy/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Org-Id": orgId },
        body: JSON.stringify({ interaction_id: interactionId, rating: newRating }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      toast.success("Feedback received. Thank you.");
    } catch {
      toast.error("Failed to submit feedback");
      setRating(null);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex items-center gap-2 mt-2 text-xs text-white/50">
      <span>Was this helpful?</span>

      <motion.button
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.92 }}
        onClick={() => void handleFeedback(1)}
        disabled={rating !== null}
        className={`p-1 rounded focus-ring disabled:opacity-50 disabled:cursor-not-allowed ${
          rating === 1 ? "text-green bg-green/20" : "text-white/40 hover:text-green hover:bg-green/10"
        }`}
        aria-label="Thumbs up"
      >
        <ThumbsUp className="w-4 h-4" />
      </motion.button>

      <motion.button
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.92 }}
        onClick={() => void handleFeedback(-1)}
        disabled={rating !== null}
        className={`p-1 rounded focus-ring disabled:opacity-50 disabled:cursor-not-allowed ${
          rating === -1 ? "text-red bg-red/20" : "text-white/40 hover:text-red hover:bg-red/10"
        }`}
        aria-label="Thumbs down"
      >
        <ThumbsDown className="w-4 h-4" />
      </motion.button>
    </div>
  );
}

