/**
 * FeedbackWidget.tsx — Phase 0
 *
 * Thumbs up/down on a single chat answer. Standalone component — not
 * imported by ChatPage.tsx yet (see backend/ml/README.md for why, and the
 * one-line usage below for how to wire it in when ready).
 *
 * Usage (inside the assistant message bubble in ChatPage.tsx):
 *   <FeedbackWidget query={userQuery} answer={msg.content} source={msg.source} />
 */

import { useState } from "react";
import { ThumbsUp, ThumbsDown, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { logChatFeedback } from "@/services/mlFeedback";

interface FeedbackWidgetProps {
    query: string;
    answer: string;
    source?: string;
    language?: string;
    className?: string;
}

export function FeedbackWidget({ query, answer, source, language, className }: FeedbackWidgetProps) {
    const [rated, setRated] = useState<"helpful" | "not_helpful" | null>(null);
    const [submitting, setSubmitting] = useState(false);

    const rate = async (helpful: boolean) => {
        if (rated || submitting) return;
        setSubmitting(true);
        const ok = await logChatFeedback({ query, answerSnippet: answer, helpful, source, language });
        setSubmitting(false);
        if (ok) setRated(helpful ? "helpful" : "not_helpful");
    };

    if (rated) {
        return (
            <div className={cn("flex items-center gap-1.5 text-xs text-muted-foreground", className)}>
                <Check className="h-3 w-3 text-emerald-500" /> Thanks for the feedback
            </div>
        );
    }

    return (
        <div className={cn("flex items-center gap-1", className)}>
            <span className="text-xs text-muted-foreground mr-1">Was this helpful?</span>
            <button
                onClick={() => rate(true)}
                disabled={submitting}
                aria-label="Helpful"
                className="p-1 rounded-md hover:bg-muted/60 text-muted-foreground hover:text-emerald-500 transition-colors disabled:opacity-50"
            >
                <ThumbsUp className="h-3.5 w-3.5" />
            </button>
            <button
                onClick={() => rate(false)}
                disabled={submitting}
                aria-label="Not helpful"
                className="p-1 rounded-md hover:bg-muted/60 text-muted-foreground hover:text-red-500 transition-colors disabled:opacity-50"
            >
                <ThumbsDown className="h-3.5 w-3.5" />
            </button>
        </div>
    );
}
