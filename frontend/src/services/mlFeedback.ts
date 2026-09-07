/**
 * mlFeedback.ts — Phase 0 client
 *
 * Talks to the new `/api/v1/ml/feedback/*` endpoints (see
 * backend/ml/README.md). These endpoints only exist once `ml_router` is
 * mounted in `app/api/v1/api.py` — until then, calls here will 404, which
 * every function below fails silently on (never breaks the calling UI).
 *
 * Nothing in the existing app imports this file yet — see
 * components/ml/FeedbackWidget.tsx and SchemeFeedback.tsx for the widgets
 * that use it, and backend/ml/README.md for how to wire both in.
 */

export type RecommendationAction = "viewed" | "clicked_apply" | "checked_eligibility" | "dismissed";

export async function logChatFeedback(params: {
    query: string;
    answerSnippet: string;
    helpful: boolean;
    source?: string;
    language?: string;
}): Promise<boolean> {
    try {
        const res = await fetch("/api/v1/ml/feedback/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                query: params.query,
                answer_snippet: params.answerSnippet.slice(0, 500),
                helpful: params.helpful,
                source: params.source ?? "",
                language: params.language ?? "English",
            }),
        });
        return res.ok;
    } catch {
        return false; // feedback logging must never break the chat UI
    }
}

export async function logRecommendationAction(params: {
    schemeId: string;
    action: RecommendationAction;
    profile: object;
    ruleScorePct: number;
    matchedCount: number;
    missedCount: number;
    isDisqualified?: boolean;
}): Promise<boolean> {
    try {
        const res = await fetch("/api/v1/ml/feedback/recommendation", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                scheme_id: params.schemeId,
                action: params.action,
                profile: params.profile,
                rule_score_pct: params.ruleScorePct,
                matched_count: params.matchedCount,
                missed_count: params.missedCount,
                is_disqualified: params.isDisqualified ?? false,
            }),
        });
        return res.ok;
    } catch {
        return false;
    }
}
