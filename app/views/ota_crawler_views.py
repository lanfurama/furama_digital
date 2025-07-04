from django.shortcuts import render
from collections import defaultdict
from app.models import OtaReview, OtaReviewCriterion, OtaReviewScore
from app.utils import save_review_data
from datetime import datetime, timedelta
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.http import JsonResponse


def fetch_reviews():
    return OtaReview.objects.all().order_by('-created_at')

def get_score_details(current_review, compare_review=None):
    scores = OtaReviewScore.objects.filter(review=current_review).select_related('criterion')

    if compare_review is None:
        # Nếu không có compare_review, không so sánh với bất kỳ review nào trước đó
        compare_scores = []
    else:
        # Nếu có compare_review, lấy điểm số của review đó
        compare_scores = (
            OtaReviewScore.objects
            .filter(
                review__resort=current_review.resort,
                review__created_at__date=compare_review.created_at.date()
            )
            .order_by('-review__created_at')
            .values('criterion', 'value')
        )

    # Lập bản đồ điểm số từ compare_scores (nếu có)
    last_week_score_map = {
        score['criterion']: score['value']
        for score in compare_scores
    }

    result = []
    for score in scores:
        # Nếu không có điểm số trước đó, previous sẽ là 0
        previous = last_week_score_map.get(score.criterion.id, 0)
        # Tính toán sự thay đổi điểm số (delta)
        delta = round(score.value - previous, 2) if previous > 0 else 0

        # Thêm thông tin vào kết quả
        result.append({
            "criterion": score.criterion.label,
            "key": score.criterion.key,
            "value": score.value,
            "increased_value": delta if delta > 0 else 0,
            "decreased_value": abs(delta) if delta < 0 else 0,
        })
    
    return result




def process_review(current_review, compare_review):
    rating_delta = current_review.rating - compare_review.rating if compare_review else 0
    total_reviews_delta = current_review.total_reviews - compare_review.total_reviews if compare_review else 0

    return {
        "resort": current_review.resort,
        "url": current_review.url,
        "rating": current_review.rating,
        "increased_rating": round(rating_delta, 2) if rating_delta > 0 else 0,
        "decreased_rating": round(abs(rating_delta), 2) if rating_delta < 0 else 0,
        "compare_review_updated_at": compare_review.created_at.strftime("%Y-%m-%d") if compare_review else None,
        "total_reviews": current_review.total_reviews,
        "increased_total_reviews": round(total_reviews_delta, 2) if total_reviews_delta > 0 else 0,
        "decreased_total_reviews": round(abs(total_reviews_delta), 2) if total_reviews_delta < 0 else 0,
        "scores": get_score_details(current_review, compare_review),
        "updated_at": current_review.created_at.strftime("%Y-%m-%d")
    }


def get_ordered_resorts(resorts_dict, order_list):
    return sorted(
        resorts_dict.items(),
        key=lambda x: order_list.index(x[0]) if x[0] in order_list else len(order_list)
    )


def annotate_extremes(processed_reviews):
    if not processed_reviews:
        return

    highest_rating = max(processed_reviews, key=lambda x: x['rating'])['rating']
    lowest_rating = min(processed_reviews, key=lambda x: x['rating'])['rating']
    highest_total = max(processed_reviews, key=lambda x: x['total_reviews'])['total_reviews']
    lowest_total = min(processed_reviews, key=lambda x: x['total_reviews'])['total_reviews']

    criterion_scores = defaultdict(list)
    for review in processed_reviews:
        for score in review['scores']:
            criterion_scores[score['key']].append(score['value'])

    for review in processed_reviews:
        review['highest_rating'] = review['rating'] == highest_rating
        review['lowest_rating'] = review['rating'] == lowest_rating
        review['highest_total_reviews'] = review['total_reviews'] == highest_total
        review['lowest_total_reviews'] = review['total_reviews'] == lowest_total

        for score in review['scores']:
            scores_for_criterion = criterion_scores[score['key']]
            score['highest_score'] = score['value'] == max(scores_for_criterion)
            score['lowest_score'] = score['value'] == min(scores_for_criterion)


