import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, XCircle, ChevronRight, ChevronLeft, Loader2, ExternalLink, Star, AlertCircle, User, IndianRupee, Briefcase, MapPin, Award, ClipboardCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { EligibilityModal } from "@/components/EligibilityModal";

// ─── Types ───────────────────────────────────────────────────────────────────

interface CriterionDetail {
  label: string;
  field: string;
  matched: boolean;
  weight: number;
  is_hard: boolean;
  actual_value: unknown;
  required_value: unknown;
}

interface SchemeRecommendation {
  scheme_id: string;
  name: string;
  ministry: string;
  description: string;
  apply_url: string;
  score_pct: number;
  is_disqualified: boolean;
  matched_criteria: CriterionDetail[];
  missed_criteria: CriterionDetail[];
  match_label: string;
  ml_engagement_score: number | null;
}

interface RecommendationResponse {
  profile_summary: {
    age: number;
    income_band: string;
    occupation: string;
    gender: string;
    category: string;
    state: string;
    land_owned_acres: number;
    is_bpl: boolean;
    is_disabled: boolean;
  };
  total_eligible: number;
  recommendations: SchemeRecommendation[];
  ranking_method: string; // "rule_engine" | "ml_reranked"
}

// ─── Constants ────────────────────────────────────────────────────────────────

const OCCUPATIONS = [
  { value: "farmer", label: "Farmer / Cultivator" },
  { value: "student", label: "Student" },
  { value: "self_employed", label: "Self-Employed / Business" },
  { value: "salaried", label: "Salaried Employee" },
  { value: "daily_wage", label: "Daily Wage Worker" },
  { value: "unemployed", label: "Unemployed" },
  { value: "other", label: "Other" },
];

const GENDERS = [
  { value: "male", label: "Male" },
  { value: "female", label: "Female" },
  { value: "transgender", label: "Transgender" },
  { value: "other", label: "Other" },
];

const CATEGORIES = [
  { value: "general", label: "General" },
  { value: "obc", label: "OBC" },
  { value: "sc", label: "SC" },
  { value: "st", label: "ST" },
];

const STATES = [
  "", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
  "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
  "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
  "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
  "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
];

const MATCH_COLORS: Record<string, string> = {
  "Excellent Match": "from-emerald-500/20 to-green-500/10 border-emerald-500/40",
  "Good Match": "from-blue-500/20 to-cyan-500/10 border-blue-500/40",
  "Partial Match": "from-amber-500/20 to-yellow-500/10 border-amber-500/40",
  "Low Match": "from-orange-500/20 to-red-500/10 border-orange-500/40",
  "Not Eligible": "from-red-500/20 to-rose-500/10 border-red-500/40",
};

const MATCH_BADGE: Record<string, string> = {
  "Excellent Match": "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  "Good Match": "bg-blue-500/20 text-blue-400 border-blue-500/30",
  "Partial Match": "bg-amber-500/20 text-amber-400 border-amber-500/30",
  "Low Match": "bg-orange-500/20 text-orange-400 border-orange-500/30",
  "Not Eligible": "bg-red-500/20 text-red-400 border-red-500/30",
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function SelectCard({
  value, label, selected, onClick,
}: { value: string; label: string; selected: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "px-4 py-2.5 rounded-xl border text-sm font-medium transition-all duration-200",
        selected
          ? "bg-primary border-primary text-primary-foreground shadow-lg shadow-primary/25 scale-105"
          : "bg-muted/40 border-border hover:border-primary/50 hover:bg-muted/70 text-foreground/80"
      )}
    >
      {label}
    </button>
  );
}

function ScoreRing({ pct, size = 80 }: { pct: number; size?: number }) {
  const r = (size - 10) / 2;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  const color = pct >= 80 ? "#10b981" : pct >= 60 ? "#3b82f6" : pct >= 40 ? "#f59e0b" : "#ef4444";

  return (
    <svg width={size} height={size} className="rotate-[-90deg]">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="currentColor"
        strokeWidth={8} className="text-muted/30" />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color}
        strokeWidth={8} strokeDasharray={`${dash} ${circ - dash}`}
        strokeLinecap="round" style={{ transition: "stroke-dasharray 0.8s ease" }} />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central"
        fill={color} fontSize={size * 0.22} fontWeight="bold"
        style={{ transform: "rotate(90deg)", transformOrigin: "center", transformBox: "fill-box" }}>
        {pct}%
      </text>
    </svg>
  );
}

