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


def create_cell(current_value, compare_value, latest_date=None, compare_date=None, is_percent=False):
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
                "display_compare_value": format_currency(compare_value, is_percent),
                "percent": f"{percent:+.1f}%",
                "trend": "up" if percent > 0 else "down",
                "change_value": f"{(current_value - compare_value):+,.1f}" + ("" if is_percent else "₫"),
                "tooltip": True
            })
        except ZeroDivisionError:
            pass
    return result
    
def calculate_rate_statistics(rows, columns):
    total_sold_out, total_flex_out, total_otb, total_price = 0, 0, 0, 0
    count, price_count = len(rows), 0

    for row in rows:
        if row.get('cells') and len(row['cells']) > 0:
            my_otb = row['cells'][0].get('current_value')
            if my_otb is not None:
                total_otb += my_otb

        # Calculate total price for resorts (furama_resort, hyatt_regency, etc.)
        for cell in row.get('cells', [])[2:]:  # Starting from "furama_resort" column
            value = cell.get('current_value')
            value_display = cell.get('display_current_value')

            if value is not None:
                total_price += value
                price_count += 1

            if value_display == "Sold out":
                total_sold_out += 1
            elif value_display == "Flex out":
                total_flex_out += 1

    # Calculate averages
    avg_otb = total_otb / count if count > 0 else 0
    avg_price = total_price / price_count if price_count > 0 else 0

    return total_sold_out, total_flex_out, format_currency(avg_otb, is_percent=True), format_currency(avg_price)

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
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")
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


def build_comparison_rows(grouped_rates, start_dt, end_dt, month_str=None):
    rows = []
    today = date.today()

    for report_date, entries in grouped_rates.items():
        # if month_str:
        #     # Lọc theo tháng nếu có tháng
        #     if report_date.strftime("%Y-%m") != month_str:
        #         continue  # Nếu reported_date không phải tháng được chọn, bỏ qua

        latest = find_latest_before(entries, end_dt)
        compare = find_latest_before(entries, start_dt)

        if not latest:
            continue

        row = {
            "reported_date": report_date.strftime("%d/%m/%Y"),
            "updated_date": latest.updated_date.strftime("%d/%m/%Y"),
            "date_status": (
                "today" if report_date == today
                else "future" if report_date > today
                else "past"
            ),
            "cells": [],
        }

        for field, _ in COLUMNS:
            latest_value = getattr(latest, field, None)
            compare_value = getattr(compare, field, 0) if compare else 0
            is_percent = field in ["my_otb", "market_demand"]
            row["cells"].append(create_cell(
                latest_value,
                compare_value,
                latest.updated_date.strftime("%d/%m/%Y"),
                compare.updated_date if compare else None,
                is_percent
            ))

        rows.append(row)

    return rows


def sort_rows(rows, sort_by):
    def parse_date_str(d):
        return datetime.strptime(d, "%d/%m/%Y")

    if sort_by == "latest-updated":
        rows.sort(key=lambda r: parse_date_str(r["updated_date"]), reverse=True)

    elif sort_by == "latest-reported":
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
        rows.sort(
            key=lambda r: (
                max([
                    cell.get("current_value") for cell in r["cells"][2:]
                    if isinstance(cell.get("current_value"), (int, float))
                ] or [0])
                -
                min([
                    cell.get("current_value") for cell in r["cells"][2:]
                    if isinstance(cell.get("current_value"), (int, float))
                ] or [0])
            ),
            reverse=True
        )


# ========================
# View
# ========================
def index(request):
    # 1. Xử lý ngày bắt đầu và kết thúc
    start_date, end_date, month_str = get_date_range(request)
    month_str = month_str or datetime.now().strftime("%Y-%m")

    # 2. Tách tháng và năm từ month_str (ví dụ: '2025-07')
    year, month = map(int, month_str.split('-'))

    # 2. Ép thành datetime để filter chính xác
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # 3. Truy vấn dữ liệu
    # rates = DailyRate.objects.filter(updated_date__lte=end_dt, reported_date__year=year, reported_date__month=month).order_by("reported_date")
    rates = DailyRate.objects.filter(updated_date__lte=end_dt, reported_date__year=year).order_by("reported_date")
    grouped_rates = group_rates_by_reported_date(rates)
    valid_dates = sorted(set(rate.updated_date.strftime('%Y-%m-%d') for rate in rates))
    rows = build_comparison_rows(grouped_rates, start_dt, end_dt, month_str)

    sort_by = request.GET.get("sort-by", "latest")

    sort_rows(rows, sort_by)
    total_sold_out, total_flex_out, avg_otb, avg_price = calculate_rate_statistics(rows, COLUMNS)

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
        "avg_otb": avg_otb,  # Average OTB
        "avg_price": avg_price,  # Average price
    }

    if request.headers.get("HX-Request") == "true":
        html = render_to_string("rates/partials/rates_table_rows.html", context)
        return HttpResponse(html)

    return render(request, "rates/index.html", context)
    # return JsonResponse(context)
