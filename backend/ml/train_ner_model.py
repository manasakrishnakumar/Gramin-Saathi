"""
train_ner_model.py — NER for automatic scheme-data extraction

Trains a CRF (Conditional Random Field — genuine sequence-labeling ML,
the standard classical approach for this exact task, lighter-weight than
a transformer NER model and needs no new heavy dependency beyond
`sklearn-crfsuite`) on the BIO-tagged data from data/generate_ner_dataset.py.

Usage:
    cd backend
    python ml/data/generate_ner_dataset.py
    python ml/train_ner_model.py
"""

from __future__ import annotations

import json
import pickle
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from ner_features import sentence_features  # noqa: E402

DATA_PATH = Path(__file__).resolve().parent / "data" / "ner_dataset.json"
MODEL_DIR = BACKEND_ROOT / "app" / "models"
MODEL_PATH = MODEL_DIR / "ner_crf_v1.pkl"
MANIFEST_PATH = MODEL_DIR / "ner_crf_v1.manifest.json"


def main():
    import sklearn_crfsuite
    from sklearn_crfsuite import metrics as crf_metrics
    from sklearn.model_selection import train_test_split

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"{DATA_PATH} not found — run ml/data/generate_ner_dataset.py first.")

    examples = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(examples)} BIO-tagged sentences")

    X = [sentence_features(ex["tokens"]) for ex in examples]
    y = [ex["tags"] for ex in examples]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    crf = sklearn_crfsuite.CRF(
        algorithm="lbfgs", c1=0.1, c2=0.1, max_iterations=100, all_possible_transitions=True
    )
    t0 = time.time()
    crf.fit(X_train, y_train)
    train_seconds = round(time.time() - t0, 2)

    y_pred = crf.predict(X_test)
    labels = [l for l in crf.classes_ if l != "O"]
    f1 = crf_metrics.flat_f1_score(y_test, y_pred, average="weighted", labels=labels)
    report = crf_metrics.flat_classification_report(y_test, y_pred, labels=labels, digits=3)
    print(f"Trained in {train_seconds}s on {len(X_train)} sentences, evaluated on {len(X_test)} held-out")
    print(f"Weighted entity F1: {f1:.3f}")
    print(report)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(crf, f)

    manifest = {
        "model": "sklearn-crfsuite CRF (lbfgs)",
        "version": "v1",
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "train_sentences": len(X_train),
        "test_sentences": len(X_test),
        "train_seconds": train_seconds,
        "weighted_f1": round(f1, 4),
        "entity_types": sorted(labels),
        "training_data": "Templated sentences built from real SCHEME_REGISTRY names/ministries/descriptions/criteria, BIO tags assigned by construction. See ml/data/generate_ner_dataset.py.",
        "artifact": str(MODEL_PATH.relative_to(BACKEND_ROOT)),
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Saved model  -> {MODEL_PATH}")
    print(f"Saved manifest -> {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
