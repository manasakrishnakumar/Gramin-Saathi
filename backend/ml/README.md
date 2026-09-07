# ML module — Gramin Saathi

Every model/service/endpoint here (`app/services/ml_*.py`,
`app/schemas/ml_*.py`, `app/api/v1/endpoints/ml_*.py`,
`app/api/v1/ml_router.py`, `app/models/`, `frontend/src/components/ml/`,
everything under `backend/ml/`) started as pure additions — no existing
file was touched to build any of it. Wiring some of it into the live app
afterward (on explicit request) required a small, specific set of edits
to pre-existing files — listed in **"What's actually wired into the live
app"** below, so it's always clear which lines in `rag_service.py`,
`recommendation.py`, etc. exist because of this ML work.

Zero new runtime dependencies ended up necessary in `requirements.txt`.
Two dev-time additions to `backend/venv` only: `sklearn-crfsuite` (for
the NER model, verified conflict-free — see Task 5 below) and a
short-lived `lightgbm` install that got reverted after it crashed
alongside the already-loaded scikit-learn models (see Task 2 below);
neither touches the committed `requirements.txt`.

## Status at a glance

Every "Trained"/"Simulated" row below is a real artifact on disk under
`app/models/`, produced by actually running the corresponding script —
not a mock. Re-run any script yourself to reproduce these numbers.

| # | What | Status | Headline metric |
|---|---|---|---|
| 0 | Event/feedback logging | Built, functional | Standalone until frontend widgets are dropped into ChatPage/RecommendPage |
| 1a | Intent classifier | **Wired into live chat** | 95.3% accuracy, 0.954 macro F1 |
| 1b | RAG reranker fine-tune | Trained, standalone | Real gradient fine-tune, 31s |
| 1c | Multilingual embedder fine-tune | Trained, standalone | Top-1 retrieval acc 0.80→0.90 |
| 2 | Recommendation ranker | **Wired into live /recommend/schemes** | ROC-AUC 0.719 |
| 3 | Outcome/"approval likelihood" | **Wired into live EligibilityModal, SYNTHETIC DEMO only** | See caveat below — built on explicit override |
| 4 | Query volume forecasting | Trained, standalone | MAE 1.11 queries/hr (synthetic — only 5 real rows exist) |
| 5 | Profile anomaly detection | Trained, standalone | Correctly flags a hand-built nonsense profile |
| 6 | Answer groundedness scorer | **Wired into live chat** | Accuracy 0.98 (synthetic) — see limitation note |
| 7 | Scheme-data NER (CRF) | Trained, standalone | F1 1.00 (synthetic) — verified on unseen sentences |
| 8 | User segmentation (KMeans) | Trained, standalone | 5 interpretable clusters |
| 9 | Contextual bandit ranker | Trained (simulation), standalone | Regret dropped 66% over 3000 simulated rounds |
| 10 | Voice transcription quality | **Wired into live /voice/converse** | Accuracy 0.75 (synthetic) — see limitation note |

## What's actually wired into the live app

On explicit request, these specific edits were made to pre-existing files
(everything else in this table stays standalone until you ask for it to
be wired in too):

- **`app/api/v1/api.py`** — 2 lines mounting `ml_router` (all `/ml/*` endpoints)
- **`app/services/rag_service.py`** — `stream_query()` now tags each chat
  turn with the trained intent classifier (Task 1a) instead of the rule
  fallback, and scores each answer's groundedness (Task 6) against its
  retrieved context, emitting both as new SSE event types (`intent`,
  `groundedness`) that the existing frontend safely ignored before this
- **`app/api/v1/endpoints/recommendation.py`** + **`app/schemas/recommendation.py`**
  — `/recommend/schemes` now reorders already rule-eligible results using
  the trained ranker (Task 2), exposing `ml_engagement_score` per scheme
  and a `ranking_method` field; disqualified/ineligible schemes are
  untouched by this — the rule engine's hard-eligibility gate is unchanged
- **`app/api/v1/endpoints/voice.py`** — `/voice/converse` now runs the
  voice-quality classifier (Task 10) on the STT transcript and includes
  the result in the response (English transcripts only)
- **`frontend/src/pages/ChatPage.tsx`** — renders the intent classification
  and a soft groundedness nudge (only below a conservative confidence
  threshold) next to each assistant message