function SchemeCard({ scheme, index, onCheckEligibility }: { scheme: SchemeRecommendation; index: number; onCheckEligibility: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const colorClass = MATCH_COLORS[scheme.match_label] ?? MATCH_COLORS["Low Match"];
  const badgeClass = MATCH_BADGE[scheme.match_label] ?? MATCH_BADGE["Low Match"];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.07 }}
      className={cn(
        "rounded-2xl border bg-gradient-to-br p-5 space-y-3",
        colorClass
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={cn("text-xs font-semibold px-2 py-0.5 rounded-full border", badgeClass)}>
              {scheme.match_label}
            </span>
            {scheme.is_disqualified && (
              <span className="text-xs text-red-400 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" /> Disqualified
              </span>
            )}
            {scheme.ml_engagement_score !== null && (
              <span
                className="text-[10px] font-semibold px-2 py-0.5 rounded-full border text-violet-400 bg-violet-500/10 border-violet-500/20 flex items-center gap-1"
                title="Predicted engagement from the trained ranker (ml/train_ranker_bootstrap.py) — reorders already-eligible schemes only, never affects eligibility"
              >
                <Star className="h-2.5 w-2.5" /> ML {Math.round(scheme.ml_engagement_score * 100)}%
              </span>
            )}
          </div>
          <h3 className="text-base font-bold mt-1.5 text-foreground leading-tight">{scheme.name}</h3>
          <p className="text-xs text-muted-foreground mt-0.5">{scheme.ministry}</p>
        </div>
        <ScoreRing pct={scheme.score_pct} size={64} />
      </div>

      <p className="text-sm text-foreground/70 leading-relaxed">{scheme.description}</p>

      {/* Criteria preview */}
      <div className="flex flex-wrap gap-1.5">
        {scheme.matched_criteria.map((c, i) => (
          <span key={i} className="flex items-center gap-1 text-xs bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-500/20">
            <CheckCircle2 className="h-3 w-3" /> {c.label}
          </span>
        ))}
        {scheme.missed_criteria.slice(0, expanded ? 100 : 2).map((c, i) => (
          <span key={i} className={cn(
            "flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border",
            c.is_hard
              ? "bg-red-500/10 text-red-400 border-red-500/20"
              : "bg-muted/40 text-muted-foreground border-border"
          )}>
            <XCircle className="h-3 w-3" /> {c.label}
            {c.is_hard && <span className="font-bold">*</span>}
          </span>
        ))}
      </div>

      {/* Footer actions */}
      <div className="flex items-center justify-between pt-1 flex-wrap gap-2">
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors underline-offset-2 hover:underline"
        >
          {expanded ? "Show less" : `Show all criteria (${scheme.matched_criteria.length + scheme.missed_criteria.length})`}
        </button>
        <div className="flex gap-2">
          <Button
            variant="outline" size="sm"
            className="h-7 text-xs gap-1 border-primary/40 hover:border-primary hover:bg-primary/5"
            onClick={onCheckEligibility}
          >
            <ClipboardCheck className="h-3 w-3" /> Eligibility
          </Button>
          <a href={scheme.apply_url} target="_blank" rel="noopener noreferrer">
            <Button variant="outline" size="sm" className="h-7 text-xs gap-1 border-border hover:border-primary/50">
              Apply <ExternalLink className="h-3 w-3" />
            </Button>
          </a>
        </div>
      </div>
    </motion.div>
  );
}

// ─── Steps ────────────────────────────────────────────────────────────────────

const STEPS = [
  { id: 0, label: "Personal", icon: User },
  { id: 1, label: "Financial", icon: IndianRupee },
  { id: 2, label: "Occupation", icon: Briefcase },
  { id: 3, label: "Category", icon: Award },
  { id: 4, label: "Location", icon: MapPin },
];

// ─── Main Component ───────────────────────────────────────────────────────────