def process_source_reviews(source, resorts, order):
    processed_reviews = []
    all_created_times = []

    for resort, review_infos in get_ordered_resorts(resorts, order):
        info = review_infos[0]
        review = info['review']
        processed_reviews.append(
            process_review(info['review'], info['compare_review'])
        )
        if review.created_at:
            all_created_times.append(review.created_at)

    annotate_extremes(processed_reviews)

    criteria_keys = list(
        OtaReviewCriterion.objects
        .filter(source=source)
        .order_by('id')
        .values_list('key', flat=True)
    )

    latest_updated_time = max(all_created_times) if all_created_times else None

    return {
        "criteria_keys": criteria_keys,
        "reviews": processed_reviews,
        "latest_updated_time": latest_updated_time
    }


def get_compare_review(current_review, compare_date):
    return (
            OtaReview.objects.filter(
                url=current_review.url,
                source=current_review.source,
                created_at__date=compare_date 
            )
            .order_by('-created_at')
            .first()
    )


def get_reviews_from_db(request, source = None, base_date=None, compare_date=None):
    reviews = fetch_reviews()
    latest_updated_time = None

    preferred_order = ['hotelscombined', 'booking', 'agoda', 'expedia', 'tripadvisor', 'naver']
    all_sources = sorted(
        {review.source for review in reviews},
        key=lambda x: preferred_order.index(x) if x in preferred_order else len(preferred_order)
    )

    grouped = defaultdict(lambda: defaultdict(list))
    for review in reviews:
        compare_review = get_compare_review(review, compare_date)   
        grouped[review.source][review.resort].append({
            'review': review,
            'compare_review': compare_review
        })

    if source:
        grouped = {source: grouped.get(source, {})}
    else:
        first_source = None
        for preferred in preferred_order:
            if preferred in grouped:
                first_source = preferred
                break
        if first_source:
            grouped = {first_source: grouped[first_source]}

    # Resort order: bạn có thể dùng danh sách thủ công hoặc từ dữ liệu
    predefined_order = [
        "Furama Resort Danang",
        "Tia_Wellness_Resort",
        "Pullman_Danang",
        "Premier_Village_Danang_Resort",
        "Danang_Marriott",
        "Hyatt_Regency_Danang",
        "Naman_Retreat",
        "Sheraton_Grand_Danang",
        "Fusion_Resort_Da_Nang"
    ]

    order = predefined_order  # hoặc lấy từ dữ liệu nếu muốn dynamic

    final = {}
    for source, resorts in grouped.items():
        result = process_source_reviews(source, resorts, order)
        final[source] = result
        # Lưu latest crawl time từ từng source (lấy lớn nhất)
        if result['latest_updated_time']:
            if not latest_updated_time or result['latest_updated_time'] > latest_updated_time:
                latest_updated_time = result['latest_updated_time']

    return {
        "reviews": final,
        "available_sources": all_sources,
        "latest_updated_time": latest_updated_time,
        "base_date": base_date,
        "compare_date": compare_date
    }

# view
def ota_crawler_home(request):
    source = request.GET.get('source', 'hotelscombined')
    base_date = request.GET.get('base_date')
    compare_date = request.GET.get('compare_date')
    
    # Chuyển đổi thành datetime nếu cần
    if isinstance(base_date, str):
        base_date = datetime.strptime(base_date, "%Y-%m-%d")
    if isinstance(compare_date, str):
        compare_date = datetime.strptime(compare_date, "%Y-%m-%d")
    
    # Gọi hàm để lấy dữ liệu
    context = get_reviews_from_db(request, source, base_date, compare_date)
 
    if request.headers.get("HX-Request") == "true":
        html = render_to_string("ota_reviews/partials/content.html", context)
        return HttpResponse(html)
    
    return render(request, "ota_reviews/index.html", context)
    # return JsonResponse(context, safe=False)
