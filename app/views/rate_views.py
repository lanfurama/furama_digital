from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import render_to_string
from app.models import DailyRate
from datetime import timedelta, date
from django.http import JsonResponse
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import math
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.dateparse import parse_date
from datetime import datetime, timedelta, date
import json

# ========================
# Utilities
# ========================

def is_nan(value):
    try:
        return math.isnan(float(value))
    except (TypeError, InvalidOperation, ValueError):
        return False

def format_currency(value, is_percent=False):
    # Định dạng số liệu để hiển thị ra frontend, tuỳ vào loại dữ liệu (giá tiền hoặc phần trăm)
    if is_nan(value):
        return "--"
    if value == -1:
        return "Flex out"
    if value == 0:
        return "Sold out"
    if is_percent:
        return f"{round(value):,d}%"
    return f"{value:,.0f}₫"


def create_cell(field, current_value, compare_value, latest_date=None, compare_date=None, is_percent=False):
    # Tạo dữ liệu cho từng ô trong bảng, bao gồm logic tính phần trăm chênh lệch và tooltip
    if current_value is None or is_nan(current_value):
        return {"display_current_value": "--"}
    if current_value in [0, -1]:
        return {"display_current_value": "Flex out" if current_value == 0 else "Sold out"}

    # Format giá trị hiện tại
    display_current_value = format_currency(current_value, is_percent)
    result = {"display_current_value": display_current_value, "current_value": current_value}

    if compare_value not in [None, 0, -1] and not is_nan(compare_value):
        try:
            percent = ((current_value - compare_value) / compare_value) * 100
            percent = max(min(percent, 100), -100)
            result.update({
                "field": field,
                "display_compare_value": format_currency(compare_value, is_percent),
                "compare_updated_date": compare_date,
                "current_updated_date": latest_date,
                "percent": f"{percent:+.1f}%" if percent != 0 else None,
                "trend": "up" if percent > 0 else "down" if percent < 0 else None,
                "change_value": f"{(current_value - compare_value):+,.1f}" + ("" if is_percent else "₫"),
                "tooltip": True
            })
        except ZeroDivisionError:
            pass
    return result
    
def calculate_rate_statistics(rows, columns):
    total_sold_out, total_flex_out = 0, 0

    for row in rows:
        # Calculate total price for resorts (furama_resort, hyatt_regency, etc.)
        for cell in row.get('cells', [])[2:]:  # Starting from "furama_resort" column
            value_display = cell.get('display_current_value')

            if value_display == "Sold out":
                total_sold_out += 1
            elif value_display == "Flex out":
                total_flex_out += 1

    return total_sold_out, total_flex_out

# ========================
# Constants
# ========================

COLUMNS = [
    ("my_otb", "My OTB"),
    ("market_demand", "Market Demand"),
    ("furama_resort", "Furama Resort"),
    ("hyatt_regency", "Hyatt Regency"),
    ("pullman_beach", "Pullman Beach"),
    ("sheraton_grand", "Sheraton Grand"),
    ("danang_marriott", "Danang Marriott"),
    ("fusion_resort", "Fusion Resort"),
    ("shilla_monogram", "Shilla Monogram"),
    ("koi_resort", "KOI Resort"),
    ("marriott_non_nuoc", "Marriott Non Nuoc"),
    ("premier_village", "Premier Village"),
    ("furama_villas", "Furama Villas"),
]

# ========================
# Helpers
# ========================

def group_rates_by_reported_date(rates):
    grouped = defaultdict(list)
    for rate in rates:
        grouped[rate.reported_date].append(rate)
    return grouped


def find_latest_before(entries, target_dt):
    candidates = [r for r in entries if r.updated_date <= target_dt]
    return max(candidates, key=lambda r: r.updated_date) if candidates else None


def get_date_range(request):
    start_str = request.GET.get("start_date")
    end_str = request.GET.get("end_date")
    month_str = request.GET.get("month")

    # Nếu có tham số start & end trong URL
    if start_str and end_str:
        return parse_date(start_str), parse_date(end_str), month_str

    # Lấy tất cả ngày có trong DB
    updated_dates = DailyRate.objects.order_by("updated_date").values_list("updated_date", flat=True).distinct()
    if not updated_dates:
        today = date.today()
        return today - timedelta(days=7), today

    # Lấy ngày mới nhất
    end = updated_dates.last().date()
    # Tìm ngày gần nhất trước ngày mới nhất
    dates_before = [d.date() for d in updated_dates if d.date() < end]
    start = max(dates_before) if dates_before else end  # fallback nếu chỉ có 1 ngày
    return start, end, month_str


