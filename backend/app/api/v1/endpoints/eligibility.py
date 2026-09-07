from fastapi import APIRouter, HTTPException
from app.schemas.eligibility import (
    EligibilityRequest,
    BulkEligibilityRequest,
    EligibilityResponse,
    BulkEligibilityResponse,
    BulkEligibilityItem,
    CriterionEligibilityDetail,
)
from app.services.eligibility_service import eligibility_service, EligibilityVerdict
from app.services.recommendation_service import recommendation_service

router = APIRouter()


def _verdict_to_response(v: EligibilityVerdict) -> EligibilityResponse:
    def _map_criterion(c):
        return CriterionEligibilityDetail(
            label=c.label,
            field=c.field,
            matched=c.matched,
            weight=c.weight,
            is_hard=c.is_hard,
            actual_value=c.actual_value,
            required_value=c.required_value,
            fix_suggestion=c.fix_suggestion,
            documents_for_criterion=c.documents_for_criterion,
        )

    return EligibilityResponse(
        scheme_id=v.scheme_id,
        scheme_name=v.scheme_name,
        ministry=v.ministry,
        description=v.description,
        apply_url=v.apply_url,
        verdict=v.verdict,
        eligibility_pct=v.eligibility_pct,
        confidence=v.confidence,
        is_eligible=v.is_eligible,
        blocking_criteria=[_map_criterion(c) for c in v.blocking_criteria],
        soft_gaps=[_map_criterion(c) for c in v.soft_gaps],
        passed_criteria=[_map_criterion(c) for c in v.passed_criteria],
        documents_required=v.documents_required,
        next_steps=v.next_steps,
        what_if_suggestions=v.what_if_suggestions,
    )


@router.post(
    "/check",
    response_model=EligibilityResponse,
    summary="Check eligibility for a specific scheme",
)
async def check_eligibility(request: EligibilityRequest):
    """
    Deep deterministic eligibility analysis for ONE scheme.

    Returns:
    - Hard verdict: Fully Eligible / Conditionally Eligible / Not Eligible
    - Exactly which criteria pass / fail
    - Blocking reasons (hard disqualifiers) with actionable fix suggestions
    - Soft gaps with improvement hints
    - Full document checklist
    - Ordered next steps
    - What-if gap analysis
    """
    profile = recommendation_service.profile_from_dict(request.model_dump())
    verdict = eligibility_service.predict(profile, request.scheme_id)

    if verdict is None:
        raise HTTPException(
            status_code=404,
            detail=f"Scheme '{request.scheme_id}' not found. "
                   f"Use GET /api/v1/recommend/schemes/list to see valid scheme IDs.",
        )

    return _verdict_to_response(verdict)


@router.post(
    "/check-all",
    response_model=BulkEligibilityResponse,
    summary="Check eligibility across ALL schemes",
)
async def check_all_eligibility(request: BulkEligibilityRequest):
    """
    Run eligibility prediction for every scheme in the registry.
    Returns a compact summary sorted by: eligible first, then by score descending.
    Use POST /eligibility/check with a specific scheme_id for the full detail view.
    """
    profile = recommendation_service.profile_from_dict(request.model_dump())
    verdicts = eligibility_service.check_all(profile)

    items = [
        BulkEligibilityItem(
            scheme_id=v.scheme_id,
            scheme_name=v.scheme_name,
            verdict=v.verdict,
            eligibility_pct=v.eligibility_pct,
            is_eligible=v.is_eligible,
            blocking_count=len(v.blocking_criteria),
            soft_gap_count=len(v.soft_gaps),
        )
        for v in verdicts
    ]

    return BulkEligibilityResponse(
        total_eligible=sum(1 for v in verdicts if v.is_eligible),
        total_not_eligible=sum(1 for v in verdicts if not v.is_eligible),
        results=items,
    )
