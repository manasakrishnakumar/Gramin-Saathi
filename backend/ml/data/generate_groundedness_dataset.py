"""
generate_groundedness_dataset.py — Answer groundedness / hallucination scoring

Builds synthetic (context, answer, grounded?) examples to train a
classifier that scores whether a generated answer is actually supported
by its retrieved context, vs. likely hallucinated — using
SCHEME_REGISTRY (read-only import) as the source of "context" passages,
same pattern as the reranker/multilingual bootstrap datasets.

Three deliberately different hallucination types are simulated, matching
real RAG failure modes:
  1. topic_mismatch  — answer is about a DIFFERENT scheme than the context
  2. fabricated_number — answer invents a specific number not in the context
  3. off_topic       — answer is generic filler unrelated to any scheme

Output: backend/ml/data/groundedness_dataset.csv (context,answer,grounded,failure_type)
"""

from __future__ import annotations

import csv
import random
import re
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.recommendation_service import SCHEME_REGISTRY  # noqa: E402

random.seed(5)

# Lightweight rule-based paraphraser (synonym substitution + light
# restructuring) — NOT an LLM call. Used to generate grounded examples
# with genuinely LOWER literal word overlap than a near-verbatim copy,
# so the classifier can't just learn "high word overlap = grounded" and
# ignore embedding similarity; it has to generalize past copy-paste.
_SYNONYMS = {
    "provides": "offers", "provide": "offer", "income": "financial", "support": "assistance",
    "farmers": "cultivators", "farmer": "cultivator", "scheme": "programme", "government": "state",
    "benefits": "advantages", "benefit": "advantage", "apply": "register", "eligible": "qualifying",
    "insurance": "coverage", "financial": "monetary", "annual": "yearly", "loan": "credit",
    "assistance": "aid", "grants": "funding", "grant": "fund", "students": "learners",
    "women": "female applicants", "children": "minors", "disability": "impairment",
    "housing": "shelter", "rural": "village-area", "healthcare": "medical care",
}


def _paraphrase(text: str) -> str:
    words = text.split()
    out = []
    for w in words:
        core = w.strip(".,()")
        suffix = w[len(core):] if w.startswith(core) else ""
        lower = core.lower()
        if lower in _SYNONYMS:
            repl = _SYNONYMS[lower]
            if core[:1].isupper():
                repl = repl[:1].upper() + repl[1:]
            out.append(repl + suffix)
        else:
            out.append(w)
    return " ".join(out)


OFF_TOPIC_FILLERS = [
    "The weather today is expected to be sunny with a light breeze.",
    "You can cook rice by boiling it in water for about fifteen minutes.",
    "The capital of France is Paris, a city known for its museums.",
    "Cricket is a popular sport played between two teams of eleven players.",
    "The moon orbits the Earth approximately every twenty-seven days.",
]


def context_for(scheme: dict) -> str:
    return f"{scheme['name']} ({scheme['ministry']}): {scheme['description']}"


def grounded_answer_for(scheme: dict) -> str:
    return f"{scheme['name']} is run by {scheme['ministry']}. It provides: {scheme['description']}"


_WRONG_TARGET_SWAPS = [
    "salaried IT employees in metro cities", "large industrial corporations",
    "foreign nationals visiting India", "private hospital chains",
]


def hard_negative_wrong_target(scheme: dict) -> str:
    """
    Same vocabulary/style/ministry as a grounded answer (high word overlap
    on purpose), but a factually wrong claim about who it's for — this is
    the actual dangerous kind of hallucination (fluent, on-topic, subtly
    wrong), and it's the case the model must learn NOT to pass just
    because the surface words overlap heavily with the context.
    """
    wrong_target = random.choice(_WRONG_TARGET_SWAPS)
    return (
        f"{scheme['name']} is run by {scheme['ministry']} and is specifically designed for "
        f"{wrong_target}. {scheme['description']}"
    )


def fabricate_number_variant(answer: str) -> str:
    numbers = re.findall(r"₹?[\d,]+(?:\.\d+)?", answer)
    if not numbers:
        return answer + f" Additional cash bonus of ₹{random.choice([25000, 50000, 100000])} is also provided in the first year."
    target = random.choice(numbers)
    fabricated = str(random.choice([25000, 45000, 75000, 999999]))
    return answer.replace(target, fabricated, 1)


def main():
    rows = []
    for scheme in SCHEME_REGISTRY:
        context = context_for(scheme)

        # Grounded — mix of near-verbatim AND genuine paraphrases (lower
        # word overlap, same meaning). Skewed toward paraphrases (4 of 5)
        # since that's what a real LLM answer actually looks like — a
        # near-verbatim copy is the unrealistic case, not the norm.
        grounded = grounded_answer_for(scheme)
        rows.append((context, grounded, 1, "grounded"))  # 1 near-verbatim, for contrast
        rows.append((context, _paraphrase(f"You may qualify for financial assistance under {scheme['name']}, run by {scheme['ministry']}: {scheme['description']}"), 1, "grounded_paraphrase"))
        rows.append((context, _paraphrase(f"This programme, {scheme['name']}, is administered by {scheme['ministry']}. In short, {scheme['description']}"), 1, "grounded_paraphrase"))
        rows.append((context, _paraphrase(f"{scheme['description']} That's what {scheme['name']} offers, under {scheme['ministry']}."), 1, "grounded_paraphrase"))
        rows.append((context, _paraphrase(scheme["description"]), 1, "grounded_paraphrase"))  # partial info, paraphrased, no scheme name/ministry mentioned

        # Ungrounded: topic mismatch — answer about a different scheme
        # (one near-verbatim, one paraphrased — same reasoning as above:
        # a hallucinated answer can be fluently paraphrased too, so low
        # overlap alone must not be the model's only signal for "ungrounded").
        other = random.choice([s for s in SCHEME_REGISTRY if s["id"] != scheme["id"]])
        rows.append((context, grounded_answer_for(other), 0, "topic_mismatch"))
        rows.append((context, _paraphrase(grounded_answer_for(other)), 0, "topic_mismatch_paraphrase"))

        # Ungrounded: fabricated number
        rows.append((context, fabricate_number_variant(grounded), 0, "fabricated_number"))
        rows.append((context, _paraphrase(fabricate_number_variant(grounded)), 0, "fabricated_number_paraphrase"))

        # Ungrounded: off-topic filler
        rows.append((context, random.choice(OFF_TOPIC_FILLERS), 0, "off_topic"))

        # Ungrounded (hard negative): correct scheme name/ministry/wording,
        # high word overlap with context, but a wrong claim about who
        # qualifies — forces the model to use more than just word overlap.
        rows.append((context, hard_negative_wrong_target(scheme), 0, "hard_negative_wrong_target"))
        rows.append((context, _paraphrase(hard_negative_wrong_target(scheme)), 0, "hard_negative_wrong_target_paraphrase"))

    random.shuffle(rows)
    out_path = Path(__file__).resolve().parent / "groundedness_dataset.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["context", "answer", "grounded", "failure_type"])
        writer.writerows(rows)

    grounded_n = sum(1 for r in rows if r[2] == 1)
    print(f"Wrote {len(rows)} (context, answer) pairs to {out_path}  ({grounded_n} grounded / {len(rows)-grounded_n} ungrounded)")


if __name__ == "__main__":
    main()
