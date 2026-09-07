# Phase 3

**Update:** the user explicitly reviewed the reasoning below and asked for
a demo model anyway, for an academic project context (not a live
government-facing deployment). Built as `ml/train_outcome_model_DEMO.py`,
served by `ml_outcome_predictor_service.py`, wired into
`EligibilityModal.tsx` as a visually distinct amber/dashed-border section
labeled "Synthetic Demo — Not Real Data," carrying the disclaimer text on
every single response so it can't be silently stripped or mistaken for
the real (rule-based) eligibility verdict shown right above it in the
same modal. The original reasoning for not building it unprompted is kept
below, unedited, because it's still the right default absent an explicit
override like this one — and because it explains exactly what the demo
model is (and isn't) proving.

## Why this wasn't built unprompted

Phase 3 was described as an "approval likelihood" signal layered on top of
the rule-based eligibility verdict: given a real applicant's profile and
documentation, predict how likely their application is to actually be
approved by the government, beyond the deterministic eligibility check.

**That needs real approval/rejection outcomes.** This project doesn't have
any, and — same as the original problem statement at the start of this
whole ML effort — there's no shortcut around that with synthetic data,
because the label being predicted here (*did a real bureaucratic process
approve this specific person*) isn't something the rule engine, an LLM, or
a template generator can honestly stand in for. Every other phase in this
pass could bootstrap from something legitimate:

- Phase 1's intent classifier: labels came from the deterministic intent
  taxonomy + templates — the "ground truth" is just "does this text match
  this category", which is knowable without real outcomes.
- Phase 1's retrieval fine-tuning: labels came from "is this passage about
  the scheme the query asks about" — again knowable in advance.
- Phase 2's bootstrap ranker: explicitly a placeholder, trained on a proxy
  signal *derived from* the rule engine's own score, clearly documented as
  such, and designed to be thrown away the moment real click data exists.

Phase 3 has no such proxy. "Will a specific application be approved" is
determined by a real government process this codebase has no visibility
into. Fabricating labels for it — even clearly documented as synthetic —
and serving a resulting "likelihood of approval: 72%" number to someone
deciding whether to spend time/money pursuing a welfare application would
be actively misleading, not just imprecise. That crosses from "imperfect
ML" into presenting invented confidence about a real person's real outcome
as if it were informed.

## What's actually here instead

- `app/schemas/ml_outcome.py` — the data shape a real outcome report needs
- `app/services/ml_outcome_service.py` — stores real outcome reports in
  their own table, nothing more
- `app/api/v1/endpoints/ml_outcomes.py` — `POST /ml/outcomes/report` /
  `GET /ml/outcomes/count`, for a trusted source (partner NGO, scheme
  administrator, verified follow-up survey) to log real outcomes as they
  become available

## When this becomes buildable

If/when there's a real, verified, meaningfully-sized set of
(profile, scheme, actual outcome) records — from a partnership, a
follow-up survey with real response volume, or access to government
application-tracking data — write `train_outcome_model.py` following the
exact same pattern as `train_ranker_from_events.py`: read from
`ml_outcome_service`, require a minimum real-row count before it will even
run, and never let it be the sole source of truth on eligibility — only an
auxiliary, clearly-labeled confidence signal alongside the deterministic
rule-based verdict, never a replacement for it.
