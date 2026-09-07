"""
intent_service.py
Intent Classification for Gramin Saathi chat queries.

No training data, no TF-IDF+LR, no fine-tuning.

Two classifiers, combined:
  1. LLM zero-shot/few-shot classification (PRIMARY)
     - Reuses the existing Gemini LLM already configured in RAGService.
     - A single strict prompt lists the intent taxonomy + one-line
       definitions + a handful of labelled examples, and asks Gemini to
       return one JSON object. No fine-tuning, inference-only.
  2. Rule-based keyword classifier (FALLBACK)
     - Fast, fully offline, deterministic. Used when the LLM call fails
       (no API key, quota, network) or times out, and as the classifier
       for latency-sensitive call sites that can't afford an extra Gemini
       round-trip (e.g. per-message chat-step enrichment).

Output feeds:
  - POST /api/v1/intent/classify — standalone endpoint for the frontend
    to decide which surface to route a query to (chat / recommend / eligibility).
  - rag_service.stream_query — tags each chat turn with a detected intent
    (rule-based, fast path) so the UI can show a contextual CTA
    ("See your personalised recommendations" / "Check eligibility for
    this scheme") alongside the normal RAG answer.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Intent taxonomy
# ---------------------------------------------------------------------------

INTENT_LABELS: dict[str, str] = {
    "eligibility_check": "User asks whether they personally qualify / are eligible for a specific scheme.",
    "scheme_recommendation": "User wants scheme suggestions tailored to their profile (age, income, occupation, etc.) without naming one scheme.",
    "application_process": "User asks how to apply, what documents are needed, or the steps/deadlines to apply for a scheme.",
    "scheme_information": "User wants general information — benefits, purpose, ministry — about a scheme, not personal eligibility.",
    "greeting_identity": "Greeting, small talk, or asking who/what the assistant is.",
    "general_query": "Anything else — off-topic or doesn't fit the categories above.",
}

# Maps an intent to the API surface the frontend should route to.
SUGGESTED_ACTION: dict[str, str] = {
    "eligibility_check": "eligibility_check",   # POST /api/v1/eligibility/check
    "scheme_recommendation": "recommend",       # POST /api/v1/recommend/schemes
    "application_process": "rag_chat",          # answered inline, RAG has the how-to-apply steps
    "scheme_information": "rag_chat",
    "greeting_identity": "rag_chat",
    "general_query": "rag_chat",
}


# ---------------------------------------------------------------------------
# Rule-based keyword classifier (fallback / fast path)
# ---------------------------------------------------------------------------

# Ordered so more specific intents are checked before generic ones.
KEYWORD_RULES: dict[str, list[str]] = {
    "eligibility_check": [
        "am i eligible", "eligible for", "do i qualify", "qualify for",
        "am i entitled", "check my eligibility", "eligibility for",
        "will i get", "do i get", "can i avail", "eligibility criteria for",
        # transliterated Hindi
        "patrata", "kya main paatr", "milega kya", "milegi kya",
    ],
    "scheme_recommendation": [
        "recommend", "which scheme", "which schemes", "suggest a scheme",
        "suggest scheme", "suitable scheme", "best scheme for me",
        "schemes for me", "what scheme should i", "what schemes can i apply",
        "schemes suitable for", "schemes based on my",
        "konsi yojana", "kaunsi yojana", "yojana suggest",
    ],
    "application_process": [
        "how to apply", "how do i apply", "application process",
        "documents required", "documents needed", "steps to apply",
        "where to apply", "apply online", "registration process",
        "how can i apply", "kaise apply", "avedan kaise", "kaise avedan",
    ],
    "scheme_information": [
        "what is", "tell me about", "benefits of", "details of",
        "information about", "explain", "kya hai",
    ],
    "greeting_identity": [
        "who are you", "what are you", "your name", "who created you",
        "your purpose", "hello", "hi ", "hey", "namaste", "vanakkam",
        "good morning", "good afternoon", "good evening",
    ],
}


@dataclass
class IntentResult:
    intent: str
    confidence: float           # 0–1
    method: str                 # "llm_zero_shot" | "rule_based"
    matched_keywords: list[str] = field(default_factory=list)
    reasoning: str = ""
    scheme_hints: list[str] = field(default_factory=list)
    suggested_action: str = "rag_chat"


def _classify_rule_based(query: str) -> IntentResult:
    """
    Deterministic keyword-count classifier. Offline, no model calls.
    Confidence grows with the number of distinct keyword hits for the
    winning intent (1 hit ≈ 0.4, 2 ≈ 0.6, 3+ ≈ 0.8, capped).
    """
    q = f" {query.lower().strip()} "

    best_intent = "general_query"
    best_hits: list[str] = []

    for intent, phrases in KEYWORD_RULES.items():
        hits = [p for p in phrases if p in q]
        if len(hits) > len(best_hits):
            best_intent = intent
            best_hits = hits

    if not best_hits:
        return IntentResult(
            intent="general_query",
            confidence=0.3,
            method="rule_based",
            matched_keywords=[],
            reasoning="No keyword rule matched — defaulted to general_query.",
            suggested_action=SUGGESTED_ACTION["general_query"],
        )

    confidence = min(0.4 + 0.2 * (len(best_hits) - 1), 0.85)
    return IntentResult(
        intent=best_intent,
        confidence=round(confidence, 2),
        method="rule_based",
        matched_keywords=best_hits,
        reasoning=f"Matched {len(best_hits)} keyword pattern(s) for '{best_intent}'.",
        suggested_action=SUGGESTED_ACTION[best_intent],
    )


# ---------------------------------------------------------------------------
# LLM zero-shot / few-shot classifier (primary)
# ---------------------------------------------------------------------------

_FEW_SHOT_EXAMPLES = """\
Examples:
Query: "Am I eligible for PM-KISAN?"
{"intent": "eligibility_check", "confidence": 0.95, "reasoning": "Asks personally about qualifying for a named scheme."}

