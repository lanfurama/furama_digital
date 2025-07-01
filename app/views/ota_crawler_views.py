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

@api_view(["GET"])
def crawl_hotel_reviews(request):
    # Danh sách các crawler bạn muốn sử dụng
    crawlers = [
        # HotelsCombinedCrawler(),
        # BookingCrawler()
        AgodaCrawler()
        # ExpediaCrawler()
        # TripAdvisorCrawler()
    ]
    
    results = []

    # Sử dụng ThreadPoolExecutor để cào các URL song song
    with ThreadPoolExecutor(max_workers=10) as executor:  # Bạn có thể điều chỉnh max_workers tuỳ theo yêu cầu
        futures = []
        
        # Lặp qua các crawler và các URL của chúng
        for crawler in crawlers:
            for url in crawler.urls:
                # Gọi hàm crawl() cho mỗi URL song song
                futures.append(executor.submit(crawler.crawl, url))
        
        # Chờ tất cả các task hoàn thành và xử lý kết quả
        for future in futures:
            result = future.result()
            if "error" in result:
                results.append(result)
                continue

            # # Lưu kết quả vào cơ sở dữ liệu
            # saved_data = save_review_data(result, crawler)
            # results.append(saved_data)
            results.append(result)

    return JsonResponse(results, safe=False)


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


def process_review(review, last_week_review):
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
        "updated_at": review.created_at.strftime("%Y-%m-%d"),
    }


# def get_reviews_from_db(request):
#     reviews = fetch_reviews()

#     # Group by source and resort
#     grouped = defaultdict(lambda: defaultdict(list))
#     for review in reviews:
#         last_week_review = get_last_week_review(review)
#         grouped[review.source][review.resort].append({
#             'review': review,
#             'last_week_review': last_week_review
#         })

#     order = [
#         "Furama_Resort_Danang",
#         "Tia_Wellness_Resort",
#         "Pullman_Danang",
#         "Premier_Village_Danang_Resort",
#         "Danang_Marriott",
#         "Hyatt_Regency_Danang",
#         "Naman_Retreat",
#         "Sheraton_Grand_Danang",
#         "Fusion_Resort_Da_Nang"
#     ]

#     final = {}

#     for source, resorts in grouped.items():
#         sorted_resorts = sorted(
#             resorts.items(),
#             key=lambda x: order.index(x[0]) if x[0] in order else len(order)
#         )

#         final[source] = []
#         for resort, review_infos in sorted_resorts:
#             info = review_infos[0]
#             final[source].append(

#                 process_review(info['review'], info['last_week_review'])
#             )

#     return final

def get_reviews_from_db(request):
    reviews = fetch_reviews()

    grouped = defaultdict(lambda: defaultdict(list))
    for review in reviews:
        last_week_review = get_last_week_review(review)
        grouped[review.source][review.resort].append({
            'review': review,
            'last_week_review': last_week_review
        })

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

    return final


def ota_crawler_home(request):
    data = get_reviews_from_db(request)
    return render(request, "ota_crawler/index.html", {'data': data})
    # return JsonResponse(data, safe=False)