- **`frontend/src/pages/RecommendPage.tsx`** — renders the ML engagement
  score badge and "ordered by trained ML ranker" note
- **`frontend/src/components/EligibilityModal.tsx`** — renders the Phase 3
  SYNTHETIC DEMO prediction in a visually distinct dashed-border amber
  section, disclaimer always attached, never merged with the real
  (rule-based) eligibility verdict shown above it in the same modal

## Task 1 — Intent classifier, RAG reranker, multilingual fine-tune

```bash
cd backend
venv/Scripts/python.exe ml/data/generate_intent_dataset.py
venv/Scripts/python.exe ml/train_intent_classifier.py
venv/Scripts/python.exe ml/data/generate_retrieval_dataset.py
venv/Scripts/python.exe ml/finetune_reranker.py
venv/Scripts/python.exe ml/finetune_multilingual.py
```

**1a. Intent classifier** — TF-IDF + Logistic Regression on 254 templated
examples. **95.3% accuracy, 0.954 macro F1** held-out. Live in the chat —
see `ml_intent_classifier_service.py`.

**1b. RAG reranker fine-tune** — real gradient fine-tune of
`cross-encoder/ms-marco-MiniLM-L-6-v2` on 234 synthetic (query, passage,
relevant?) triples. 90MB checkpoint, 31s to train. Standalone — `hybrid_retriever.py` still uses the pretrained base model.

**1c. Multilingual embedder fine-tune** — `MultipleNegativesRankingLoss`
fine-tune of `paraphrase-multilingual-MiniLM-L12-v2`. **Top-1 retrieval
accuracy: base 0.80 → fine-tuned 0.90**, same held-out eval both times.
Standalone — `multilingual_service.py` unchanged.

## Task 2 — Recommendation ranker

```bash
venv/Scripts/python.exe ml/data/generate_ranker_bootstrap.py
venv/Scripts/python.exe ml/train_ranker_bootstrap.py
```

**ROC-AUC 0.719, average precision 0.916** on 1,939 synthetic
(profile, eligible-scheme) rows. Labels are a weak-supervision proxy
derived from the rule engine's own score, not real behavior — see the
script's docstring. Live in `/recommend/schemes`, reordering only
already-eligible results.

**A real bug found and fixed while building this**: originally used
LightGBM. Loading the scikit-learn intent classifier (Task 1a) and then
calling LightGBM's native `predict` in the same process reliably crashed
with `OSError: exception: access violation reading 0x0...` — a conflict
between two different bundled OpenMP runtimes, reproduced directly and
isolated to "any scikit-learn model loaded first," not anything specific
to this app. Swapped to scikit-learn's own `HistGradientBoostingClassifier`
— same result, zero new dependency, proven stable in-process (it's the
same native stack already used elsewhere in this app).

`ml/train_ranker_from_events.py` is the real version — same feature
engineering, reads from `ml_feedback_service.export_ranker_training_rows()`
instead of synthetic data, refuses to run below 500 real logged events.

## Task 3 — Outcome / "approval likelihood" (SYNTHETIC DEMO)

