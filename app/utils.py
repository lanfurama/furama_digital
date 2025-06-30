# app/utils.py
from app.models import OtaReview, OtaReviewCriterion, OtaReviewScore

def save_review_data(result, crawler):
    review = OtaReview.objects.create(
        resort=result["resort"],
        url=result["url"],
        source=result["source"],
        rating=result["rating"],
        total_reviews=result["total_reviews"]
    )

    scores = []
    for key, value in result["scores"].items():
        criterion, _ = OtaReviewCriterion.objects.get_or_create(
            source=result["source"],
            key=key,
            defaults={"label": key.replace("_", " ").title()}
        )
        OtaReviewScore.objects.create(
            review=review,
            criterion=criterion,
            value=value
        )
        scores.append({
            "criterion": {"key": key, "label": criterion.label},
            "value": value
        })

    return {
        "resort": result["resort"],
        "url": result["url"],
        "source": result["source"],
        "rating": result["rating"],
        "total_reviews": result["total_reviews"],
        "scores": scores
    }
