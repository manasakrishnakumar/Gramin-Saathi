from pydantic import BaseModel


class IntentClassifyRequest(BaseModel):
    query: str
    use_llm: bool = True   # False = rule-based only (fast, offline)


class IntentClassifyResponse(BaseModel):
    intent: str
    confidence: float
    method: str                      # "llm_zero_shot" | "rule_based"
    matched_keywords: list[str] = []
    reasoning: str = ""
    scheme_hints: list[str] = []
    suggested_action: str            # "eligibility_check" | "recommend" | "rag_chat"


class IntentLabelsResponse(BaseModel):
    labels: dict[str, str]