Query: "Which government schemes can I apply for? I'm a farmer earning 1.5 lakh a year."
{"intent": "scheme_recommendation", "confidence": 0.9, "reasoning": "Wants suggestions matched to their profile, no single scheme named."}

Query: "What documents do I need for Ayushman Bharat and how do I apply?"
{"intent": "application_process", "confidence": 0.92, "reasoning": "Asks about documents and application steps."}

Query: "What is PM Awas Yojana?"
{"intent": "scheme_information", "confidence": 0.88, "reasoning": "Wants general information, not a personal eligibility check."}

Query: "Hi, who are you?"
{"intent": "greeting_identity", "confidence": 0.99, "reasoning": "Greeting plus identity question."}

Query: "What's the weather today?"
{"intent": "general_query", "confidence": 0.9, "reasoning": "Unrelated to government schemes."}
"""

_INTENT_PROMPT_TEMPLATE = """You are an intent classifier for "Gramin Saathi", a government-schemes assistant.
Classify the user's query into EXACTLY ONE of these intents:

{labels}

{examples}

Return ONLY a single-line JSON object with keys "intent", "confidence" (0-1 float), "reasoning" (max 15 words).
No markdown, no code fences, no extra text.

Query: "{query}"
"""


def _build_prompt(query: str) -> str:
    labels = "\n".join(f"- {name}: {desc}" for name, desc in INTENT_LABELS.items())
    return _INTENT_PROMPT_TEMPLATE.format(labels=labels, examples=_FEW_SHOT_EXAMPLES, query=query.replace('"', "'"))


def _parse_llm_json(raw_text: str) -> dict | None:
    """Extract the first {...} JSON object from the LLM's raw text response."""
    text = raw_text.strip()
    # Strip common markdown code-fence wrapping
    text = re.sub(r"^```(json)?", "", text.strip(), flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text.strip()).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def _classify_llm(query: str) -> IntentResult:
    """
    Zero-shot classification via the existing Gemini LLM (inference-only,
    no fine-tuning). Raises on any failure so the caller can fall back
    to the rule-based classifier.
    """
    # Local import to avoid a circular import (rag_service also imports
    # this module for chat-turn intent tagging).
    from app.services.rag_service import rag_service

    prompt = _build_prompt(query)
    response = rag_service.llm.complete(prompt)
    parsed = _parse_llm_json(response.text)

    if not parsed or "intent" not in parsed:
        raise ValueError(f"Could not parse intent JSON from LLM response: {response.text[:200]!r}")

    intent = str(parsed["intent"]).strip()
    if intent not in INTENT_LABELS:
        raise ValueError(f"LLM returned unknown intent label: {intent!r}")

    confidence = float(parsed.get("confidence", 0.7))
    confidence = max(0.0, min(1.0, confidence))

    return IntentResult(
        intent=intent,
        confidence=round(confidence, 2),
        method="llm_zero_shot",
        matched_keywords=[],
        reasoning=str(parsed.get("reasoning", ""))[:200],
        suggested_action=SUGGESTED_ACTION.get(intent, "rag_chat"),
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class IntentService:

    def classify_fast(self, query: str) -> IntentResult:
        """
        Rule-based only. Offline, sub-millisecond. Use at call sites that
        can't afford an extra LLM round-trip (e.g. per chat-turn tagging).
        """
        result = _classify_rule_based(query)
        result.scheme_hints = self._scheme_hints(query)
        return result

    def classify(self, query: str, use_llm: bool = True) -> IntentResult:
        """
        Full classification: LLM zero-shot is primary, rule-based keyword
        matching is the fallback if the LLM call fails or is disabled.
        """
        if not query or not query.strip():
            return IntentResult(
                intent="general_query", confidence=0.0, method="rule_based",
                reasoning="Empty query.", suggested_action="rag_chat",
            )

        result: IntentResult
        if use_llm:
            try:
                result = _classify_llm(query)
            except Exception as e:
                logger.warning(f"LLM intent classification failed, falling back to rule-based: {e}")
                result = _classify_rule_based(query)
        else:
            result = _classify_rule_based(query)

        result.scheme_hints = self._scheme_hints(query)
        return result

    @staticmethod
    def _scheme_hints(query: str) -> list[str]:
        # Reuse the scheme-name pattern matcher already built for multilingual RAG.
        from app.services.multilingual_service import multilingual_service
        return multilingual_service.expander.extract_scheme_hints(query)

    def result_to_dict(self, result: IntentResult) -> dict:
        return {
            "intent": result.intent,
            "confidence": result.confidence,
            "method": result.method,
            "matched_keywords": result.matched_keywords,
            "reasoning": result.reasoning,
            "scheme_hints": result.scheme_hints,
            "suggested_action": result.suggested_action,
        }


# Singleton
intent_service = IntentService()
