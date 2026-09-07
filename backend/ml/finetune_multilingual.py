"""
finetune_multilingual.py — Phase 1

Domain-adapts the multilingual bi-encoder (`paraphrase-multilingual-MiniLM-L12-v2`,
currently used purely off-the-shelf in `app.services.multilingual_service`)
to Hinglish/regional-language scheme queries, using the same synthetic
retrieval dataset as the reranker (data/generate_retrieval_dataset.py),
restricted to its Hinglish-flavored positive pairs.

Uses MultipleNegativesRankingLoss — the standard approach for fine-tuning
a bi-encoder from (query, relevant-passage) positive pairs alone, using
other in-batch passages as implicit negatives. Real gradient fine-tuning,
not just inference — produces a distinct model artifact.

Trained on synthetic/templated Hinglish, not authentic native-script text
or real user queries — see ml/README.md. Does NOT modify or replace
multilingual_service.py's pretrained model; saves a separate standalone
artifact.

Usage:
    cd backend
    python ml/data/generate_retrieval_dataset.py   # if not already run
    python ml/finetune_multilingual.py
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

DATA_PATH = Path(__file__).resolve().parent / "data" / "retrieval_dataset.csv"
OUTPUT_DIR = BACKEND_ROOT / "app" / "models" / "multilingual_v1"
BASE_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


def load_positive_pairs():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"{DATA_PATH} not found — run ml/data/generate_retrieval_dataset.py first.")
    rows = []
    with open(DATA_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["label"] == "1":  # MultipleNegativesRankingLoss needs positives only
                rows.append((row["query"], row["passage"], row["lang"]))
    return rows


def main():
    from sentence_transformers import SentenceTransformer, InputExample, losses
    from sentence_transformers.util import cos_sim
    from torch.utils.data import DataLoader
    from sklearn.model_selection import train_test_split

    rows = load_positive_pairs()
    print(f"Loaded {len(rows)} positive query/passage pairs "
          f"({sum(1 for r in rows if r[2] == 'hi-mix')} Hinglish, "
          f"{sum(1 for r in rows if r[2] == 'en')} English)")

    train_rows, test_rows = train_test_split(rows, test_size=0.2, random_state=42)
    train_examples = [InputExample(texts=[q, p]) for q, p, _ in train_rows]

    print(f"Loading base model: {BASE_MODEL} …")
    model = SentenceTransformer(BASE_MODEL)

    # Retrieval-accuracy check (top-1 recall against distractor passages),
    # computed the same way both before and after fine-tuning so the delta
    # is meaningful. This fits this data far better than a correlation-based
    # evaluator: our held-out set is *all positive* pairs (no graded
    # similarity scores to correlate against), but "does the fine-tuned
    # model rank the correct passage #1 among several candidates" is
    # exactly the retrieval behavior this model is used for downstream.
    all_passages = sorted({p for _, p, _ in rows})

    def top1_retrieval_accuracy(m) -> float:
        correct = 0
        for q, p, _ in test_rows:
            q_emb = m.encode([q], convert_to_tensor=True, normalize_embeddings=True)
            cand_passages = [p] + [c for c in all_passages if c != p][:9]  # 1 correct + up to 9 distractors
            c_emb = m.encode(cand_passages, convert_to_tensor=True, normalize_embeddings=True)
            sims = cos_sim(q_emb, c_emb)[0]
            if int(sims.argmax()) == 0:
                correct += 1
        return correct / len(test_rows) if test_rows else 0.0

    print("Scoring base (pretrained) model on held-out retrieval accuracy…")
    base_acc = top1_retrieval_accuracy(model)
    print(f"Base model top-1 retrieval accuracy: {base_acc:.3f}")

    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)
    train_loss = losses.MultipleNegativesRankingLoss(model)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Fine-tuning (CPU) — this trains for 3 epochs over the synthetic set…")
    t0 = time.time()
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=3,
        warmup_steps=10,
        output_path=str(OUTPUT_DIR),
        show_progress_bar=False,
    )
    train_seconds = round(time.time() - t0, 1)
    print(f"Fine-tuning finished in {train_seconds}s")

    print("Scoring fine-tuned model on the same held-out retrieval accuracy…")
    eval_score = top1_retrieval_accuracy(model)
    print(f"Fine-tuned model top-1 retrieval accuracy: {eval_score:.3f}  (base was {base_acc:.3f})")

    manifest = {
        "model": "multilingual bi-encoder fine-tuned from " + BASE_MODEL,
        "version": "v1",
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "train_examples": len(train_rows),
        "test_examples": len(test_rows),
        "train_seconds": train_seconds,
        "holdout_top1_retrieval_accuracy": round(eval_score, 3),
        "base_model_holdout_top1_retrieval_accuracy": round(base_acc, 3),
        "training_data": "SYNTHETIC — templated Hinglish/English queries against SCHEME_REGISTRY descriptions, not authentic native-script text or real user queries. See ml/README.md.",
        "artifact": str(OUTPUT_DIR.relative_to(BACKEND_ROOT)),
        "base_model": BASE_MODEL,
        "not_wired_in": "multilingual_service.py still uses the pretrained base model unchanged — this artifact is standalone until explicitly swapped in behind a flag.",
    }
    with open(OUTPUT_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Saved fine-tuned multilingual embedder -> {OUTPUT_DIR}")
    print(f"Holdout top-1 retrieval accuracy: {eval_score:.3f} (base model: {base_acc:.3f})")


if __name__ == "__main__":
    main()
