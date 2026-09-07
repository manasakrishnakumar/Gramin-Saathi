import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X, CheckCircle2, XCircle, AlertTriangle, Loader2, ExternalLink,
  FileText, ListChecks, Lightbulb, ChevronDown, ChevronUp, ShieldCheck, ShieldX, ShieldAlert,
  FlaskConical,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ─── Types ───────────────────────────────────────────────────────────────────

interface CriterionEligibilityDetail {
  label: string;
  field: string;
  matched: boolean;
  weight: number;
  is_hard: boolean;
  actual_value: unknown;
  required_value: unknown;
  fix_suggestion: string;
  documents_for_criterion: string[];
}

interface EligibilityResponse {
  scheme_id: string;
  scheme_name: string;
  ministry: string;
  description: string;
  apply_url: string;
  verdict: string;
  eligibility_pct: number;
  confidence: string;
  is_eligible: boolean;
  blocking_criteria: CriterionEligibilityDetail[];
  soft_gaps: CriterionEligibilityDetail[];
  passed_criteria: CriterionEligibilityDetail[];
  documents_required: string[];
  next_steps: string[];
  what_if_suggestions: string[];
}

// ─── Helper components ───────────────────────────────────────────────────────

function VerdictBadge({ verdict }: { verdict: string }) {
  const config: Record<string, { icon: typeof ShieldCheck; color: string; bg: string; border: string }> = {
    "Fully Eligible":         { icon: ShieldCheck, color: "text-emerald-400", bg: "bg-emerald-500/15", border: "border-emerald-500/30" },
    "Conditionally Eligible": { icon: ShieldAlert, color: "text-blue-400",    bg: "bg-blue-500/15",    border: "border-blue-500/30"    },
    "Partially Eligible":     { icon: ShieldAlert, color: "text-amber-400",   bg: "bg-amber-500/15",   border: "border-amber-500/30"   },
    "Not Eligible":           { icon: ShieldX,     color: "text-red-400",     bg: "bg-red-500/15",     border: "border-red-500/30"     },
  };
  const cfg = config[verdict] ?? config["Not Eligible"];
  const Icon = cfg.icon;
  return (
    <span className={cn("inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-sm font-semibold", cfg.color, cfg.bg, cfg.border)}>
      <Icon className="h-4 w-4" /> {verdict}
    </span>
  );
}

function EligibilityBar({ pct }: { pct: number }) {
  const color = pct >= 80 ? "bg-emerald-500" : pct >= 60 ? "bg-blue-500" : pct >= 40 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>Eligibility Score</span>
        <span className="font-semibold text-foreground">{pct}%</span>
      </div>
      <div className="h-2.5 w-full rounded-full bg-muted/40 overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className={cn("h-full rounded-full", color)}
        />
      </div>
    </div>
  );
}

function Section({
  title, icon: Icon, children, defaultOpen = true,
}: { title: string; icon: React.ElementType; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-border rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 bg-muted/30 hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <Icon className="h-4 w-4 text-primary" />
          {title}
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
      </button>
      {open && <div className="px-4 py-3">{children}</div>}
    </div>
  );
}

// ─── Main Modal ───────────────────────────────────────────────────────────────

interface EligibilityModalProps {
  schemeId: string;
  schemeName: string;
  profilePayload: object;
  onClose: () => void;
}

interface DemoOutcomePrediction {
  synthetic_approval_likelihood: number | null;
  disclaimer: string;
  error?: string;
}

