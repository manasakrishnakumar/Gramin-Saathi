from fastapi import APIRouter, HTTPException
from app.schemas.intent import IntentClassifyRequest, IntentClassifyResponse, IntentLabelsResponse
from app.services.intent_service import intent_service, INTENT_LABELS

router = APIRouter()


@router.post("/classify", response_model=IntentClassifyResponse, summary="Classify a chat query's intent")
async def classify_intent(request: IntentClassifyRequest):
    """
    Classifies a free-text query into one of: eligibility_check,
    scheme_recommendation, application_process, scheme_information,
    greeting_identity, general_query.

    LLM zero-shot classification (Gemini) is primary; a rule-based
    keyword matcher is used automatically if the LLM call fails, or
    directly if `use_llm=false`.

    No training data or fine-tuning involved — inference-only.
    """
    try:
        result = intent_service.classify(request.query, use_llm=request.use_llm)
        return IntentClassifyResponse(**intent_service.result_to_dict(result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/labels", response_model=IntentLabelsResponse, summary="List supported intent labels")
async def list_intent_labels():
    """Returns the intent taxonomy with one-line definitions — for building frontend UX."""
    return IntentLabelsResponse(labels=INTENT_LABELS)
