from django.shortcuts import render
from collections import defaultdict
from app.models import OtaReview, OtaReviewCriterion, OtaReviewScore
from app.utils import save_review_data
from django.http import JsonResponse
from datetime import datetime


def fetch_reviews():
    return OtaReview.objects.all().order_by('-created_at')


def get_compare_review(current_review, base_date=None, compare_date=None):
    query = OtaReview.objects.filter(
        url=current_review.url,
        source=current_review.source
    )
    if compare_date:
        query = query.filter(created_at__date=compare_date)

    return query.order_by('-created_at').first()


def get_score_details(current_review, compare_review):
    current_scores = {
        s.criterion.id: s for s in OtaReviewScore.objects.filter(review=current_review).select_related('criterion')
    }
    prev_scores = {}
    if compare_review:
        prev_scores = {
            s.criterion.id: s for s in OtaReviewScore.objects.filter(review=compare_review).select_related('criterion')
        }

    result = []
    for crit_id, score in current_scores.items():
        prev = prev_scores.get(crit_id)
        prev_value = prev.value if prev else 0
        delta = round(score.value - prev_value, 2) if prev_value > 0 else 0
        result.append({
            "criterion": score.criterion.label,
            "key": score.criterion.key,
            "value": score.value,
            "increased_value": delta if delta > 0 else 0,
            "decreased_value": abs(delta) if delta < 0 else 0,
        })
    return result


def process_review(review, compare_review, base_date=None, compare_date=None):
    """Build dict review sau khi xử lý."""
    predefined_order = [
        "Furama Resort",
        "TIA",
        "Pullman",
        "Premier",
        "Marriott",
        "Hyatt",
        "Naman",
        "Sheraton",
        "Fusion",
        "Furama Villas",
    ]

    display_resort = normalize_resort_name(review.resort, predefined_order)

    if review.rating is not None and compare_review and compare_review.rating is not None:
        # Nếu có rating so sánh, tính delta
        rating_delta = review.rating - compare_review.rating
    else:
        # Nếu không có review so sánh, delta là 0
        rating_delta = 0
    # Nếu có review so sánh, tính tổng số lượng review delta
    if review.total_reviews is not None and compare_review and compare_review.total_reviews is not None:
        total_reviews_delta = review.total_reviews - compare_review.total_reviews
    else:
        # Nếu không có review so sánh, delta là 0
        total_reviews_delta = 0

    scores = get_score_details(review, compare_review)

    return {
        "resort": display_resort,
        "url": review.url,
        "rating": review.rating,
        "increased_rating": round(rating_delta, 2) if rating_delta > 0 else 0,
        "decreased_rating": round(abs(rating_delta), 2) if rating_delta < 0 else 0,
        "current_review_updated_at": review.created_at.strftime("%Y-%m-%d"),
        "compare_review_updated_at": compare_review.created_at.strftime("%Y-%m-%d") if compare_review else None,
        "total_reviews": review.total_reviews,
        "increased_total_reviews": round(total_reviews_delta, 2) if total_reviews_delta > 0 else 0,
        "decreased_total_reviews": round(abs(total_reviews_delta), 2) if total_reviews_delta < 0 else 0,
        "scores": scores,
        "scores_dict": {score['key']: score for score in scores},
        "updated_at": review.created_at.strftime("%Y-%m-%d")
    }


def get_ordered_resorts(resorts_dict, order_list):
    normalized_order = [kw.lower().strip() for kw in order_list]

    def get_order_index(resort_name):
        resort_name_lower = resort_name.lower().strip()
        for i, keyword in enumerate(normalized_order):
            if keyword in resort_name_lower:
                return i
        return len(normalized_order)  # resort không khớp keyword nào sẽ ở cuối

    return sorted(resorts_dict.items(), key=lambda x: get_order_index(x[0].lower().strip()))



def annotate_extremes(processed_reviews):
    if not processed_reviews:
        return
    for review in processed_reviews:
        if review.get('rating') is None:
            review['rating'] = 0
        if review.get('total_reviews') is None:
            review['total_reviews'] = 0

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
            is_highest = score['value'] == max(scores_for_criterion)
            is_lowest = score['value'] == min(scores_for_criterion)

            score['highest_score'] = is_highest
            score['lowest_score'] = is_lowest

            # ✅ Update trong scores_dict
            review['scores_dict'][score['key']]['highest_score'] = is_highest
            review['scores_dict'][score['key']]['lowest_score'] = is_lowest


def normalize_resort_name(original_name, predefined_order):
    original_lower = original_name.lower().strip()
    for keyword in predefined_order:
        if keyword.lower() in original_lower:
            return keyword  # Dùng tên ngắn trong predefined_order
    return original_name



def process_source_reviews(source, resorts, order, base_date=None, compare_date=None):
    processed_reviews = []
    all_created_times = []

    for resort, review_infos in get_ordered_resorts(resorts, order):
        info = review_infos[0]
        review = info['review']
        compare_review = info['compare_review']
        processed_reviews.append(
            process_review(review, compare_review, base_date, compare_date)
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


def get_reviews_from_db(request):
    source_param = request.GET.get('source')
    base_date_str = request.GET.get('base_date')
    compare_date_str = request.GET.get('compare_date')
    month_param = request.GET.get('month')

    base_date = datetime.strptime(base_date_str, "%Y-%m-%d") if base_date_str else None
    compare_date = datetime.strptime(compare_date_str, "%Y-%m-%d") if compare_date_str else None

    reviews = fetch_reviews()

    if month_param:
        reviews = [
            r for r in reviews
            if r.created_at.strftime('%Y-%m') == month_param
        ]

    valid_dates = sorted(list({r.created_at.date().isoformat() for r in reviews}))
    latest_updated_time = None

    all_sources = list({review.source for review in reviews})
    if not source_param and all_sources:
        source_param = all_sources[0]

    grouped = defaultdict(lambda: defaultdict(list))
    for review in reviews:
        compare_review = get_compare_review(review, base_date, compare_date)
        grouped[review.source][review.resort].append({
            'review': review,
            'compare_review': compare_review
        })

    if source_param:
        grouped = {source_param: grouped.get(source_param, {})}

    # Resort order: bạn có thể dùng danh sách thủ công hoặc từ dữ liệu
    predefined_order = [
        "Furama Resort",
        "TIA",
        "Pullman",
        "Premier",
        "Marriott",
        "Hyatt",
        "Naman",
        "Sheraton",
        "Fusion",
        "Furama Villas",
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
        "source": source_param,  # 💡 nhớ truyền lại để dùng trong template
        "base_date": request.GET.get('base_date'),
        "compare_date": request.GET.get('compare_date'),
        "valid_dates": valid_dates,
        "month": month_param,
    }


def ota_crawler_home(request):
    data = get_reviews_from_db(request)

    context = {
        'reviews': data['reviews'],
        'available_sources': data['available_sources'],
        'latest_updated_time': data['latest_updated_time'],
        'source': data['source'],
        'base_date': data['base_date'],
        'compare_date': data['compare_date'],
        'valid_dates': data['valid_dates'], 
        'month': data.get('month'),
    }

    if request.headers.get("HX-Request"):
        return render(request, "ota_reviews/partials/content.html", context)
    
    return render(request, "ota_reviews/index.html", context)
    # return JsonResponse({
    #     'reviews': data['reviews'],
    #     'available_sources': data['available_sources'],
    #     'latest_updated_time': data['latest_updated_time']
    # }, safe=False)  # Trả về JsonResponse thay vì render template
