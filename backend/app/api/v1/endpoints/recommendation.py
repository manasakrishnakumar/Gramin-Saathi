from fastapi import APIRouter
from app.schemas.recommendation import (
    ProfileRequest,
    RecommendationResponse,
    SchemeRecommendation,
    CriterionDetail,
    ProfileSummary,
    SchemeListItem,
    ProfileFieldsResponse,
)
from app.services.recommendation_service import recommendation_service, SCHEME_REGISTRY
from app.services.ml_ranker_service import ml_ranker_service

router = APIRouter()


def _match_label(score_pct: float, is_disqualified: bool) -> str:
    if is_disqualified:
        return "Not Eligible"
    if score_pct >= 90:
        return "Excellent Match"
    if score_pct >= 70:
        return "Good Match"
    if score_pct >= 50:
        return "Partial Match"
    return "Low Match"


@router.post("/schemes", response_model=RecommendationResponse, summary="Get personalised scheme recommendations")
async def recommend_schemes(request: ProfileRequest):
    """
    Accepts a user profile and returns government schemes ranked by
    rule-based eligibility score (weighted criteria matching).

    No ML inference — pure deterministic rule evaluation.
    Explainability is built-in: every matched/missed criterion is surfaced.
    """
    profile = recommendation_service.profile_from_dict(request.model_dump())
    results = recommendation_service.score_schemes(
        profile,
        top_n=request.top_n,
        min_score_pct=request.min_score_pct,
    )
    summary = recommendation_service.profile_summary(profile)

    recommendations = []
    for r in results:
        matched = [
            CriterionDetail(
                label=c.label,
                field=c.field,
                matched=c.matched,
                weight=c.weight,
                is_hard=c.is_hard,
                actual_value=c.actual_value,
                required_value=c.required_value,
            )
            for c in r.matched_criteria
        ]
        missed = [
            CriterionDetail(
                label=c.label,
                field=c.field,
                matched=c.matched,
                weight=c.weight,
                is_hard=c.is_hard,
                actual_value=c.actual_value,
                required_value=c.required_value,
            )
            for c in r.missed_criteria
        ]

        # ML re-ranking (ml/train_ranker_bootstrap.py, trained model) — this
        # score NEVER decides eligibility; it only predicts how likely a
        # user is to engage with an already rule-eligible scheme, used
        # below to reorder (not filter) the list. Disqualified/zero-score
        # schemes are never scored or reordered by it.
        ml_score = None
        if ml_ranker_service.is_ready and not r.is_disqualified and r.score_pct > 0:
            ml_score = ml_ranker_service.score(
                profile=request.model_dump(),
                scheme_result={
                    "rule_score_pct": r.score_pct,
                    "matched_count": len(r.matched_criteria),
                    "missed_count": len(r.missed_criteria),
                },
            )

        recommendations.append(
            SchemeRecommendation(
                scheme_id=r.scheme_id,
                name=r.name,
                ministry=r.ministry,
                description=r.description,
                apply_url=r.apply_url,
                score_pct=r.score_pct,
                is_disqualified=r.is_disqualified,
                matched_criteria=matched,
                missed_criteria=missed,
                match_label=_match_label(r.score_pct, r.is_disqualified),
                ml_engagement_score=ml_score,
            )
        )

    total_eligible = sum(1 for r in results if not r.is_disqualified and r.score_pct > 0)

    # Reorder only the already rule-eligible schemes by the trained ranker's
    # score; disqualified/zero-score schemes keep their existing (tail)
    # position exactly as the rule engine placed them.
    ranking_method = "rule_engine"
    if ml_ranker_service.is_ready:
        eligible = [rec for rec in recommendations if rec.ml_engagement_score is not None]
        ineligible = [rec for rec in recommendations if rec.ml_engagement_score is None]
        eligible.sort(key=lambda rec: rec.ml_engagement_score, reverse=True)
        recommendations = eligible + ineligible
        ranking_method = "ml_reranked"

    return RecommendationResponse(
        profile_summary=ProfileSummary(**summary),
        total_eligible=total_eligible,
        recommendations=recommendations,
        ranking_method=ranking_method,
    )


@router.get("/schemes/list", response_model=list[SchemeListItem], summary="List all available schemes")
async def list_schemes():
    """Returns all schemes in the registry with basic info."""
    return [
        SchemeListItem(
            scheme_id=s["id"],
            name=s["name"],
            ministry=s["ministry"],
            description=s["description"],
        )
        for s in SCHEME_REGISTRY
    ]


@router.get("/profile/fields", response_model=ProfileFieldsResponse, summary="Get profile field options")
async def get_profile_fields():
    """Returns valid option values for each profile field — for building frontend forms."""
    return ProfileFieldsResponse(
        occupations=["farmer", "student", "self_employed", "salaried", "daily_wage", "unemployed", "other"],
        genders=["male", "female", "transgender", "other"],
        categories=["general", "obc", "sc", "st"],
        education_levels=["none", "primary", "secondary", "graduate", "postgraduate"],
        marital_statuses=["single", "married", "widowed", "divorced"],
    )