def get_suggested_furama_resort_rate(report_date, furama_price, otb, demand, competitor_avg_price=None):
    """
    Trả về mức giá gợi ý và lý do điều chỉnh.
    
    :param report_date: ngày cần dự đoán
    :param furama_price: giá hiện tại của Furama
    :param otb: booking hiện tại (%)
    :param demand: nhu cầu thị trường (%)
    :param competitor_avg_price: giá trung bình đối thủ cùng ngày
    :return: (suggested_rate, rate_note)
    """
    if not furama_price or furama_price <= 0:
        return 0, ""

    suggested_rate = furama_price
    notes = []

    # Cờ đánh dấu
    is_very_high = otb >= 90 and demand >= 80
    is_high = otb >= 80 or demand >= 80
    is_low = otb <= 30 or demand <= 30
    is_very_low = otb <= 20 and demand <= 20

    # Logic tính toán
    if is_very_high:
        suggested_rate *= 1.15
        notes.append("↑15% (High OTB & Demand)")
    elif is_high:
        suggested_rate *= 1.10
        notes.append("↑10% (OTB or Demand)")
    elif is_low:
        suggested_rate *= 0.93
        notes.append("↓7% (OTB or Demand)")
    elif is_very_low:
        suggested_rate *= 0.90
        notes.append("↓10% (Low OTB & Demand)")
    else:
        notes.append("→0% (Stable)")

    # 2. So sánh với giá trung bình đối thủ
    if competitor_avg_price and competitor_avg_price > 0:
        delta = (furama_price - competitor_avg_price) / competitor_avg_price

        # Nếu Furama thấp hơn đối thủ nhưng OTB/Demand cao → Tăng giá 5%
        if delta <= -0.10 and otb >= 80 and demand >= 80:
            suggested_rate *= 1.05
            notes.append("↑5% (Furama underpriced vs Competitor)")

        # Nếu Furama cao hơn đối thủ và OTB/Demand thấp → Giảm giá 5%
        elif delta >= 0.10 and otb <= 30 and demand <= 30:
            suggested_rate *= 0.95
            notes.append("↓5% (Furama overpriced vs Competitor)")
        
        # Nếu Furama thấp hơn đối thủ nhưng OTB thấp → Giữ giá hoặc giảm nhẹ
        elif delta <= -0.05 and otb <= 30:
            suggested_rate *= 0.98
            notes.append("↓2% (Furama lower price but Low OTB)")

        # Nếu Furama cao hơn đối thủ nhưng OTB cao và Demand cao → Giữ giá
        elif delta >= 0.10 and otb >= 80 and demand >= 80:
            suggested_rate *= 1.00  # Giữ nguyên
            notes.append("→0% (Furama premium, High OTB & Demand)")

    # Làm tròn đến hàng nghìn
    suggested_rate = round(suggested_rate, -3)

    return suggested_rate, " | ".join(notes)


def build_comparison_rows(grouped_rates, start_dt, end_dt, month_str=None):
    rows = []
    today = date.today()

    for report_date, entries in grouped_rates.items():
        latest = find_latest_before(entries, end_dt)
        compare = find_latest_before(entries, start_dt)

        if not latest:
            continue

        furama_price = parse_number(getattr(latest, "furama_resort", 0))
        
        # Lấy giá các đối thủ (tất cả field sau "furama_resort")
        competitor_prices = []
        passed_furama = False
        for field, _ in COLUMNS[2:]:  # Bỏ qua OTB, Demand
            if field == "furama_resort":
                passed_furama = True
                continue
            if not passed_furama:
                continue
            val = getattr(latest, field, None)
            parsed_val = parse_number(val)
            if parsed_val is not None and parsed_val > 0:
                competitor_prices.append(parsed_val)

        competitor_avg_price = sum(competitor_prices) / len(competitor_prices) if competitor_prices else None

        # Tính giá trị max/min và khoảng cách giá
        price_values = []
        for field, _ in COLUMNS[2:]:  # Bỏ qua 2 cột đầu (giả định là OTB, Demand)
            val = getattr(latest, field, None)
            parsed_val = parse_number(val)
            if parsed_val is not None and parsed_val > 0:
                price_values.append(parsed_val)
        if len(price_values) >= 2:
            max_price = max(price_values) if price_values else 0
            min_price = min(price_values) if price_values else 0
            price_gap = max_price - min_price
        else:
            max_price = min_price = price_gap = 0 

        avg_price = sum(price_values) / len(price_values) if price_values else 0
        otb = parse_number(getattr(latest, "my_otb", 0))
        demand = parse_number(getattr(latest, "market_demand", 0))
        suggested_furama_rate, rate_note = get_suggested_furama_resort_rate(report_date, furama_price, otb, demand, competitor_avg_price)

        row = {
            "reported_date": report_date.strftime("%Y/%m/%d"),
            "updated_date": latest.updated_date.strftime("%Y/%m/%d"),
            "date_status": (
                "today" if report_date == today
                else "future" if report_date > today
                else "past"
            ),
            "cells": [],
            "max_price": max_price,
            "min_price": min_price,
            "price_gap": price_gap,
            "avg_price": avg_price,
            "suggested_furama_rate": format_currency(suggested_furama_rate),
            "suggested_furama_rate_note": rate_note,
        }

        for field, _ in COLUMNS:
            latest_value = getattr(latest, field, None)
            compare_value = getattr(compare, field, 0) if compare else 0
            is_percent = field in ["my_otb", "market_demand"]
            row["cells"].append(create_cell(
                field,
                latest_value,
                compare_value,
                latest.updated_date.strftime("%Y/%m/%d"),
                compare.updated_date if compare else None,
                is_percent
            ))

        rows.append(row)

    return rows


