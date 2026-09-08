"""
generate_intent_dataset.py — Phase 1

Builds a synthetic, labeled dataset for training a real intent classifier,
without needing any paid LLM calls or real user logs.

Approach: template-based generation. For each intent label already defined
in `app.services.intent_service.INTENT_LABELS` (read-only import — nothing
in that file is touched), fill a set of natural-language templates with
real scheme names pulled from `app.services.recommendation_service.
SCHEME_REGISTRY` (also read-only) and plausible profile values, producing
a diverse labeled corpus.

This is weak/synthetic supervision, not real usage data — see
backend/ml/README.md for how this fits into the overall plan and how to
replace it with real labels once Phase 0 events accumulate.

Output: backend/ml/data/intent_dataset.csv  (columns: text,label)
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

# Make `app.*` importable when this script is run directly
# (backend/ml/data/generate_intent_dataset.py -> backend/ is two levels up).
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.recommendation_service import SCHEME_REGISTRY  # noqa: E402

random.seed(42)

SCHEME_NAMES = [s["name"] for s in SCHEME_REGISTRY]
OCCUPATIONS = ["farmer", "student", "self-employed person", "daily wage worker", "unemployed person", "salaried employee"]
CATEGORIES = ["SC", "ST", "OBC", "general category"]
AGES = [19, 24, 28, 35, 42, 55, 61, 68]
INCOMES = ["50,000", "1.2 lakh", "2.5 lakh", "3 lakh", "6 lakh"]

TEMPLATES: dict[str, list[str]] = {
    "eligibility_check": [
        "Am I eligible for {scheme}?",
        "Do I qualify for {scheme}",
        "Can I get {scheme} benefits",
        "Will I be entitled to {scheme}",
        "Check my eligibility for {scheme}",
        "Is a {occupation} eligible for {scheme}",
        "Can a {age} year old apply for {scheme}",
        "Am I eligible for {scheme} if my income is {income}",
        "Does {category} qualify for {scheme}",
        "kya main {scheme} ke liye patra hoon",
        "mujhe {scheme} milega kya",
    ],
    "scheme_recommendation": [
        "Which schemes can I apply for as a {occupation}?",
        "What government schemes suit a {age} year old {occupation}",
        "Suggest schemes for someone earning {income} a year",
        "Best scheme for {category} farmers",
        "Recommend schemes for me",
        "Which yojana is suitable for a {occupation}",
        "What schemes am I eligible for",
        "Suggest a scheme for a {occupation} earning {income}",
        "konsi yojana meri liye sahi hai",
        "mere liye kaunsi sarkari yojana theek hai",
    ],
    "application_process": [
        "How do I apply for {scheme}?",
        "What documents are needed for {scheme}",
        "Steps to apply for {scheme}",
        "Where can I submit the application for {scheme}",
        "How can I register for {scheme}",
        "What is the application process for {scheme}",
        "Documents required for {scheme}",
        "{scheme} ke liye kaise apply karen",
        "avedan kaise karen {scheme} ke liye",
    ],
    "scheme_information": [
        "What is {scheme}?",
        "Tell me about {scheme}",
        "Explain the benefits of {scheme}",
        "Details about {scheme}",
        "What does {scheme} provide",
        "Give me information on {scheme}",
        "{scheme} kya hai",
    ],
    "greeting_identity": [
        "Hi", "Hi!", "hi there", "Hello", "Hello!", "Hello there", "hey", "Hey!",
        "Hey there", "Good morning", "Good morning!", "Good afternoon",
        "Good evening", "Namaste", "Namaste!", "Vanakkam", "Who are you?",
        "who are you", "What are you?", "what are you exactly", "What is your name",
        "what's your name", "Who created you", "who made you",
        "What can you help me with", "what do you do", "Hiya", "Yo",
    ],
    "general_query": [
        "What's the weather today?", "how's the weather", "will it rain today",
        "Tell me a joke", "tell me something funny", "make me laugh",
        "What's the capital of France", "what's the capital of Japan",
        "How do I cook rice", "how do I make tea", "best recipe for biryani",
        "What time is it", "what's today's date",
        "Recommend a good movie", "suggest a good book to read",
        "What's 2 plus 2", "what's 15 times 3",
        "How far is the moon", "how big is the sun",
        "Play some music", "play a song",
        "What's the score of yesterday's match", "who won the cricket match",
        "tell me about black holes", "what is quantum physics",
        "how do airplanes fly", "translate hello to french",
    ],
}


def fill(template: str) -> str:
    return template.format(
        scheme=random.choice(SCHEME_NAMES),
        occupation=random.choice(OCCUPATIONS),
        category=random.choice(CATEGORIES),
        age=random.choice(AGES),
        income=random.choice(INCOMES),
    )


def generate(samples_per_template: int = 6) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for label, templates in TEMPLATES.items():
        for template in templates:
            n = samples_per_template if "{" in template else 1  # fixed strings need no repeats
            seen = set()
            attempts = 0
            while len(seen) < n and attempts < n * 5:
                text = fill(template)
                attempts += 1
                if text not in seen:
                    seen.add(text)
                    rows.append((text, label))
    random.shuffle(rows)
    return rows


def main():
    rows = generate()
    out_path = Path(__file__).resolve().parent / "intent_dataset.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "label"])
        writer.writerows(rows)

    counts: dict[str, int] = {}
    for _, label in rows:
        counts[label] = counts.get(label, 0) + 1

    print(f"Wrote {len(rows)} synthetic examples to {out_path}")
    for label, n in sorted(counts.items()):
        print(f"  {label:24s} {n}")


if __name__ == "__main__":
    main()