Originally not built — see the "why this wasn't built unprompted"
reasoning preserved in `PHASE3_NOTES.md`: there's no real
approval/rejection data, and unlike every other task here, there's no
honest way to synthesize the *specific* label being predicted (a real
government decision). Built anyway on **explicit user instruction**
overriding that default, for an academic-project context, with every
artifact end-to-end tagged `SYNTHETIC_DEMO` — filename, manifest, API
response, and the UI element that shows it (dashed amber border, "Not
Real Data" label, disclaimer text on every single response).

```bash
venv/Scripts/python.exe ml/data/generate_outcome_bootstrap.py
venv/Scripts/python.exe ml/train_outcome_model_DEMO.py
```

Fabricated labels via a hand-written heuristic (documentation
completeness + BPL status + noise) — **not real outcomes, not
extrapolated from anything real**. ROC-AUC 0.648 on the synthetic task
itself; that number describes how well the model fits the made-up
heuristic, not real-world accuracy. Kept in a completely separate model
file and service (`ml_outcome_predictor_service.py`) from the real
outcome-collection pathway (`ml_outcome_service.py`, `POST
/ml/outcomes/report`) — the two must never be merged.

## Task 4 — Query volume forecasting

```bash
venv/Scripts/python.exe ml/data/generate_query_volume_bootstrap.py
venv/Scripts/python.exe ml/train_query_forecast.py
```

`metrics.db` (existing query logs) only had **5 real rows** at build
time — nowhere near enough to fit a seasonal model. Falls back to a
synthetic seasonal bootstrap (evening-peak usage pattern, weekend boost,
gradual adoption trend — designer's assumption, not measured), MAE 1.11
queries/hour on the synthetic task. `train_query_forecast.py` checks the
real row count every time it's run and automatically switches to real
data once there are 500+ real rows — no code change needed, just re-run
it later.

## Task 5 — Profile anomaly detection

```bash
venv/Scripts/python.exe ml/data/generate_profile_distribution.py
venv/Scripts/python.exe ml/train_anomaly_detector.py
```

Unsupervised `IsolationForest` — genuinely no labels needed or used.
Sanity-checked directly: a typical profile (age 35 farmer, moderate
income) scores normal (0.070, not flagged); a hand-built nonsense profile
(age 14, ₹50 lakh income, 200 acres) correctly flags as anomalous
(-0.026). `sklearn-crfsuite` was verified compatible with the rest of the
loaded model stack before use (see Task 7) — no repeat of the Task 2
lightgbm conflict.

## Task 6 — Answer groundedness / hallucination scoring

```bash
venv/Scripts/python.exe ml/data/generate_groundedness_dataset.py
venv/Scripts/python.exe ml/train_groundedness_classifier.py
```

Classifier on hand-engineered features (word overlap, embedding cosine
similarity via `all-MiniLM-L6-v2`, length ratio, numeric-mismatch flag)
over synthetic (context, answer, grounded?) pairs — simulates topic
mismatch, fabricated numbers, and off-topic filler as hallucination
types. **Two real bugs found and fixed via direct testing, not just
held-out accuracy**:
1. First version scored a genuinely good, naturally-paraphrased answer
   as "ungrounded" (0.19) because the synthetic training data's
   "paraphrases" were too close to verbatim copies — the model over-learned
   "high word overlap = grounded." Fixed by adding rule-based
   synonym-substitution paraphrases to the training set.
2. Added "hard negatives" (same vocabulary/ministry/style as a correct
   answer, but a fabricated wrong claim about eligibility) so the model
   can't just use word overlap as a shortcut — these are now correctly
   caught (0.01 grounded-probability, i.e. confidently flagged).

**Known remaining limitation, disclosed rather than hidden**: a heavily
reworded but factually correct answer using vocabulary far outside the
training set can still false-positive as "ungrounded" — the
rule-based paraphraser can't produce the full diversity a real LLM
rewrite would. Wired into the live chat *conservatively* as a result: a
soft, low-key badge that only appears below a strict confidence
threshold, phrased as a suggestion ("consider verifying"), never a
hard "this is wrong" claim.

## Task 7 — Scheme-data NER

```bash
venv/Scripts/python.exe ml/data/generate_ner_dataset.py
venv/Scripts/python.exe ml/train_ner_model.py
```

CRF (`sklearn-crfsuite`) sequence-labeling model — extracts SCHEME,
MINISTRY, AMOUNT, AGE, PCT entities from free text, aimed at newly
scraped scheme documents (`scraper_service.py`) to reduce how much of
`SCHEME_REGISTRY` needs hand-transcription (the one part of this whole
pipeline still fully manual — arguably the highest real-world value of
anything built in this pass). F1 1.00 on the synthetic held-out split.

**Generalization bug found and fixed via direct testing on unseen
sentences** (not template-generated): the first version, trained on only
4 sentence templates, missed "PM-KISAN" entirely as a SCHEME entity in a
new sentence structure, truncated ministry names, and missed age ranges
phrased differently than training. Expanding to 8 template patterns (168
training sentences instead of 68) fixed all three on the same test
sentences — verified by rerunning the exact same unseen-sentence probe
before and after. One minor residual limitation remains and is
documented in the endpoint docstring: multi-word ministry names
containing "and" can still truncate (e.g. "Ministry of Commerce and
Industry" → "Ministry of Commerce").

## Task 8 — User segmentation

```bash
venv/Scripts/python.exe ml/train_profile_clusters.py
```

Unsupervised KMeans (k=5) over the same realistic profile distribution as
Task 5. Auto-generates human-readable labels per cluster from its own
centroid statistics (not hand-written) — e.g. "middle-aged, high-income
self employeds," "moderate-income farmers." Descriptive analytics only;
doesn't feed into eligibility, ranking, or anything outcome-affecting.

## Task 9 — Contextual bandit ranker

```bash
venv/Scripts/python.exe ml/simulate_bandit.py
```

A genuinely different technique from everything else here: LinUCB
(pure numpy, no new dependency) does **online learning** — it updates
immediately after each observed reward, no batch retrain step, unlike
the static Task 2 ranker. Verified via a 3000-round simulation using the
real, unmodified rule engine to determine eligible schemes each round:
**regret dropped 66%** (0.069 → 0.024 in a rolling 200-round window) over
the course of the simulation — the cleaner convergence signal here, since
many schemes tie for the top rule score, making exact oracle-agreement a
noisier metric than regret. `ml_bandit_service.update()` is designed to
be called with real reward signals from `ml_feedback_service.py` as they
arrive, learning from each one live — not wired to real events yet
(Phase 0 isn't collecting live traffic), but the mechanism itself is
proven, not just asserted.

## Task 10 — Voice transcription quality

```bash
venv/Scripts/python.exe ml/data/generate_transcript_quality_dataset.py
venv/Scripts/python.exe ml/train_transcript_quality_classifier.py
```

No real Sarvam STT transcripts (clean or garbled) exist to train on —
would need live microphone input + paid API calls. Standard workaround
when real ASR-error data isn't available: corrupt clean text with
simulated ASR-style noise (word deletion/duplication/shuffling, char
substitution, filler insertion) — an established technique in ASR
quality-estimation research, not invented for this project.

**Two real bugs found and fixed via direct testing**:
1. First version (bag-of-words features only: out-of-vocabulary rate,
   repeated-word ratio, etc.) scored 59% accuracy — barely better than
   chance. Diagnosis: half the corruption types (word shuffling, random
   deletion) don't change *which* words appear, only their *order* — so
   bag-of-words features are structurally blind to them. Added a bigram
   out-of-vocabulary-rate feature (a lightweight n-gram perplexity proxy
   that does capture word-order plausibility) — accuracy jumped to 81%.
2. Even then, genuinely clean sentences using vocabulary outside the tiny
   (78-sentence) reference corpus false-positived as "garbled." Expanded
   the reference corpus to ~30 additional everyday sentences — 2 of 3
   held-out clean test sentences now correctly classify; documented the
   remaining gap rather than continuing to chase it (same standard of
   honesty as Task 6).

Wired into `/voice/converse` (English transcripts only — the reference
vocabulary is English) as an informational flag alongside the response,
never blocking the flow.

## Re-running everything from scratch

```bash
cd backend
venv/Scripts/python.exe -m pip install sklearn-crfsuite   # only genuinely new dependency
venv/Scripts/python.exe ml/data/generate_intent_dataset.py && venv/Scripts/python.exe ml/train_intent_classifier.py
venv/Scripts/python.exe ml/data/generate_retrieval_dataset.py && venv/Scripts/python.exe ml/finetune_reranker.py && venv/Scripts/python.exe ml/finetune_multilingual.py
venv/Scripts/python.exe ml/data/generate_ranker_bootstrap.py && venv/Scripts/python.exe ml/train_ranker_bootstrap.py
venv/Scripts/python.exe ml/data/generate_outcome_bootstrap.py && venv/Scripts/python.exe ml/train_outcome_model_DEMO.py
venv/Scripts/python.exe ml/data/generate_query_volume_bootstrap.py && venv/Scripts/python.exe ml/train_query_forecast.py
venv/Scripts/python.exe ml/data/generate_profile_distribution.py && venv/Scripts/python.exe ml/train_anomaly_detector.py
venv/Scripts/python.exe ml/data/generate_groundedness_dataset.py && venv/Scripts/python.exe ml/train_groundedness_classifier.py
venv/Scripts/python.exe ml/data/generate_ner_dataset.py && venv/Scripts/python.exe ml/train_ner_model.py
venv/Scripts/python.exe ml/train_profile_clusters.py
venv/Scripts/python.exe ml/simulate_bandit.py
venv/Scripts/python.exe ml/data/generate_transcript_quality_dataset.py && venv/Scripts/python.exe ml/train_transcript_quality_classifier.py
```

All scripts are deterministic (seeded) except the two neural fine-tunes
(1b, 1c), which vary slightly run to run but land in the same range.