export function EligibilityModal({ schemeId, schemeName, profilePayload, onClose }: EligibilityModalProps) {
  const [data, setData] = useState<EligibilityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [demoPrediction, setDemoPrediction] = useState<DemoOutcomePrediction | null>(null);

  // Fetch on mount or when schemeId / profilePayload changes
  useEffect(() => {
    const fetch_ = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch("/api/v1/eligibility/check", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...profilePayload, scheme_id: schemeId }),
        });
        if (!res.ok) {
          let errorMsg = `Error ${res.status}`;
          try {
            const errData = await res.json();
            if (errData.detail) {
              errorMsg = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
            }
          } catch {
            errorMsg = await res.text();
          }
          throw new Error(errorMsg);
        }
        const result: EligibilityResponse = await res.json();
        setData(result);

        // Phase 3 SYNTHETIC DEMO prediction — separate fetch, never blocks
        // or replaces the real (rule-based) eligibility result above. See
        // ml_outcome_predictor_service.py and ml/PHASE3_NOTES.md.
        try {
          const demoRes = await fetch("/api/v1/ml/outcomes/predict-demo", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              profile: profilePayload,
              scheme_id: schemeId,
              rule_score_pct: result.eligibility_pct,
              matched_count: result.passed_criteria.length,
              missed_count: result.blocking_criteria.length + result.soft_gaps.length,
            }),
          });
          if (demoRes.ok) setDemoPrediction(await demoRes.json());
        } catch {
          // Demo prediction is optional decoration — never surface this as a hard error
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };
    fetch_();
  }, [schemeId, profilePayload]);

  return (
    <AnimatePresence>
      {/* Backdrop */}
      <motion.div
        key="backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
      />

      {/* Panel */}
      <motion.div
        key="panel"
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 40 }}
        transition={{ type: "spring", damping: 28, stiffness: 280 }}
        className="fixed inset-x-0 bottom-0 z-50 md:inset-auto md:top-1/2 md:left-1/2 md:-translate-x-1/2 md:-translate-y-1/2 md:w-[720px] md:max-h-[88vh] max-h-[90vh] overflow-y-auto bg-background border border-border rounded-t-3xl md:rounded-2xl shadow-2xl"
      >
        {/* Header */}
        <div className="sticky top-0 bg-background/95 backdrop-blur border-b border-border px-5 py-4 flex items-start justify-between z-10">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-0.5">Eligibility Check</p>
            <h2 className="text-lg font-bold text-foreground leading-tight">{schemeName}</h2>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-5 space-y-5">
          {/* Loading */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm">Evaluating eligibility rules…</p>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" /> {error}
            </div>
          )}

          {/* Results */}
          {data && !loading && (
            <>
              {/* Verdict + Score */}
              <div className="space-y-4 p-4 rounded-2xl bg-muted/20 border border-border">
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <VerdictBadge verdict={data.verdict} />
                  <span className="text-xs text-muted-foreground">
                    Confidence: <span className="font-semibold text-foreground">{data.confidence}</span>
                  </span>
                </div>
                <EligibilityBar pct={data.eligibility_pct} />
                <p className="text-sm text-muted-foreground leading-relaxed">{data.description}</p>
              </div>

              {/* Blocking (hard failures) */}
              {data.blocking_criteria.length > 0 && (
                <Section title={`Disqualifying Criteria (${data.blocking_criteria.length})`} icon={ShieldX} defaultOpen={true}>
                  <div className="space-y-3">
                    {data.blocking_criteria.map((c, i) => (
                      <div key={i} className="rounded-xl border border-red-500/20 bg-red-500/5 p-3 space-y-1.5">
                        <div className="flex items-center gap-2">
                          <XCircle className="h-4 w-4 text-red-400 shrink-0" />
                          <span className="text-sm font-medium text-red-300">{c.label}</span>
                          <span className="ml-auto text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full border border-red-500/20 font-bold">HARD</span>
                        </div>
                        <p className="text-xs text-muted-foreground pl-6 leading-relaxed">
                          <span className="text-amber-400 font-medium">Fix: </span>{c.fix_suggestion}
                        </p>
                        {c.documents_for_criterion.length > 0 && (
                          <div className="pl-6 flex flex-wrap gap-1.5 mt-1">
                            {c.documents_for_criterion.map((d, j) => (
                              <span key={j} className="text-xs bg-muted/50 text-muted-foreground border border-border px-2 py-0.5 rounded-full">
                                📄 {d}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </Section>
              )}

              {/* Soft gaps */}
              {data.soft_gaps.length > 0 && (
                <Section title={`Soft Gaps — Won't Disqualify (${data.soft_gaps.length})`} icon={AlertTriangle} defaultOpen={true}>
                  <div className="space-y-3">
                    {data.soft_gaps.map((c, i) => (
                      <div key={i} className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 space-y-1.5">
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
                          <span className="text-sm font-medium text-amber-300">{c.label}</span>
                          <span className="ml-auto text-xs text-muted-foreground">weight: {c.weight}</span>
                        </div>
                        <p className="text-xs text-muted-foreground pl-6 leading-relaxed">
                          <span className="text-primary font-medium">Improve: </span>{c.fix_suggestion}
                        </p>
                      </div>
                    ))}
                  </div>
                </Section>
              )}

              {/* Passed */}
              {data.passed_criteria.length > 0 && (
                <Section title={`Criteria You Meet (${data.passed_criteria.length})`} icon={CheckCircle2} defaultOpen={data.blocking_criteria.length === 0}>
                  <div className="flex flex-wrap gap-2">
                    {data.passed_criteria.map((c, i) => (
                      <span key={i} className="flex items-center gap-1.5 text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">
                        <CheckCircle2 className="h-3 w-3" />
                        {c.label}
                        {c.is_hard && <span className="font-bold text-emerald-300 ml-0.5">✓ Hard</span>}
                      </span>
                    ))}
                  </div>
                </Section>
              )}

              {/* Documents */}
              <Section title="Documents Required" icon={FileText} defaultOpen={true}>
                <ul className="space-y-2">
                  {data.documents_required.map((doc, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-foreground/80">
                      <span className="shrink-0 mt-0.5 text-primary">📄</span> {doc}
                    </li>
                  ))}
                </ul>
              </Section>

              {/* Next Steps */}
              <Section title="Next Steps" icon={ListChecks} defaultOpen={true}>
                <ol className="space-y-2">
                  {data.next_steps.map((step, i) => (
                    <li key={i} className="text-sm text-foreground/80 leading-relaxed">{step}</li>
                  ))}
                </ol>
              </Section>

              {/* What-if */}
              {data.what_if_suggestions.some(s => s !== "All criteria are met. No changes needed.") && (
                <Section title="What-If Gap Analysis" icon={Lightbulb} defaultOpen={false}>
                  <div className="space-y-2">
                    {data.what_if_suggestions.map((s, i) => (
                      <p key={i} className="text-sm text-foreground/70 leading-relaxed border-l-2 border-primary/30 pl-3">{s}</p>
                    ))}
                  </div>
                </Section>
              )}

              {/* Phase 3 SYNTHETIC DEMO — visually distinct (dashed border, amber)
                  on purpose, so it can never be mistaken for the real
                  eligibility verdict above. See ml/PHASE3_NOTES.md. */}
              {demoPrediction && demoPrediction.synthetic_approval_likelihood !== null && (
                <div className="rounded-xl border-2 border-dashed border-amber-500/40 bg-amber-500/5 p-4 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-amber-500 uppercase tracking-wide">
                    <FlaskConical className="h-3.5 w-3.5" /> Synthetic Demo — Not Real Data
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-foreground/80">Simulated approval likelihood</span>
                    <span className="text-lg font-bold text-amber-500">
                      {Math.round(demoPrediction.synthetic_approval_likelihood * 100)}%
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">{demoPrediction.disclaimer}</p>
                </div>
              )}

              {/* Apply CTA */}
              <div className="pt-2">
                <a href={data.apply_url} target="_blank" rel="noopener noreferrer" className="block">
                  <Button className="w-full gap-2" disabled={!data.is_eligible} variant={data.is_eligible ? "default" : "outline"}>
                    {data.is_eligible ? (
                      <><ShieldCheck className="h-4 w-4" /> Apply Now on Official Portal <ExternalLink className="h-3.5 w-3.5 ml-1" /></>
                    ) : (
                      <><ShieldX className="h-4 w-4" /> Not Yet Eligible — Resolve Issues First</>
                    )}
                  </Button>
                </a>
              </div>
            </>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
