# views/ota_crawler_views.py
from django.shortcuts import render
from datetime import timedelta
from django.utils import timezone
from concurrent.futures import ThreadPoolExecutor
from django.db.models import Avg
from rest_framework.decorators import api_view
from django.http import JsonResponse
from app.ota_crawlers.hotelscombined import HotelsCombinedCrawler
from app.ota_crawlers.booking import BookingCrawler
from app.ota_crawlers.agoda import AgodaCrawler
from app.ota_crawlers.expedia import ExpediaCrawler
from app.ota_crawlers.tripadvisor import TripAdvisorCrawler
from app.models import OtaReview, OtaReviewCriterion, OtaReviewScore
from app.utils import save_review_data
from collections import defaultdict


def fetch_reviews():
    return OtaReview.objects.all().order_by('-created_at')


def get_last_week_review(current_review):
    return (
        OtaReview.objects.filter(
            url=current_review.url,
            source=current_review.source,
            created_at__lt=current_review.created_at
        )
        .order_by('-created_at')
        .first()
    )


def get_score_details(review):
    scores = OtaReviewScore.objects.filter(review=review).select_related('criterion')

    last_week_scores = (
        OtaReviewScore.objects
        .filter(review__resort=review.resort, review__created_at__lt=review.created_at)
        .order_by('-review__created_at')
        .values('criterion', 'value')
    )

    last_week_score_map = {
        score['criterion']: score['value']
        for score in last_week_scores
    }

    result = []

    for score in scores:
        previous = last_week_score_map.get(score.criterion.id, 0)
        delta = round(score.value - previous, 2) if previous > 0 else 0

        result.append({
            "criterion": score.criterion.label,
            "key": score.criterion.key,
            "value": score.value,
            "increased_value": delta if delta > 0 else 0,
            "decreased_value": abs(delta) if delta < 0 else 0,
        })
    return result


def process_review(review, last_week_review, highest_rating=None, lowest_rating=None, highest_total_reviews=None, lowest_total_reviews=None):
    rating_delta = review.rating - last_week_review.rating if last_week_review else 0
    total_reviews_delta = review.total_reviews - last_week_review.total_reviews if last_week_review else 0

    return {
        "resort": review.resort.name if hasattr(review.resort, 'name') else str(review.resort),
        "url": review.url,
        "rating": review.rating,
        "increased_rating": round(rating_delta, 2) if rating_delta > 0 else 0,
        "decreased_rating": round(abs(rating_delta), 2) if rating_delta < 0 else 0,
        "last_week_review_updated_at": last_week_review.created_at.strftime("%Y-%m-%d") if last_week_review else None,
        "total_reviews": review.total_reviews,
        "increased_total_reviews": round(total_reviews_delta, 2) if total_reviews_delta > 0 else 0,
        "decreased_total_reviews": round(abs(total_reviews_delta), 2) if total_reviews_delta < 0 else 0,
        "scores": get_score_details(review),
        "updated_at": review.created_at.strftime("%Y-%m-%d")
    }

def get_reviews_from_db(request):
    source_param = request.GET.get('source', None)
    reviews = fetch_reviews()

    # Extract sources from reviews (unique sources only)
    available_sources = list({review.source for review in reviews})

    # If no source is provided, set the first source from the available sources as default
    if not source_param and available_sources:
        source_param = available_sources[0]

    grouped = defaultdict(lambda: defaultdict(list))
    for review in reviews:
        last_week_review = get_last_week_review(review)
        grouped[review.source][review.resort].append({
            'review': review,
            'last_week_review': last_week_review
        })
    
    # If the source param is provided, only process that source
    if source_param:
        grouped = {source_param: grouped.get(source_param, {})}

    order = [
        "Furama_Resort_Danang",
        "Tia_Wellness_Resort",
        "Pullman_Danang",
        "Premier_Village_Danang_Resort",
        "Danang_Marriott",
        "Hyatt_Regency_Danang",
        "Naman_Retreat",
        "Sheraton_Grand_Danang",
        "Fusion_Resort_Da_Nang"
    ]

    final = {}

    for source, resorts in grouped.items():
        sorted_resorts = sorted(
            resorts.items(),
            key=lambda x: order.index(x[0]) if x[0] in order else len(order)
        )

        processed_reviews = []
        for resort, review_infos in sorted_resorts:
            info = review_infos[0]
            processed_reviews.append(
                process_review(info['review'], info['last_week_review'])
            )

        # Tính toán highest_rating, lowest_rating, highest_total_reviews, lowest_total_reviews sau khi đã xử lý xong reviews
        highest_rating = max(processed_reviews, key=lambda x: x['rating'])['rating'] if processed_reviews else None
        lowest_rating = min(processed_reviews, key=lambda x: x['rating'])['rating'] if processed_reviews else None
        highest_total_reviews = max(processed_reviews, key=lambda x: x['total_reviews'])['total_reviews'] if processed_reviews else None
        lowest_total_reviews = min(processed_reviews, key=lambda x: x['total_reviews'])['total_reviews'] if processed_reviews else None

        criterion_scores = defaultdict(list)    

        # Thu thập tất cả các scores theo từng criterion
        for review_info in processed_reviews:
            for score in review_info['scores']:
                criterion_scores[score['key']].append(score['value'])

        # Thêm các giá trị này vào dict mỗi resort
        for review_info in processed_reviews:
            review_info['highest_rating'] = review_info['rating'] == highest_rating
            review_info['lowest_rating'] = review_info['rating'] == lowest_rating
            review_info['highest_total_reviews'] = review_info['total_reviews'] == highest_total_reviews
            review_info['lowest_total_reviews'] = review_info['total_reviews'] == lowest_total_reviews

            for score in review_info['scores']:
                # Lấy danh sách tất cả các score cho criterion này
                all_scores_for_criterion = criterion_scores[score['key']]
                
                # Tìm giá trị max và min cho criterion
                highest_score_value = max(all_scores_for_criterion) if all_scores_for_criterion else None
                lowest_score_value = min(all_scores_for_criterion) if all_scores_for_criterion else None
                
                # Gán highest_score và lowest_score cho từng score trong review_info
                score['highest_score'] = score['value'] == highest_score_value
                score['lowest_score'] = score['value'] == lowest_score_value

        # chỉ cần lấy criteria_keys một lần cho mỗi source
        criteria_keys = list(
            OtaReviewCriterion.objects
            .filter(source=source)
            .order_by('id')
            .values_list('key', flat=True)
        )

        final[source] = {
            "criteria_keys": criteria_keys,
            "reviews": processed_reviews
        }

    return {
        "reviews": final,
        "available_sources": available_sources
    }


def ota_crawler_home(request):
    data = get_reviews_from_db(request)
    # Unpack the data into final and available_sources
    reviews = data['reviews']
    available_sources = data['available_sources']
    return render(request, "ota_crawler/index.html", {'reviews': reviews, 'available_sources': available_sources})
    # return JsonResponse(data, safe=False) 
