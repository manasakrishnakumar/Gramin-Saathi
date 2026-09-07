"""
finetune_reranker.py — Phase 1

Domain-adapts the cross-encoder reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`,
currently used purely off-the-shelf in `app.services.hybrid_retriever`) to
Indian-government-scheme content, using the synthetic pairs from
data/generate_retrieval_dataset.py.

This is real fine-tuning (gradient updates on the pretrained cross-encoder
weights), not just calling the pretrained model — the resulting artifact is
a genuinely different model on disk. Trained on synthetic data though, so
treat it as a domain-adaptation starting point, not a guarantee of quality;
retrain on real (query, clicked-passage) pairs once Phase 0 event data
exists.

This does NOT modify or replace `hybrid_retriever.py`'s pretrained model —
it produces a separate artifact under app/models/reranker_v1/ that can be
swapped in later behind a feature flag if it out-performs the baseline on
held-out data (see evaluate.py).

Usage:
    cd backend
    python ml/data/generate_retrieval_dataset.py
    python ml/finetune_reranker.py
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

DATA_PATH = Path(__file__).resolve().parent / "data" / "retrieval_dataset.csv"
OUTPUT_DIR = BACKEND_ROOT / "app" / "models" / "reranker_v1"
BASE_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def load_pairs():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"{DATA_PATH} not found — run ml/data/generate_retrieval_dataset.py first.")
    rows = []
    with open(DATA_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append((row["query"], row["passage"], float(row["label"])))
    return rows


def main():
    from sentence_transformers import CrossEncoder, InputExample
    from sentence_transformers.cross_encoder.evaluation import CEBinaryClassificationEvaluator
    from torch.utils.data import DataLoader
    from sklearn.model_selection import train_test_split
    import json

    rows = load_pairs()
    print(f"Loaded {len(rows)} query/passage pairs")

    train_rows, test_rows = train_test_split(rows, test_size=0.2, random_state=42)
    train_examples = [InputExample(texts=[q, p], label=y) for q, p, y in train_rows]

    print(f"Loading base model: {BASE_MODEL} …")
    model = CrossEncoder(BASE_MODEL, num_labels=1)

    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)

    evaluator = CEBinaryClassificationEvaluator(
        sentence_pairs=[[q, p] for q, p, y in test_rows],
        labels=[int(y) for q, p, y in test_rows],
        name="scheme-retrieval-holdout",
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Fine-tuning (CPU) — this trains for 2 epochs over the synthetic set…")
    t0 = time.time()
    model.fit(
        train_dataloader=train_dataloader,
        evaluator=evaluator,
        epochs=2,
        warmup_steps=10,
        output_path=str(OUTPUT_DIR),
        show_progress_bar=False,
    )
    train_seconds = round(time.time() - t0, 1)
    print(f"Fine-tuning finished in {train_seconds}s")

    # Manual before/after sanity check: does the fine-tuned model score the
    # *correct* scheme passage above a *wrong* one for a few held-out queries?
    sample = test_rows[:6]
    scores = model.predict([[q, p] for q, p, y in sample])
    correct = 0
    for (q, p, y), score in zip(sample, scores):
        pred_positive = score > 0
        if pred_positive == bool(y):
            correct += 1
    sample_acc = correct / len(sample) if sample else 0.0

    manifest = {
        "model": "cross-encoder fine-tuned from " + BASE_MODEL,
        "version": "v1",
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "train_examples": len(train_rows),
        "test_examples": len(test_rows),
        "train_seconds": train_seconds,
        "holdout_sample_accuracy": round(sample_acc, 3),
        "training_data": "SYNTHETIC — templated queries against SCHEME_REGISTRY descriptions, not real scraped documents or real user queries. See ml/README.md.",
        "artifact": str(OUTPUT_DIR.relative_to(BACKEND_ROOT)),
        "base_model": BASE_MODEL,
        "not_wired_in": "hybrid_retriever.py still uses the pretrained base model unchanged — this artifact is standalone until explicitly swapped in behind a flag.",
    }
    with open(OUTPUT_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Saved fine-tuned reranker -> {OUTPUT_DIR}")
    print(f"Sample holdout sanity-check accuracy: {sample_acc:.2f}")


if __name__ == "__main__":
    main()
