# app/utils.py
from app.models import OtaReview, OtaReviewCriterion, OtaReviewScore
from django.db import IntegrityError
from datetime import datetime


def save_review_data(result, crawler):
    # Kiểm tra nếu review đã tồn tại dựa trên url và resort
    today = datetime.today().date()
    review = OtaReview.objects.filter(url=result["url"], source=result["source"]).first()
    
    if review and review.created_at.date() == today:
        return {
            "resort": result["resort"],
            "url": result["url"],
            "source": result["source"],
            "rating": result["rating"],
            "total_reviews": result["total_reviews"],
            "scores": []  # Không cần scores vì không cập nhật
        }

    # Nếu không có review hoặc không có updated_date, tạo mới
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