def parse_number(val):
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return val
    try:
        # Remove comma (1,234,000 -> 1234000)
        return float(str(val).replace(',', '').strip())
    except Exception:
        return None


def sort_rows(rows, sort_by):
    def parse_date_str(d):
        return datetime.strptime(d, "%Y/%m/%d")

    if sort_by == "latest-reported":
        rows.sort(key=lambda r: parse_date_str(r["reported_date"]), reverse=True)

    elif sort_by == "oldest-reported":
        rows.sort(key=lambda r: parse_date_str(r["reported_date"]))

    elif sort_by == "highest_price":
        rows.sort(
            key=lambda r: next(
                (cell.get("current_value") or 0 for cell in r["cells"][2:]
                 if cell.get("current_value") is not None),
                0
            ),
            reverse=True
        )

    elif sort_by == "lowest_price":
        rows.sort(
            key=lambda r: next(
                (cell.get("current_value") for cell in r["cells"][2:]
                 if cell.get("current_value") is not None),
                float("inf")
            )
        )

    elif sort_by == "most_soldout":
        rows.sort(
            key=lambda r: sum(
                1 for cell in r["cells"][2:]
                if cell.get("display_current_value") == "Sold out"
            ),
            reverse=True
        )

    elif sort_by == "price_gap":
        rows.sort(key=lambda r: r["price_gap"], reverse=True)


def calculate_column_averages(rows, columns):
    summary = []

    for idx, (field, _) in enumerate(columns):
        total = 0
        count = 0
        is_percent = field in ["my_otb", "market_demand"]

        for row in rows:
            cell = row["cells"][idx]
            value = parse_number(cell.get("current_value"))
            if value is not None and not is_nan(value):
                total += value
                count += 1

        if count:
            average = total / count
            formatted = format_currency(round(average, 0), is_percent=is_percent)
        else:
            formatted = None

        summary.append(formatted)

    return summary

# ========================
# View
# ========================
def index(request):
    # 1. Xử lý ngày bắt đầu và kết thúc
    start_date, end_date, month_str = get_date_range(request)
    print(f"Start Date: {start_date}, End Date: {end_date}, Month: {month_str}")
    month_str = month_str or datetime.now().strftime("%Y-%m")

    # 2. Tách tháng và năm từ month_str (ví dụ: '2025-07')
    year, month = map(int, month_str.split('-'))

    # 2. Ép thành datetime để filter chính xác
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # 3. Truy vấn dữ liệu
    rates = DailyRate.objects.filter(updated_date__lte=end_dt, reported_date__year=year, reported_date__month=month)
    grouped_rates = group_rates_by_reported_date(rates)
    valid_dates = sorted(set(rate.updated_date.strftime('%Y-%m-%d') for rate in rates))
    latest_updated_date = DailyRate.objects.order_by('-updated_date').values_list('updated_date', flat=True).first()
    rows = build_comparison_rows(grouped_rates, start_dt, end_dt, month_str)
    sort_by = request.GET.get("sort_by", "oldest_reported")
    sort_rows(rows, sort_by)
    total_sold_out, total_flex_out = calculate_rate_statistics(rows, COLUMNS)

    # 5. Tạo context
    context = {
        "total_rates": rates.count(),
        "total_rows": len(rows),
        "rows": rows,
        "columns": COLUMNS,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "valid_dates": valid_dates, 
        "total_sold_out": total_sold_out,  # Total sold out
        "total_flex_out": total_flex_out,  # Total flex out
        "month": month_str, 
        "sort_by": sort_by,
        "latest_updated_date": latest_updated_date.strftime("%Y-%m-%d") if latest_updated_date else None,
        "column_averages": calculate_column_averages(rows, COLUMNS),
    }

    if request.headers.get("HX-Request") == "true":
        html = render_to_string("rates/partials/table.html", context)
        return HttpResponse(html)
                

    return render(request, "rates/index.html", context)
    # return JsonResponse(context)