export default function RecommendPage() {
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [eligibilityTarget, setEligibilityTarget] = useState<{ id: string; name: string } | null>(null);
  const [profilePayload, setProfilePayload] = useState<object>({});

  const [profile, setProfile] = useState({
    age: "",
    annual_income: "",
    occupation: "",
    gender: "",
    category: "",
    state: "",
    land_owned_acres: "0",
    is_bpl: false,
    is_disabled: false,
  });

  const set = (k: string, v: unknown) => setProfile(p => ({ ...p, [k]: v }));

  const canNext = () => {
    if (step === 0) return profile.age !== "" && profile.gender !== "";
    if (step === 1) return profile.annual_income !== "";
    if (step === 2) return profile.occupation !== "";
    if (step === 3) return profile.category !== "";
    return true;
  };

  const submit = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        age: Number(profile.age),
        annual_income: Number(profile.annual_income),
        occupation: profile.occupation,
        gender: profile.gender,
        category: profile.category,
        state: profile.state,
        land_owned_acres: Number(profile.land_owned_acres) || 0,
        is_bpl: profile.is_bpl,
        is_disabled: profile.is_disabled,
        top_n: 15,
        min_score_pct: 0,
      };
      setProfilePayload(payload); // Store for eligibility checks
      const res = await fetch("/api/v1/recommend/schemes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
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
      const data: RecommendationResponse = await res.json();
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const reset = () => { setResult(null); setStep(0); setError(null); };

  // ── Results view ─────────────────────────────────────────────────────────
  if (result) {
    const ps = result.profile_summary;
    return (
      <div className="min-h-screen bg-background px-4 py-10">
        {/* Eligibility Modal */}
        {eligibilityTarget && (
          <EligibilityModal
            schemeId={eligibilityTarget.id}
            schemeName={eligibilityTarget.name}
            profilePayload={profilePayload}
            onClose={() => setEligibilityTarget(null)}
          />
        )}
        <div className="max-w-3xl mx-auto">
          {/* Header */}
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
            <button onClick={reset} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors">
              <ChevronLeft className="h-4 w-4" /> New Profile
            </button>
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div>
                <h1 className="text-2xl font-bold text-foreground">Your Scheme Matches</h1>
                <p className="text-muted-foreground text-sm mt-1">
                  Found <span className="text-primary font-semibold">{result.total_eligible}</span> eligible schemes for you
                  {result.ranking_method === "ml_reranked" && (
                    <span className="ml-1.5 text-violet-400">· ordered by trained ML ranker</span>
                  )}
                </p>
              </div>
              {/* Profile pill */}
              <div className="flex flex-wrap gap-2 text-xs">
                {[
                  ps.age + " yrs",
                  ps.gender,
                  ps.category.toUpperCase(),
                  ps.occupation,
                  ps.income_band,
                  ps.is_bpl ? "BPL" : null,
                ].filter(Boolean).map((tag, i) => (
                  <span key={i} className="px-2 py-1 rounded-full bg-muted border border-border text-muted-foreground">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>

          {/* Scheme cards */}
          <div className="space-y-4">
            {result.recommendations.length === 0 ? (
              <div className="text-center py-20 text-muted-foreground">
                <AlertCircle className="h-12 w-12 mx-auto mb-3 opacity-40" />
                <p>No schemes matched your profile. Try adjusting the filters.</p>
              </div>
            ) : (
              result.recommendations.map((s, i) => (
                <SchemeCard
                  key={s.scheme_id}
                  scheme={s}
                  index={i}
                  onCheckEligibility={() => setEligibilityTarget({ id: s.scheme_id, name: s.name })}
                />
              ))
            )}
          </div>
        </div>
      </div>
    );
  }

  // ── Profile form ─────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4 py-10">
      <div className="w-full max-w-lg">
        {/* Title */}
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-8">
          <div className="inline-flex items-center gap-2 bg-primary/10 border border-primary/20 text-primary rounded-full px-4 py-1.5 text-sm font-medium mb-3">
            <Star className="h-3.5 w-3.5" /> Personalised Scheme Finder
          </div>
          <h1 className="text-2xl font-bold text-foreground">Find Schemes You're Eligible For</h1>
          <p className="text-muted-foreground text-sm mt-2">
            Fill your profile — our rule-based engine matches you to 18+ government schemes
          </p>
        </motion.div>

        {/* Progress */}
        <div className="flex items-center justify-between mb-8 relative">
          <div className="absolute top-4 left-0 right-0 h-0.5 bg-border" />
          <div
            className="absolute top-4 left-0 h-0.5 bg-primary transition-all duration-500"
            style={{ width: `${(step / (STEPS.length - 1)) * 100}%` }}
          />
          {STEPS.map((s) => {
            const Icon = s.icon;
            const done = step > s.id;
            const active = step === s.id;
            return (
              <div key={s.id} className="relative flex flex-col items-center gap-1 z-10">
                <div className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all duration-300",
                  done ? "bg-primary border-primary" : active ? "bg-background border-primary" : "bg-background border-border"
                )}>
                  {done
                    ? <CheckCircle2 className="h-4 w-4 text-primary-foreground" />
                    : <Icon className={cn("h-3.5 w-3.5", active ? "text-primary" : "text-muted-foreground")} />
                  }
                </div>
                <span className={cn("text-[10px] font-medium", active ? "text-primary" : "text-muted-foreground")}>
                  {s.label}
                </span>
              </div>
            );
          })}
        </div>

        {/* Form card */}
        <div className="bg-card border border-border rounded-2xl p-6 shadow-xl shadow-black/10">
          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
              className="space-y-5"
            >
              {/* Step 0 — Personal */}
              {step === 0 && (
                <>
                  <h2 className="font-semibold text-lg">Personal Details</h2>
                  <div>
                    <Label>Age</Label>
                    <Input
                      type="number" min={0} max={120} placeholder="e.g. 28"
                      value={profile.age}
                      onChange={e => set("age", e.target.value)}
                      className="mt-1.5"
                    />
                  </div>
                  <div>
                    <Label>Gender</Label>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {GENDERS.map(g => (
                        <SelectCard key={g.value} value={g.value} label={g.label}
                          selected={profile.gender === g.value}
                          onClick={() => set("gender", g.value)} />
                      ))}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <label className="flex items-center gap-2 cursor-pointer select-none">
                      <input type="checkbox" checked={profile.is_bpl}
                        onChange={e => set("is_bpl", e.target.checked)}
                        className="w-4 h-4 accent-primary" />
                      <span className="text-sm">I have a BPL card</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer select-none">
                      <input type="checkbox" checked={profile.is_disabled}
                        onChange={e => set("is_disabled", e.target.checked)}
                        className="w-4 h-4 accent-primary" />
                      <span className="text-sm">Person with disability</span>
                    </label>
                  </div>
                </>
              )}

              {/* Step 1 — Financial */}
              {step === 1 && (
                <>
                  <h2 className="font-semibold text-lg">Financial Details</h2>
                  <div>
                    <Label>Annual Household Income (₹)</Label>
                    <Input
                      type="number" min={0} placeholder="e.g. 120000"
                      value={profile.annual_income}
                      onChange={e => set("annual_income", e.target.value)}
                      className="mt-1.5"
                    />
                    <p className="text-xs text-muted-foreground mt-1">Enter total yearly income of your household</p>
                  </div>
                  <div>
                    <Label>Land Owned (acres)</Label>
                    <Input
                      type="number" min={0} step={0.1} placeholder="0 if none"
                      value={profile.land_owned_acres}
                      onChange={e => set("land_owned_acres", e.target.value)}
                      className="mt-1.5"
                    />
                  </div>
                </>
              )}

              {/* Step 2 — Occupation */}
              {step === 2 && (
                <>
                  <h2 className="font-semibold text-lg">Occupation</h2>
                  <div className="grid grid-cols-2 gap-2">
                    {OCCUPATIONS.map(o => (
                      <SelectCard key={o.value} value={o.value} label={o.label}
                        selected={profile.occupation === o.value}
                        onClick={() => set("occupation", o.value)} />
                    ))}
                  </div>
                </>
              )}

              {/* Step 3 — Category */}
              {step === 3 && (
                <>
                  <h2 className="font-semibold text-lg">Social Category</h2>
                  <div className="flex flex-wrap gap-2">
                    {CATEGORIES.map(c => (
                      <SelectCard key={c.value} value={c.value} label={c.label}
                        selected={profile.category === c.value}
                        onClick={() => set("category", c.value)} />
                    ))}
                  </div>
                </>
              )}

              {/* Step 4 — Location */}
              {step === 4 && (
                <>
                  <h2 className="font-semibold text-lg">Location (Optional)</h2>
                  <div>
                    <Label>State</Label>
                    <select
                      value={profile.state}
                      onChange={e => set("state", e.target.value)}
                      className="w-full mt-1.5 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                      <option value="">All India (No preference)</option>
                      {STATES.filter(Boolean).map(s => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    State is used for state-specific schemes (future). Most central schemes apply nationwide.
                  </p>
                </>
              )}
            </motion.div>
          </AnimatePresence>

          {/* Error */}
          {error && (
            <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" /> {error}
            </div>
          )}

          {/* Navigation */}
          <div className="flex justify-between mt-6">
            <Button variant="ghost" onClick={() => setStep(s => s - 1)} disabled={step === 0}>
              <ChevronLeft className="h-4 w-4 mr-1" /> Back
            </Button>
            {step < STEPS.length - 1 ? (
              <Button onClick={() => setStep(s => s + 1)} disabled={!canNext()}>
                Next <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            ) : (
              <Button onClick={submit} disabled={loading} className="gap-2">
                {loading ? <><Loader2 className="h-4 w-4 animate-spin" /> Analysing…</> : "Find My Schemes"}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
