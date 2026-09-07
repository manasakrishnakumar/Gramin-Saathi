/**
 * SchemeFeedback.tsx — Phase 0
 *
 * Logs recommendation-card interactions (viewed / dismissed) that the
 * existing RecommendPage.tsx UI doesn't currently report anywhere. This
 * is the signal train_ranker_from_events.py needs. Standalone — not
 * imported by RecommendPage.tsx yet (see backend/ml/README.md).
 *
 * Note: the existing "Eligibility" and "Apply" buttons on SchemeCard
 * already exist in RecommendPage.tsx — this component doesn't replace
 * them, it's meant to sit alongside so those clicks can ALSO call
 * logRecommendationAction("clicked_apply" / "checked_eligibility") when
 * you wire it in, in addition to the small "not relevant" affordance this
 * component adds on its own.
 *
 * Usage (inside SchemeCard in RecommendPage.tsx):
 *   <SchemeFeedback
 *     schemeId={scheme.scheme_id}
 *     profile={profilePayload}
 *     ruleScorePct={scheme.score_pct}
 *     matchedCount={scheme.matched_criteria.length}
 *     missedCount={scheme.missed_criteria.length}
 *     isDisqualified={scheme.is_disqualified}
 *   />
 */

import { useEffect, useRef, useState } from "react";
import { X, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { logRecommendationAction, RecommendationAction } from "@/services/mlFeedback";

interface SchemeFeedbackProps {
    schemeId: string;
    profile: object;
    ruleScorePct: number;
    matchedCount: number;
    missedCount: number;
    isDisqualified?: boolean;
    className?: string;
}

export function SchemeFeedback({
    schemeId, profile, ruleScorePct, matchedCount, missedCount, isDisqualified, className,
}: SchemeFeedbackProps) {
    const [dismissed, setDismissed] = useState(false);
    const loggedViewRef = useRef(false);

    const log = (action: RecommendationAction) =>
        logRecommendationAction({
            schemeId, action, profile,
            ruleScorePct, matchedCount, missedCount, isDisqualified,
        });

    // Log a "viewed" event once per mount — this card was shown to the user.
    useEffect(() => {
        if (loggedViewRef.current) return;
        loggedViewRef.current = true;
        log("viewed");
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [schemeId]);

    const dismiss = async () => {
        if (dismissed) return;
        setDismissed(true);
        await log("dismissed");
    };

    if (dismissed) {
        return (
            <div className={cn("flex items-center gap-1.5 text-xs text-muted-foreground", className)}>
                <Check className="h-3 w-3" /> Won't show this again as a top match
            </div>
        );
    }

    return (
        <button
            onClick={dismiss}
            className={cn(
                "flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors",
                className,
            )}
            title="Not relevant to me"
        >
            <X className="h-3 w-3" /> Not relevant
        </button>
    );
}

/** Call this from the existing "Apply" / "Eligibility" button handlers when wiring in. */
export function logSchemeEngagement(params: {
    schemeId: string;
    action: "clicked_apply" | "checked_eligibility";
    profile: object;
    ruleScorePct: number;
    matchedCount: number;
    missedCount: number;
    isDisqualified?: boolean;
}) {
    return logRecommendationAction({
        schemeId: params.schemeId,
        action: params.action,
        profile: params.profile,
        ruleScorePct: params.ruleScorePct,
        matchedCount: params.matchedCount,
        missedCount: params.missedCount,
        isDisqualified: params.isDisqualified,
    });
}
