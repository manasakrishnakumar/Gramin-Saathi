"""
generate_transcript_quality_dataset.py — Voice transcription quality classifier

No real Sarvam STT transcripts (clean or garbled) exist to train on —
getting them would mean live microphone input + paid API calls, which
this offline script has no access to and shouldn't spend unprompted.
Standard technique when real ASR-error data isn't available: corrupt
clean text with simulated ASR-style noise (word deletion, word
duplication, character-level substitution, word-order shuffling, random
filler insertion) — this is an established approach in ASR
quality-estimation research, not something invented for this project.

Clean corpus: real English sentences already in this codebase — the
Phase 1 intent-classification queries and SCHEME_REGISTRY descriptions
(read-only imports) — genuine text, not fabricated.

Output: backend/ml/data/transcript_quality_dataset.csv (text,is_clean)
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.recommendation_service import SCHEME_REGISTRY  # noqa: E402

random.seed(9)

FILLER_TOKENS = ["um", "uh", "hmm", "xyz", "blah", "err", "aa", "kkk"]


def clean_corpus() -> list[str]:
    texts = [s["description"] for s in SCHEME_REGISTRY]
    texts += [f"What is {s['name']}" for s in SCHEME_REGISTRY]
    texts += [f"Am I eligible for {s['name']}" for s in SCHEME_REGISTRY]
    texts += [f"How do I apply for {s['name']} scheme" for s in SCHEME_REGISTRY]
    texts += [
        "I want to know about government schemes for farmers",
        "Please tell me the documents required for this scheme",
        "What is the annual income limit for this program",
        "Can a self employed person apply for this loan",
        "I need help understanding the eligibility criteria",
        "How much money will I receive from this scheme",
        # Broader, everyday English phrasing — not scheme-specific — so the
        # reference vocabulary/bigrams capture general fluency rather than
        # just this narrow template set. Same lesson learned twice already
        # in this build (groundedness scorer, NER): a narrow reference
        # corpus makes genuinely fine but differently-phrased text look
        # anomalous, which defeats the point of an OOV-based feature.
        "I would like to know if my family qualifies for any support",
        "Can you please help me understand how this works",
        "What documents do I need to bring with me",
        "I am not sure which option is best for my situation",
        "Could you explain that again in simpler terms",
        "My income changed recently and I want to check my eligibility",
        "I live in a small village and I am not sure where to apply",
        "Is there a deadline I need to be aware of",
        "I filled out the form but I am not sure what happens next",
        "My father is elderly and needs some financial assistance",
        "I lost my job last month and need some support",
        "We recently had a baby and want to know what help is available",
        "I am a student and looking for a scholarship",
        "Thank you for your help, I appreciate it very much",
        "Good morning, I have a question about my application",
        "Please let me know what the next steps are",
        "I visited the office but they told me to come back later",
        "How long does it usually take to process an application",
        "I do not have internet access at home, can I apply offline",
        "My neighbor told me about this scheme and I am interested",
        "Is this available in my state or only in certain regions",
        "I want to check the status of my previous application",
        "Can someone from your team call me back tomorrow",
        "I am worried I might not qualify because of my income",
        "What happens if I miss the application deadline",
        "I need this information translated into my local language",
        "Please guide me through the entire process step by step",
    ]
    return texts


def corrupt(text: str) -> str:
    words = text.split()
    if len(words) < 3:
        return text

    op = random.choice(["delete", "duplicate", "char_noise", "shuffle", "filler", "truncate"])

    if op == "delete":
        n = max(1, len(words) // 4)
        idxs = set(random.sample(range(len(words)), min(n, len(words) - 1)))
        words = [w for i, w in enumerate(words) if i not in idxs]

    elif op == "duplicate":
        i = random.randrange(len(words))
        words = words[:i] + [words[i]] * random.randint(2, 3) + words[i + 1:]

    elif op == "char_noise":
        idxs = random.sample(range(len(words)), max(1, len(words) // 3))
        for i in idxs:
            w = list(words[i])
            if len(w) > 2:
                pos = random.randrange(len(w))
                w[pos] = random.choice("aeioubcdfg")
            words[i] = "".join(w)

    elif op == "shuffle":
        mid = words[1:-1]
        random.shuffle(mid)
        words = [words[0]] + mid + [words[-1]]

    elif op == "filler":
        n = random.randint(1, 3)
        for _ in range(n):
            words.insert(random.randrange(len(words) + 1), random.choice(FILLER_TOKENS))

    elif op == "truncate":
        cut = max(1, int(len(words) * random.uniform(0.4, 0.7)))
        words = words[:cut]

    return " ".join(words)


def main():
    corpus = clean_corpus()
    rows = []
    for text in corpus:
        rows.append((text, 1))
        # 2 corrupted variants per clean sentence, for balance
        rows.append((corrupt(text), 0))
        rows.append((corrupt(text), 0))

    random.shuffle(rows)
    out_path = Path(__file__).resolve().parent / "transcript_quality_dataset.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "is_clean"])
        writer.writerows(rows)

    clean_n = sum(1 for _, y in rows if y == 1)
    print(f"Wrote {len(rows)} examples to {out_path}  ({clean_n} clean / {len(rows)-clean_n} corrupted)")


if __name__ == "__main__":
    main()
